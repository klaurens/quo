from tokped_scraper import get_brand_listing, get_item_details
from datetime import datetime
import os
import glob
import json
from jsonpath_ng import parse


WRITE_DATE = datetime.today().date()

def scrape_listing():
    with open('brands.txt', 'r') as read_file:
        brands = read_file.readlines()
        brands = [b.strip() for b in brands]

    for brand in brands:
        print(f'Fetching brand list for {brand}')
        brand_listing = get_brand_listing(brand_uri=brand)

        file_name = f'{brand}_listing_{WRITE_DATE}'
        file_dir = f'{brand}/{file_name}.json'
        os.makedirs(os.path.dirname(file_dir), exist_ok=True)
        print(f'Writing {file_name} list at {file_dir}')
        with open(file_dir, 'w+') as write_file:
            json.dump(brand_listing, write_file)

def unify_listings():
    scraped_products = []
    json_files = glob.glob('./**/*.json')    
    for json_file in json_files:
        with open(json_file) as jf:
            j = json.loads(jf.read())
            parser = parse('[*].[*].data.GetShopProduct.data[*]')
            update_parser = parse('[*].[*].data.GetShopProduct.data[*].brand')
            brand = json_file.split('/')[1]
            update_parser.update_or_create(j, brand)
            values = parser.find(j)
            scraped_products.extend([values[x].value for x in range(len(values))])

    unified_file = f'unified_scraped_products.json'
    with open(unified_file, 'w+') as write_file:
        json.dump(scraped_products, write_file)

if __name__ == '__main__':
    scrape_listing()
    unify_listings()