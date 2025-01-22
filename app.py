import json
import os

from flask import Flask, render_template, request
import requests

app = Flask(__name__)


def load_env(file_path):
    with open(file_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value


load_env('.env')

apikey = os.getenv('API_KEY')

headers = {
    "content-type": "application/json",
    "X-RapidAPI-Key": f"{apikey}",
    "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    city = request.form.get('city')
    checkin_date = request.form.get('checkin')
    checkout_date = request.form.get('checkout')
    adults = request.form.get('adults')

    url = "https://hotels4.p.rapidapi.com/locations/v3/search"
    querystring = {"q": city, "locale": "en_US"}

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        hotels_data = response.json()
        print("Hotels Data Received")
        print(hotels_data)
        hotels_list = []

        for item in hotels_data.get('sr', []):
            if item.get('@type') == 'gaiaHotelResult':
                hotel_name = item.get('regionNames', {}).get('displayName', 'N/A')
                print(hotel_name)
                hotel_id = item.get('hotelId', None)
                print("hotel id: ", hotel_id)
                latitude = item.get('coordinates', {}).get('lat', None)
                longitude = item.get('coordinates', {}).get('long', None)
                region_id = item.get('cityId', None)
                print("region id:", region_id)

                if hotel_id and region_id:
                    print("Checking for OFFERS...")
                    review_score, rating_percentage = get_hotel_review_score(hotel_id)
                    hotel_offers = get_hotel_offers(checkin_date, checkout_date, adults, hotel_id,
                                                    latitude, longitude, region_id)
                    for offer in hotel_offers:
                        offer['hotel_name'] = hotel_name  
                        price_str = offer['price'].split(' ')[0].replace(',', '').replace("$", '')
                        offer['numeric_price'] = float(price_str)
                        offer['review_score'] = review_score
                        offer['rating_percentage'] = rating_percentage
                    hotels_list.extend(hotel_offers)
        return render_template('results.html', hotels=hotels_list)
    else:
        print("Error in search: Status Code", response.status_code)
        return "Eroare la cautarea hotelurilor"


def get_hotel_offers(checkin, checkout, adults, hotel_id, latitude, longitude, region_id):
    url = "https://hotels4.p.rapidapi.com/properties/v2/get-offers"

    payload = {
        "currency": "USD",
        "eapid": 1,
        "locale": "en_US",
        "siteId": 300000001,
        "propertyId": hotel_id,
        "checkInDate": {
            "day": int(checkin.split('-')[2]),
            "month": int(checkin.split('-')[1]),
            "year": int(checkin.split('-')[0])
        },
        "checkOutDate": {
            "day": int(checkout.split('-')[2]),
            "month": int(checkout.split('-')[1]),
            "year": int(checkout.split('-')[0])
        },
        "destination": {
            "coordinates": {
                "latitude": latitude,
                "longitude": longitude
            },
            "regionId": region_id
        },
        "rooms": [{"adults": int(adults), "children": []}]
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        offers_data = response.json()
        room_offers = []
        try:
            for unit in offers_data['data']['propertyOffers']['units']:
                room_name = unit.get('header', {}).get('text')  
                print("ROOM NAME: ", room_name)
                for rate_plan in unit.get('ratePlans'):
                    for room_price in rate_plan['priceDetails']:
                        price = room_price['totalPriceMessage']
                        break
                for pic_plan in unit.get('unitGallery', {}).get('gallery'):
                    pic = pic_plan.get('image', {}).get('url')
                    break
                room_offers.append({'room_name': room_name, 'price': price, 'pic': pic})
        except Exception as ex:
            return f"No offers - {ex}"
            print("No offers")

        try:
            return room_offers
        except Exception as ex:
            print("No offers...")
            return f"No offers: {ex}"
    else:
        print("Error in get_hotel_offers: Status Code", response.status_code)
        return []


def get_hotel_review_score(hotel_id):
    url = "https://hotels4.p.rapidapi.com/reviews/v3/get-summary"
    payload = {
        "currency": "USD",
        "eapid": 1,
        "locale": "en_US",
        "siteId": 300000001,
        "propertyId": hotel_id
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        review_data = response.json()
        # print(review_data)
        score = review_data['data']['propertyReviewSummaries'][0]['overallScoreWithDescriptionA11y']['value']
        rating_percentage = review_data['data']['propertyReviewSummaries'][0]['reviewSummaryDetails'][0][
            'ratingPercentage']
        return score, rating_percentage
    else:
        return None, None


if __name__ == '__main__':
    app.run(debug=True)

