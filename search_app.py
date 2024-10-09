import streamlit as st
from google.cloud import storage
from google.cloud import vision
import requests
from io import BytesIO
import glob




def get_similar_products_file(
    project_id,
    location,
    product_set_id,
    product_category,
    file_path,
    filter,
    max_results,
):
    """Search similar products to image.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_set_id: Id of the product set.
        product_category: Category of the product.
        file_path: Local file path of the image to be searched.
        filter: Condition to be applied on the labels.
                Example for filter: (color = red OR color = blue) AND style = kids
                It will search on all products with the following labels:
                color:red AND style:kids
                color:blue AND style:kids
        max_results: The maximum number of results (matches) to return. If omitted, all results are returned.
    """
    # product_search_client is needed only for its helper methods.
    product_search_client = vision.ProductSearchClient()
    image_annotator_client = vision.ImageAnnotatorClient()

    # Read the image as a stream of bytes.
    if not isinstance(file_path, str):
        content = file_path
    else:
        with open(file_path, "rb") as image_file:
            content = image_file.read()

    # Create annotate image request along with product search feature.
    image = vision.Image(content=content)

    # product search specific parameters
    product_set_path = product_search_client.product_set_path(
        project=project_id, location=location, product_set=product_set_id
    )
    product_search_params = vision.ProductSearchParams(
        product_set=product_set_path,
        product_categories=[product_category],
        filter=filter,
    )
    image_context = vision.ImageContext(product_search_params=product_search_params)

    # Search products similar to the image.
    response = image_annotator_client.product_search(
        image, image_context=image_context, max_results=max_results
    )

    index_time = response.product_search_results.index_time
    results = response.product_search_results.results

    return results

def load_image_from_url(url):
    response = requests.get(url)
    image_bytes = BytesIO(response.content)
    # return Image.open(image_bytes)
    return image_bytes

def get_related_images(input_image):
    project_id = "argon-producer-437209-a7"
    location = "us-east1"
    product_set_id = "master_set"
    product_category = "apparel-v2"
    file_path = input_image
    filter = ""
    max_results = 10

    sim = get_similar_products_file(
        project_id=project_id,
        location=location,
        product_set_id=product_set_id,
        product_category=product_category,
        file_path=file_path,
        filter=filter,
        max_results=max_results,
    ) 

    print(sim)
    return sim

st.title('Quo Trials')

st.write("Upload an image or provide an image URL")
# Image upload input
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

# Image URL input
image_url = st.text_input("...or enter an image URL:")

input_image = None
if uploaded_file is not None:
    input_image = uploaded_file.getvalue() # bytes
elif image_url:
    try:
        input_image = load_image_from_url(image_url)
    except Exception as e:
        st.error(f"Error loading image from URL: {e}")

# If we have an input image, display it and find related images
if input_image:
    # Display the input image
    st.image(input_image, caption="Input Image", use_column_width=True)

    # Get related images (mock function)
    related_images = get_related_images(input_image)
    product_images = []
    for related_img in related_images:
        all_image = glob.glob(f'products/**/{related_img.product.display_name}/*.[jpg][png]*')
        if all_image:
            product_images.append(all_image[0])

    # Display related images side-by-side
    st.write("Similar Images:")
    cols = st.columns(5)  # Create 5 columns for the images to be displayed side by side

    # Loop over related images and display them
    for i, img_location in enumerate(product_images):
        with open(img_location, 'rb') as f:
            img = f.read()
            cols[i % 5].image(img, use_column_width=True)
else:
    st.info("Please upload an image or enter a URL to continue.")
