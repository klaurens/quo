import streamlit as st
from google.cloud import vision
import requests
from io import BytesIO
import glob
import numpy as np
from PIL import Image

CATEGORY_MAPPING = {
    "shirt": ["sweater", "shirt|blouse", "top|t-shirt|sweatshirt", "vest"],
    "blouse": ["sweater", "shirt|blouse", "top|t-shirt|sweatshirt", "vest"],
    "t-shirt": ["sweater", "shirt|blouse", "top|t-shirt|sweatshirt", "vest"],
    "top": ["sweater", "shirt|blouse", "top|t-shirt|sweatshirt", "vest"],
    "sweatshirt": ["sweater", "shirt|blouse", "top|t-shirt|sweatshirt", "vest"],
    "jacket": ["cardigan", "coat", "jacket", "vest"],
    "outerwear": ["cardigan", "coat", "jacket", "vest"],
    "hoodie": ["jacket", "top|t-shirt|sweatshirt"],
    "coat": ["cardigan", "coat", "jacket"],
    "pants": ["shorts", "pants"],
    "jeans": ["shorts", "pants"],
    "culottes": ["shorts", "pants"],
    "shorts": ["shorts", "pants"],
    "skirt": ["skirt"],
    "dress": ["dress"],
    "midi dress": ["dress"],
    "mini dress": ["dress"],
    "maxi dress": ["dress"],
    "cardigan": ["cardigan", "coat", "jacket"],
    "sweater": ["sweater", "shirt|blouse", "top|t-shirt|sweatshirt", "vest"],
    "vest": ["sweater", "shirt|blouse", "top|t-shirt|sweatshirt", "vest"],
    "jumpsuit": ["jumpsuit"],
    "playsuit": ["jumpsuit"],
    "tights": ["tights|stockings"],
    "stockings": ["tights|stockings"],
    "leggings": ["tights|stockings"],
    "shoe": ["shoe"],
    "sneaker": ["shoe"],
    "boot": ["shoe"],
    "heel": ["shoe"],
    "sandal": ["shoe"],
    "flat shoe": ["shoe"],
    "slip-on": ["shoe"]
}

@st.cache_resource
def get_similar_products_file(project_id, location, product_set_id, product_category, file_path, filter="", max_results=500):
    """Search for similar products using Google Vision API."""
    product_search_client = vision.ProductSearchClient()
    image_annotator_client = vision.ImageAnnotatorClient()
    content = file_path if not isinstance(file_path, str) else open(file_path, "rb").read()
    image = vision.Image(content=content)
    product_set_path = product_search_client.product_set_path(project=project_id, location=location, product_set=product_set_id)
    product_search_params = vision.ProductSearchParams(
        product_set=product_set_path,
        product_categories=[product_category],
        filter=filter
    )
    image_context = vision.ImageContext(product_search_params=product_search_params)
    response = image_annotator_client.product_search(image, image_context=image_context, max_results=max_results)
    return response.product_search_results.results, response.product_search_results.product_grouped_results

def segment_images(group_results, img_shape, img):
    """Extract segmented images from bounding boxes."""
    output = []
    for group_result in group_results:
        polys = group_result.bounding_poly.normalized_vertices
        annot = group_result.object_annotations[0]
        bounding_boxes = [
            [(int(poly.x * img_shape[1]), int(poly.y * img_shape[0])) for poly in polys[i:i + 4]]
            for i in range(0, len(polys), 4)
        ]
        for box in bounding_boxes:
            x_coords, y_coords = zip(*box)
            x_min, x_max, y_min, y_max = min(x_coords), max(x_coords), min(y_coords), max(y_coords)
            output.append((img[y_min:y_max, x_min:x_max], annot))
    return output

def map_category(category):
    """Map Google Vision category to predefined categories."""
    for key, values in CATEGORY_MAPPING.items():
        if category.lower() in values:
            return key
    return category

def display_related_images(segment_similar, tab_name):
    """Display images in the selected tab."""
    product_images = {}
    for related_img in segment_similar:
        product_name = related_img.product.display_name
        category = next((label.value for label in related_img.product.product_labels if label.key == "category"), None)
        mapped_category = map_category(category)
        valid_categories = CATEGORY_MAPPING.get(tab_name.lower(), None)
        if valid_categories and category.lower() in valid_categories:
            img_files = glob.glob(f"details/**/{product_name}/images/*.[jp][pn]g")
            if img_files:
                img_loc = img_files[0]
                product_images[product_name] = {
                    "img_loc": img_loc,
                    "score": related_img.score,
                    "brand": img_loc.split("/")[1],
                    "category": mapped_category,
                    "original_category": category,
                    "all_images": img_files[1:] if len(img_files) > 1 else []
                }

    num_cols = 7
    max_images = num_cols * 3
    cols = st.columns(num_cols)

    def toggle_item(item):
        """Toggle item in session state."""
        if item in st.session_state["selected_items"]:
            st.session_state["selected_items"].remove(item)
        else:
            st.session_state["selected_items"].add(item)

    for idx, (p_name, attrs) in enumerate(product_images.items()):
        if idx >= max_images:
            break
        with cols[idx % num_cols]:
            primary_image = attrs["img_loc"]
            with open(primary_image, "rb") as f:
                img_data = f.read()
            st.image(
                img_data,
                use_column_width=True,
                caption=f"{p_name}\n{attrs['brand']}\n{attrs['category']}\n{attrs['original_category']}\n{round(attrs['score'], 5)}"
            )
            # Create toggle button
            toggle_label = "Remove Item" if primary_image in st.session_state["selected_items"] else "Add Item"
            st.button(
                toggle_label, 
                key=f"toggle_{p_name}", 
                on_click=toggle_item, 
                args=(primary_image,)
            )

            # Place expander directly under the image
            with st.expander("More Images", expanded=False):
                for other_img_path in attrs['all_images']:
                    st.image(other_img_path, use_column_width=True)

# Streamlit UI
st.set_page_config(layout="wide")
st.sidebar.title("Selected Items")
if "selected_items" not in st.session_state:
    st.session_state["selected_items"] = set()
# Initialize the session state if not already done
if st.session_state["selected_items"]:
    for item in sorted(st.session_state["selected_items"]):
        st.sidebar.image(item)
else:
    st.sidebar.write("No items selected")


st.title("Quo Trials")
st.write("Upload an image or provide an image URL")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"])
image_url = st.text_input("...or enter an image URL:")

input_image, img_array = None, None
if uploaded_file:
    input_image = uploaded_file.getvalue()
    img_array = np.array(Image.open(uploaded_file))
elif image_url:
    try:
        response = requests.get(image_url)
        input_image = BytesIO(response.content).read()
        img_array = np.array(Image.open(BytesIO(response.content)))
    except Exception as e:
        st.error(f"Error loading image from URL: {e}")

if input_image:
    st.image(input_image, caption="Input Image", use_column_width="auto")
    index = st.selectbox("Select an Index", ('test-set', 'set_A', 'set_B'))
    related_images, segments = get_similar_products_file(
        project_id="argon-producer-437209-a7",
        location="us-east1",
        product_set_id=index,
        product_category="apparel-v2",
        file_path=input_image
    )
    segmented_images = segment_images(segments, img_array.shape, img_array)
    seg_cols = st.columns(len(segments))
    for idx, (seg_img, annot) in enumerate(segmented_images):
        seg_cols[idx % 5].image(seg_img, use_column_width="auto", caption=f"{annot.name}\n{round(annot.score, 5)}")
    
    st.write("Similar Images:")
    tab_names = [s.object_annotations[0].name for s in segments]
    similar_tabs = st.tabs(tab_names)
    for i, tab in enumerate(similar_tabs):
        with tab:
            display_related_images(segments[i].results, tab_names[i])
