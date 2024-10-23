import requests
import re
from logger import logger
from requests.exceptions import RequestException
from queries import get_product_query, get_sid_query, get_product_details_query

# Configuration constants
ARRAY_REQUEST_URI = "https://gql.tokopedia.com/graphql/ShopProducts"
PDP_REQUEST_URI = "https://gql.tokopedia.com/graphql/PDPGetLayoutQuery"
REGEX_PRODUCT_URI = r"(https?://www\.)?tokopedia\.com/([\w\d]+?)/([\w\d-]+)\??"
REQUEST_TIMEOUT = 10  # Timeout for all requests (in seconds)


def get_headers(brand_uri, product_uri=None):
    referer = (
        f"https://www.tokopedia.com/{brand_uri}/{product_uri}?extParam=src%3Dshop"
        if product_uri
        else f"https://www.tokopedia.com/{brand_uri}/product/page/1"
    )

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
        headers["X-TKPD-AKAMAI"] = "pdpGetLayout"

    return headers


def get_brand_sid(brand_uri):
    """Converts Brand Official Store Name to SID"""
    try:
        headers = get_headers(brand_uri)
        data = [
            {
                "operationName": "ShopInfoCore",
                "variables": {"domain": brand_uri, "id": 0},
                "query": get_sid_query(),
            }
        ]

        response = requests.post(
            ARRAY_REQUEST_URI, headers=headers, json=data, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()  # Raise an error for bad HTTP status codes

        sid = response.json()[0]["data"]["shopInfoByID"]["result"][0]["shopCore"][
            "shopID"
        ]
        logger.info(f"Successfully retrieved SID for {brand_uri}: {sid}")
        return sid
    except (RequestException, KeyError) as e:
        logger.error(f"Failed to retrieve SID for {brand_uri}: {str(e)}")
        return None


def get_brand_listing(brand_uri):
    """Returns all products from a brand page"""
    sid = get_brand_sid(brand_uri)
    if not sid:
        return []

    headers = get_headers(brand_uri)
    listings = []
    i = 1

    while True:
        try:
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
                    },
                    "query": get_product_query(),
                }
            ]

            response = requests.post(
                ARRAY_REQUEST_URI, headers=headers, json=data, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            listings.append(response.json())

            if not response.json()[0]["data"]["GetShopProduct"]["links"]["next"]:
                break
            i += 1
        except (RequestException, KeyError) as e:
            logger.error(
                f"Error retrieving product listings for {brand_uri} on page {i}: {str(e)}"
            )
            break

    logger.info(f"Retrieved {len(listings)} pages of products for {brand_uri}")
    return listings


def split_product_uri(product_url):
    match = re.match(REGEX_PRODUCT_URI, product_url)
    if not match:
        raise ValueError(f"Invalid product URL: {product_url}")

    brand_uri, product_uri = match[2], match[3]
    return brand_uri, product_uri


def get_item_details(product_url):
    try:
        brand_uri, product_uri = split_product_uri(product_url)
        headers = get_headers(brand_uri, product_uri)

        data = [
            {
                "operationName": "PDPGetLayoutQuery",
                "variables": {
                    "shopDomain": brand_uri,
                    "productKey": product_uri,
                    "layoutID": "",
                    "apiVersion": 1,
                    "tokonow": {"shopID": "0", "whID": "0", "serviceType": ""},
                    "extParam": "src%3Dshop",
                },
                "query": get_product_details_query(),
            }
        ]

        response = requests.post(
            PDP_REQUEST_URI, headers=headers, json=data, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except (RequestException, ValueError) as e:
        logger.error(f"Error retrieving product details for {product_url}: {str(e)}")
        return None


def get_image(image_url, brand_uri=""):
    try:
        response = requests.get(
            image_url, headers=get_headers(brand_uri), timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.content
    except (RequestException, ValueError) as e:
        logger.error(f"Error retrieving image from {image_url}: {str(e)}")
        return None
