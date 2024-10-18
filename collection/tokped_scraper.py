import requests
from queries import get_product_query, get_sid_query

REQUEST_URI = "https://gql.tokopedia.com/graphql/ShopProducts"


def get_headers(brand_uri):

    headers = {
        "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        "X-Version": "3ffc927",
        "sec-ch-ua-mobile": "?0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "content-type": "application/json",
        "accept": "*/*",
        "Referer": f"https://www.tokopedia.com/{brand_uri}/product/page/1",
        "X-Source": "tokopedia-lite",
        "X-Device": "default_v3",
        "X-Tkpd-Lite-Service": "zeus",
        "sec-ch-ua-platform": '"macOS"',
    }

    return headers


def get_brand_sid(brand_uri):
    """Converts Brand Official Store Name to SID"""

    url = REQUEST_URI

    headers = get_headers(brand_uri)
    data = [
        {
            "operationName": "ShopInfoCore",
            "variables": {"domain": f"{brand_uri}", "id": 0},
            "query": get_sid_query(),
        }
    ]

    response = requests.post(url, headers=headers, json=data)
    sid = response.json()[0]["data"]["shopInfoByID"]["result"][0]["shopCore"]["shopID"]
    return sid


def get_brand_listing(brand_uri):
    """Returns all products from a brand page"""

    sid = get_brand_sid(brand_uri)

    headers = get_headers(brand_uri)
    url = REQUEST_URI

    listings = []
    i = 1
    while True:
        print(f"Collecting {brand_uri} page {i}")
        data = [
            {
                "operationName": "ShopProducts",
                "variables": {
                    "source": "shop",
                    "sid": sid,
                    "page": i,
                    "perPage": 80,
                    "etalaseId": "etalase",
                    "sort": 1,
                    # "user_districtId": "2274",
                    # "user_cityId": "176",
                    # "user_lat": "0",
                    # "user_long": "0",
                },
                "query": get_product_query(),
            }
        ]

        response = requests.post(url, headers=headers, json=data)

        # Output the response from the request
        listings.append(response.json())
        i += 1
        if response.json()[0]["data"]["GetShopProduct"]["links"]["next"] == "":
            return listings
