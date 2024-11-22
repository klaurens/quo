import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import glob
import numpy as np
import tensorflow as tf
from PIL import Image
import threading
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from dotenv import load_dotenv
from utils import mask_utils, box_utils
from utils.object_detection import visualization_utils
from pycocotools import mask as mask_api
from processing.logger import logger
from datetime import timedelta
import time
import threading

# Load environment variables
load_dotenv()

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Environment variables
LABEL_MAP_DIR = os.getenv("LABEL_MAP_DIR")
LABEL_MAP_FILE = os.getenv("LABEL_MAP_FILE")
MODEL_DIR = os.path.join(ROOT_DIR, os.getenv("MODEL_DIR"))

DETECT_MAX_BOXES = os.getenv("DETECT_MAX_BOXES")
DETECT_MIN_THRESH = os.getenv("DETECT_MIN_THRESH")
OVERWITE_DETECTION = os.getenv("OVERWITE_DETECTION") == "True"
OUTPUT_SUBDIR = os.getenv("OUTPUT_SUBDIR")

thread_local = threading.local()

def get_model(model_dir):
    if not hasattr(thread_local, "model"):
        thread_local.model = tf.saved_model.load(model_dir)
    return thread_local.model


# def read_labels():
#     """Reads the label map file and returns a dictionary of labels."""
#     label_map_dict = {}
#     label_map_path = os.path.join(LABEL_MAP_DIR, LABEL_MAP_FILE)

#     try:
#         with open(label_map_path, "r") as file:
#             lines = file.readlines()
#             for line in lines:
#                 key, value = line.strip().split(":")
#                 label_map_dict[int(key)] = {"id": int(key), "name": value.strip()}
#         logger.info("Label map loaded successfully.")
#     except Exception as e:
#         logger.error(f"Error reading label map: {e}")

#     return label_map_dict


def process_image(image_file):
    """Processes an image file and returns it as a tensor."""
    try:
        image = Image.open(image_file).convert("RGB")
        result = np.array(image)[:, :, :3]  # Remove alpha channel
        # input_tensor = tf.convert_to_tensor(result[np.newaxis, :, :, :], dtype=tf.uint8)
        input_tensor = tf.convert_to_tensor(result, dtype=tf.uint8)
        logger.info(f"Processed image {image_file}")
        return input_tensor, result.shape
    except Exception as e:
        logger.error(f"Error processing image {image_file}: {e}")
        return None, None


def adjust_boxes(np_boxes, image_info, width, height):
    """Adjusts bounding boxes to the dimensions of the image."""
    np_boxes = np_boxes / np.tile(image_info[1:2, :], (1, 2))
    ymin, xmin, ymax, xmax = np.split(np_boxes, 4, axis=-1)
    ymin = ymin * height
    ymax = ymax * height
    xmin = xmin * width
    xmax = xmax * width
    adjusted_boxes = np.concatenate([ymin, xmin, ymax, xmax], axis=-1)
    logger.debug(f"Adjusted bounding boxes for image of size ({width}, {height})")
    return adjusted_boxes


def process_masks(np_boxes, output_results, height, width):
    """Processes instance masks if available in the model output."""
    np_masks = output_results.get("detection_masks", None)
    encoded_masks = None
    if np_masks is not None:
        np_masks = mask_utils.paste_instance_masks(
            np_masks[0, : len(np_boxes)],
            box_utils.yxyx_to_xywh(np_boxes),
            height,
            width,
        )
        encoded_masks = [mask_api.encode(np.asfortranarray(mask)) for mask in np_masks]
        logger.info("Masks processed successfully.")
    return np_masks, encoded_masks


def visualize_detections(
    result, np_boxes, np_classes, np_scores, label_map_dict, np_masks
):
    """Visualizes bounding boxes and labels on the image array."""
    image_with_detections = visualization_utils.visualize_boxes_and_labels_on_result(
        result,
        np_boxes,
        np_classes,
        np_scores,
        label_map_dict,
        instance_masks=np_masks,
        use_normalized_coordinates=False,
        max_boxes_to_draw=DETECT_MAX_BOXES,
        min_score_thresh=DETECT_MIN_THRESH,
    )
    logger.info("Image visualization completed.")
    return image_with_detections


def infer_single_image(image_file, model_dir):
    """Performs inference on a single image file and returns detection results."""
    output_dir = os.path.join(os.path.dirname(image_file), OUTPUT_SUBDIR)
    output_path = os.path.join(output_dir, os.path.basename(image_file) + ".npy")
    if os.path.exists(output_path) and not OVERWITE_DETECTION:
        logger.info(f"{output_path} exists, skipping detection")
        return None

    input_tensor, (height, width, _) = process_image(image_file)
    input_tensor = tf.expand_dims(input_tensor, axis=0)
    if input_tensor is None:
        logger.info(f"Processing image {output_path} failed, skipping detection")
        return None  # Skip if image processing failed

    try:
        model = get_model(model_dir)  # Retrieve thread-specific model instance
        output_results = model.signatures["serving_default"](input_tensor)
        num_detections = int(output_results["num_detections"][0])
        np_boxes = output_results["detection_boxes"][0, :num_detections]
        np_scores = output_results["detection_scores"][0, :num_detections].numpy()
        np_classes = (
            output_results["detection_classes"][0, :num_detections].numpy().astype(int)
        )
        np_attributes = output_results.get("detection_attributes", None)

        # Adjust bounding boxes
        np_image_info = output_results["image_info"][0]
        np_boxes = adjust_boxes(np_boxes, np_image_info, width, height)

        # Process masks if available
        np_masks, encoded_masks = process_masks(np_boxes, output_results, height, width)

        # Visualization
        # image_with_detections = visualize_detections(
        #     input_tensor[0].numpy(),
        #     np_boxes,
        #     np_classes,
        #     np_scores,
        #     label_map_dict,
        #     np_masks,
        # )

        out = {
            "image_file": image_file,
            "boxes": np_boxes,
            "classes": np_classes,
            "scores": np_scores,
            "attributes": np_attributes.numpy() if np_attributes is not None else None,
            "masks": encoded_masks,
            # "visualized_image": image_with_detections,
        }

        logger.info(f"Inference completed for {image_file}")
        return out

    except Exception as e:
        logger.error(f"Error during inference on {image_file}: {e}")
        return None


def save_detection(result):
    """Saves the visualized image back to the original folder or a subdirectory."""
    # Define the output path, using the original directory with a subdirectory for processed files
    image_file = result["image_file"]
    output_dir = os.path.join(os.path.dirname(image_file), OUTPUT_SUBDIR)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, os.path.basename(image_file))

    np.save(output_path, result)
    logger.info(f"Saved detection output to {output_path}")

    # # Convert array to image and save
    # visualized_image = Image.fromarray(result)
    # visualized_image.save(output_path)
    # logger.info(f"Saved visualized image to {output_path}")


def main():
    # # Load the model
    # global MODEL
    # MODEL = tf.saved_model.load(MODEL_DIR)

    # label_map_dict = read_labels()
    # image_pattern = "details/**/**/images/*.[jp][pn]g"
    image_pattern = os.path.join(ROOT_DIR, "details/**/**/images/*.[jp][pn]g")
    image_files = glob.glob(image_pattern)
    results_lock = threading.Lock()
    results = [0]

    # Run inference with a ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            # executor.submit(infer_single_image, image_file, label_map_dict, MODEL): image_file
            executor.submit(infer_single_image, image_file, MODEL_DIR): image_file
            for image_file in image_files
        }
        for future in tqdm(futures, desc="Processing images"):
            result = future.result()

            if result:
                save_detection(result)
                with results_lock:
                    results[0] += 1

    logger.info(f"Processed {results[0]} images")


if __name__ == "__main__":

    start_time = time.time()

    logger.info("Starting detection process")

    main()

    logger.info(
        f"Completed detection process. Execution time: {timedelta(seconds=time.time() - start_time)}"
    )
