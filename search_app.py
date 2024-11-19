import streamlit as st
from google.cloud import storage
from google.cloud import vision
import requests
from io import BytesIO
import glob
import os
import numpy as np
from PIL import Image


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
    segment = response.product_search_results.product_grouped_results

    return results, segment


def get_related_images(input_image):
    project_id = "argon-producer-437209-a7"
    location = "us-east1"
    product_set_id = "set_B"
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

    return sim


def segment_images(group_results, img_shape, img):
    out = []
    for idx, group_result in enumerate(
        group_results[: len(group_results)]
    ):  # Limit to number of subplots
        polys = group_result.bounding_poly.normalized_vertices
        annot = group_result.object_annotations[0]
        bounding_boxes = []

        # Extract bounding boxes as sets of 4 coordinate pairs
        for i in range(0, len(polys), 4):
            box = []
            for poly in polys[i : i + 4]:
                x = int(poly.x * img_shape[1])
                y = int(poly.y * img_shape[0])
                box.append((x, y))
            if len(box) == 4:
                bounding_boxes.append(box)

        # Display each bounding box on its subplot
        for j, box in enumerate(bounding_boxes[: len(group_results)]):
            x_coords, y_coords = zip(
                *box
            )  # Unzip into separate x and y coordinate lists
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)

            out.append((img[y_min:y_max, x_min:x_max], annot))
    return out


st.title("Quo Trials")

st.write("Upload an image or provide an image URL")
# Image upload input
uploaded_file = st.file_uploader(
    "Choose an image...", type=["jpg", "jpeg", "png", "webp"]
)

# Image URL input
image_url = st.text_input("...or enter an image URL:")

input_image = None
if uploaded_file is not None:
    input_image = uploaded_file.getvalue()  # bytes
    image = Image.open(uploaded_file)
    img_array = np.array(image)
elif image_url:
    try:
        response = requests.get(image_url)
        input_bytes = BytesIO(response.content)
        input_image = input_bytes.read()
        image = Image.open(input_bytes)
        img_array = np.array(image)
    except Exception as e:
        st.error(f"Error loading image from URL: {e}")

# If we have an input image, display it and find related images
if input_image:
    # Display the input image
    st.image(input_image, caption="Input Image", use_column_width="auto")

    # Get related images (mock function)
    related_images, segments = get_related_images(input_image)
    segmented_images = segment_images(segments, img_array.shape, img_array)
    seg_cols = st.columns(len(segments))
    for i, seg_img in enumerate(segmented_images):
        seg_img, annot = seg_img
        seg_cols[i % 5].image(
            seg_img,
            use_column_width="auto",
            caption=f"{annot.name}  \n{round(annot.score, 5)}",
        )

    

    # Display related images side-by-side
    st.write("Similar Images:")

    similar_tabs = st.tabs([s.object_annotations[0].name for s in segments])
    for i, tab in enumerate(similar_tabs):
        with tab:
            segment_similar = segments[i].results
            print(segment_similar)

            product_images = {}
            for related_img in segment_similar:
                product_name = related_img.product.display_name
                all_image = glob.glob(f"details/**/{product_name}/images/*.[jp][pn]g")
                if all_image:
                    img_loc = all_image[0]
                    product_images[product_name] = {
                        "img_loc": img_loc,
                        "score": related_img.score,
                        "brand": img_loc.split("/")[1],
                    }
            cols = st.columns(5)  # Create 5 columns for the images to be displayed side by side

            # Loop over related images and display them
            for i, product in enumerate(product_images.items()):
                product_name, brand, img_location, score = (
                    product[0],
                    product[1]["brand"],
                    product[1]["img_loc"],
                    product[1]["score"],
                )
                with open(img_location, "rb") as f:
                    img = f.read()
                    cols[i % 5].image(
                        img,
                        use_column_width=True,
                        caption=f"{brand}  \n{product_name}  \n{round(score, 5)}",
                    )
