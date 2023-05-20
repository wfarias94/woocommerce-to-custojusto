import requests
import json
import subprocess
import re
import random
import string


# POST PARTS ADS FROM WOOCOMMERCE TO CUSTOJUSTO

# WooCommerce API URL for retrieving data
WC_API_URL_AllProducts = "https://ajjmgroup.com/wp-json/wc/v3/products?per_page=900"
WC_API_URL = "https://ajjmgroup.com/wp-json/wc/v3/products"

# CustoJusto.pt API URL for submitting data
CJ_API_URL = "https://v2.custojusto.pt"

# WooCommerce API credentials
WC_CONSUMER_KEY = "ck_5f6b28d47e042a3c24f36a9255a11669e133003e"
WC_CONSUMER_SECRET = "cs_39d060d3b061bb1176564eaacc9d7e5f5d624e83"

# CustoJusto.pt API credentials
CJ_API_KEY = "BzAf7GIvy94bKlainMZm"

# Pagination parameters
PER_PAGE = 100  # Number of products per page

# Create the basic authentication string
auth_string = f"{WC_CONSUMER_KEY}:{WC_CONSUMER_SECRET}"

# Retrieve all products recursively
def retrieve_all_products(page=1, wc_data=[]):
    params = {
        "per_page": str(PER_PAGE),
        "page": str(page)
    }
    response = requests.get(WC_API_URL, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET), params=params)
    if response.status_code == 200:
        products = response.json()
        wc_data.extend(products)

        total_pages = int(response.headers.get("X-WP-TotalPages"))
        if page < total_pages:
            return retrieve_all_products(page + 1, wc_data)
        else:
            return wc_data
    else:
        print(f"WooCommerce API Error - Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")
        exit(1)

# Retrieve WooCommerce data using the API GET
print("Retrieving data from WooCommerce...")
wc_data = retrieve_all_products()

product_ids = []

for product in wc_data:
    wc_product_id = product['id']
    product_ids.append(wc_product_id)

# Sort the product IDs in ascending order
product_ids.sort()

# Iteration for each product
for wc_product_id in product_ids:
    
    # Retrieve the corresponding product from wc_data based on the ID
    product = next((p for p in wc_data if p['id'] == wc_product_id), None)
    wc_id = wc_product_id
    wc_title = product["name"].lower()
    wc_description = subprocess.run(['echo', product['short_description']], capture_output=True, text=True).stdout.strip()
    wc_price = int(product['price'])
    wc_slug = product['slug']
    wc_type = product['type']
    
    # Sanitize the description text by removing invalid tags
    wc_description = re.sub('<[^<]+?>', '', wc_description)
    
    # Store the image URLs in a list
    image_urls = [image['src'] for image in product['images']]
    image_ids = []

    # Loop through each image URL and upload it
    for image_url in image_urls:

        # Generate a random filename for each image
        image_file = subprocess.run(['mktemp', '-t', 'ad-image-XXXXXXXXXX.jpg'], capture_output=True, text=True).stdout.strip().lower()
        subprocess.run(['curl', '-o', image_file, '-L', '--create-dirs', image_url], check=True)
        mime_type = subprocess.run(['file', '-b', '--mime-type', image_file], capture_output=True, text=True).stdout.strip()

        if not mime_type.startswith('image/'):
            print('{"results":[{"field":"image","value":"ERROR_BAD_FILENAME"}]}')
            subprocess.run(['rm', image_file])
            exit(1)

        # Make the API request to upload the image
        response = requests.post(f"{CJ_API_URL}/images/ads", headers={"Authorization": CJ_API_KEY}, files={"file": open(image_file, 'rb')})
        response_data = response.json()
    
        # Handle the response
        if 'image' in response_data:
            image_id = response_data['image']['id']
            image_ids.append(image_id)
            image_url = response_data['image']['image_url']
            thumbnail_url = response_data['image']['thumbnail_url']
            gallery_url = response_data['image']['gallery_url']
            server_url = response_data['image']['server_url']
            bytes_received = response_data['image']['bytes_received']
            valid_until = response_data['image']['valid_until']
            #print(f"Image uploaded successfully. Image ID: {image_id}")
        else:
            print("Image upload failed.")
            print(f"Response: {response.text}")
        
        # Remove the locally downloaded image file
        subprocess.run(['rm', image_file])

        # Prepare the data to be submitted to CustoJusto.pt API

        escaped_wc_title = wc_title.replace('"', '\\"')
        escaped_wc_description = wc_description.replace('"', '\\"')
        body = f"[{escaped_wc_title}]\n\n{escaped_wc_description}".lower()

        # Remove newlines from the body field
        escaped_body = body.replace('\n', '')

        # Convert the image IDs list to a JSON string
        image_ids_json = ','.join(str(image_id) for image_id in image_ids)
        CJ_POST_DATA = json.dumps({
            'author': {
                'email': 'ajjmpart@gmail.com',
                'name': 'Ajjm Parts',
                'phone': '937951665',
                'phoneDisabled': False,
                'professionalAd': True,
                'salesmanDisabled': False,
                'vatNumber': '503453200'
            },
            'body': escaped_body,
            'category': '2121',
            'images': image_ids_json.split(","),
            'location': {
                'area': 65,
                'cp6': '4745-399',
                'district': 5,
                'subArea': 4
            },
            'params': {
                'partNumber': ''
            },
            'partner': {
                'externalAdID': str(wc_product_id),
                'externalGroupID': 'CJPRO'
            },
            'price': int(wc_price),
            'subject': wc_slug,
            'type': 's'
        })

    response = requests.post(f"{CJ_API_URL}/partner/entries", headers={"Content-Type": "application/json", "Authorization": CJ_API_KEY}, data=CJ_POST_DATA)
    cj_response = response.text

# Handle the CustoJusto.pt API response
#if "Já existe um anúncio com esse ID Externo" not in cj_response:
    print("CustoJusto.pt API Response:")
    print(cj_response)