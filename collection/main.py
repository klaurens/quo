from tokped_scraper import get_brand_listing, get_product_details_query
from datetime import datetime
import os
import json

if __name__ == '__main__':
    WRITE_DATE = datetime.today().date()

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
