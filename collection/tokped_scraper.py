import requests
import re
from queries import get_product_query, get_sid_query, get_product_details_query

ARRAY_REQUEST_URI = "https://gql.tokopedia.com/graphql/ShopProducts"
PDP_REQUEST_URI = "https://gql.tokopedia.com/graphql/PDPGetLayoutQuery"
REGEX_PRODUCT_URI = "(https?://www\.)?tokopedia\.com/([\w\d]+?)/([\w\d-]+)\??"


def get_headers(brand_uri, product_uri=None):
    if product_uri:
        referer = (
            f"https://www.tokopedia.com/{brand_uri}/{product_uri}?extParam=src%3Dshop"
        )
    else:
        referer = f"https://www.tokopedia.com/{brand_uri}/product/page/1"

    headers = {
        "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        "X-Version": "3ffc927",
        "sec-ch-ua-mobile": "?0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "content-type": "application/json",
        "accept": "*/*",
        "Referer": referer,
        "X-Source": "tokopedia-lite",
        "X-Device": "default_v3",
        "X-Tkpd-Lite-Service": "zeus",
        "sec-ch-ua-platform": '"macOS"',
    }

    if product_uri:
        headers['X-TKPD-AKAMAI'] = 'pdpGetLayout'

    return headers


def get_brand_sid(brand_uri):
    """Converts Brand Official Store Name to SID"""

    headers = get_headers(brand_uri)
    data = [
        {
            "operationName": "ShopInfoCore",
            "variables": {"domain": f"{brand_uri}", "id": 0},
            "query": get_sid_query(),
        }
    ]

    response = requests.post(ARRAY_REQUEST_URI, headers=headers, json=data)
    sid = response.json()[0]["data"]["shopInfoByID"]["result"][0]["shopCore"]["shopID"]
    return sid


def get_brand_listing(brand_uri):
    """Returns all products from a brand page"""

    sid = get_brand_sid(brand_uri)

    headers = get_headers(brand_uri)

    listings = []
    i = 1
    while True:
        print(f"Collecting {brand_uri} page {i}")
        data = [
            {
                "operationName": "ShopProducts",
                "variables": {
                    "source": "shop",
                    "sid": f"{sid}",
                    "page": i,
                    "perPage": 80,
                    "etalaseId": "etalase",
                    "sort": 1,
                },
                "query": get_product_query(),
            }
        ]

        response = requests.post(ARRAY_REQUEST_URI, headers=headers, json=data)

        # Output the response from the request
        print(response.json())
        listings.append(response.json())
        i += 1
        if response.json()[0]["data"]["GetShopProduct"]["links"]["next"] == "":
            return listings


def split_product_uri(product_url):
    match = re.match(REGEX_PRODUCT_URI, product_url)
    if not match:
        raise Exception(f"{product_url} does not match product listing regex condition")
    else:
        brand_uri, product_uri = match[2], match[3]
        return brand_uri, product_uri


def get_item_details(product_url):
    brand_uri, product_uri = split_product_uri(product_url)
    headers = get_headers(brand_uri, product_uri=product_uri)

    data = [
        {
            "operationName": "PDPGetLayoutQuery",
            "variables": {
                "shopDomain": brand_uri,
                "productKey": product_uri,
                "layoutID": "",
                "apiVersion": 1,
                "tokonow": {
                    "shopID": "0",
                    "whID": "0",
                    "serviceType": "",
                },
                "extParam": "src%3Dshop",
            },
            "query": get_product_details_query(),
        },
    ]

    response = requests.post(PDP_REQUEST_URI, headers=headers, json=data)
    return response.json()
