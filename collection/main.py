from tokped_scraper import get_brand_listing, get_item_details, get_image
from datetime import datetime
import os
import glob
import json
from jsonpath_ng import parse


IMAGE_MIN_BYTES = 5000
WRITE_DATE = datetime.today().date()
UNIFIED_FILE = f"unified/{WRITE_DATE}.json"


def scrape_listing(source_file="brands.txt"):
    """Scrapes all listing from brands given"""
    with open(source_file, "r") as read_file:
        brands = read_file.readlines()
        brands = [b.strip() for b in brands]

    for brand in brands:
        print(f"Fetching brand list for {brand}")
        brand_listing = get_brand_listing(brand_uri=brand)

        file_name = f"{brand}_listing_{WRITE_DATE}"
        file_dir = f"listing/{brand}/{file_name}.json"
        os.makedirs(os.path.dirname(file_dir), exist_ok=True)
        print(f"Writing {file_name} list at {file_dir}")
        with open(file_dir, "w+") as write_file:
            json.dump(brand_listing, write_file)


def unify_listings():
    """Unifies and simplifies JSON of product listing"""
    scraped_products = []
    json_files = glob.glob("./**/*.json")
    parser = parse("$..GetShopProduct.data") # [*].[*].data.GetShopProduct.data[*]
    update_parser = parse("$..GetShopProduct.data[*].brand") # [*].[*].data.GetShopProduct.data[*].brand
    for json_file in json_files:
        with open(json_file) as jf:
            j = json.loads(jf.read())
        brand = json_file.split("/")[1]
        update_parser.update_or_create(j, brand)
        values = parser.find(j)
        scraped_products.extend([values[x].value for x in range(len(values))])

    os.makedirs(os.path.dirname(UNIFIED_FILE), exist_ok=True)
    with open(UNIFIED_FILE, "w+") as write_file:
        json.dump(scraped_products, write_file)


def scrape_products():
    latest_unified_json = sorted(glob.glob('unified/*.json'))[-1]
    with open(latest_unified_json, "r") as f:
        products = json.loads(f.read())
    
    for product in products:
        product_name = product["name"]
        product_brand = product["brand"]
        product_url = product["product_url"]
        product_details = get_item_details(product_url)
        write_file = f"details/{product_brand}/{product_name}/{WRITE_DATE}.json"
        os.makedirs(os.path.dirname(write_file), exist_ok=True)
        with open(write_file, "w+") as wf:
            print(f'Writing {write_file}')
            json.dump(product_details, wf)

def scrape_images():
    json_files = glob.glob('details/**/**/*.json')
    parser = parse("$..urlMaxRes")

    for json_file in json_files:
        dir_parts = json_file.split('/')
        product_brand = dir_parts[1]
        product_name = dir_parts[2]
        with open(json_file) as jf:
            j = json.loads(jf.read())
            links = [link.value for link in parser.find(j)]

        for link in links:
            image_name = link.split('/')[-1]
            write_file = f"details/{product_brand}/{product_name}/{image_name}"
            os.makedirs(os.path.dirname(write_file), exist_ok=True)
            image_file = get_image(link, brand_uri=product_brand)
            if len(image_file) >= IMAGE_MIN_BYTES:
                with open(write_file, 'wb') as f:
                    print(f'writing {write_file}')
                    f.write(image_file)
            else:
                print(f'Skip writing {image_file}')
    


if __name__ == "__main__":
    scrape_listing()
    unify_listings()
    scrape_products()
    scrape_images()
