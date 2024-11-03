import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import glob
import numpy as np
import tensorflow as tf
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from dotenv import load_dotenv
from utils import mask_utils, box_utils
from utils.object_detection import visualization_utils
from pycocotools import mask as mask_api
from processing.logger import logger

# Load environment variables
load_dotenv()

# Environment variables
LABEL_MAP_DIR = os.getenv("LABEL_MAP_DIR")
LABEL_MAP_FILE = os.getenv("LABEL_MAP_FILE")
MODEL_DIR = os.getenv("MODEL_DIR")

DETECT_MAX_BOXES = os.getenv("DETECT_MAX_BOXES")
DETECT_MIN_THRESH = os.getenv("DETECT_MIN_THRESH")

# Load the model
MODEL = tf.saved_model.load(MODEL_DIR)


def read_labels():
    """Reads the label map file and returns a dictionary of labels."""
    label_map_dict = {}
    label_map_path = os.path.join(LABEL_MAP_DIR, LABEL_MAP_FILE)

    try:
        with open(label_map_path, "r") as file:
            lines = file.readlines()
            for line in lines:
                key, value = line.strip().split(":")
                label_map_dict[int(key)] = {"id": int(key), "name": value.strip()}
        logger.info("Label map loaded successfully.")
    except Exception as e:
        logger.error(f"Error reading label map: {e}")

    return label_map_dict


def process_image(image_file):
    """Processes an image file and returns it as a tensor."""
    try:
        image = Image.open(image_file).convert("RGB")
        image_array = np.array(image)[:, :, :3]  # Remove alpha channel
        # input_tensor = tf.convert_to_tensor(image_array[np.newaxis, :, :, :], dtype=tf.uint8)
        input_tensor = tf.convert_to_tensor(image_array, dtype=tf.uint8)
        logger.info(f"Processed image {image_file}")
        return input_tensor, image_array.shape
    except Exception as e:
        logger.error(f"Error processing image {image_file}: {e}")
        return None, None


def adjust_boxes(np_boxes, image_info, width, height):
    """Adjusts bounding boxes to the dimensions of the image."""
    np_boxes = np_boxes / np.tile(image_info[1:2, :], (1, 2))
    ymin, xmin, ymax, xmax = np.split(np_boxes, 4, axis=-1)
    ymin *= height
    ymax *= height
    xmin *= width
    xmax *= width
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
    image_array, np_boxes, np_classes, np_scores, label_map_dict, np_masks
):
    """Visualizes bounding boxes and labels on the image array."""
    image_with_detections = (
        visualization_utils.visualize_boxes_and_labels_on_image_array(
            image_array,
            np_boxes,
            np_classes,
            np_scores,
            label_map_dict,
            instance_masks=np_masks,
            use_normalized_coordinates=False,
            max_boxes_to_draw=DETECT_MAX_BOXES,
            min_score_thresh=DETECT_MIN_THRESH,
        )
    )
    logger.info("Image visualization completed.")
    return image_with_detections


def infer_single_image(image_file, label_map_dict):
    """Performs inference on a single image file and returns detection results."""
    input_tensor, (height, width, _) = process_image(image_file)
    if input_tensor is None:
        return None  # Skip if image processing failed

    try:
        output_results = MODEL.signatures["serving_default"](input_tensor)
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

        logger.info(f"Inference completed for {image_file}")
        return {
            "image_file": image_file,
            "boxes": np_boxes,
            "classes": np_classes,
            "scores": np_scores,
            "attributes": np_attributes.numpy() if np_attributes is not None else None,
            "masks": encoded_masks,
            # "visualized_image": image_with_detections,
        }

    except Exception as e:
        logger.error(f"Error during inference on {image_file}: {e}")
        return None


def save_visualized_image(image_array, image_file, output_subdir="processed"):
    """Saves the visualized image back to the original folder or a subdirectory."""
    # Define the output path, using the original directory with a subdirectory for processed files
    output_dir = os.path.join(os.path.dirname(image_file), output_subdir)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, os.path.basename(image_file))

    # # Convert array to image and save
    # visualized_image = Image.fromarray(image_array)
    # visualized_image.save(output_path)
    # logger.info(f"Saved visualized image to {output_path}")

    np.save(image_array, output_path)
    logger.info(f"Saved detection output to {output_path}")


def main():
    label_map_dict = read_labels()
    image_pattern = "../details/**/**/*.[jp][pn]g"
    image_files = glob.glob(image_pattern, recursive=True)
    results = []

    # Run inference with a ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(infer_single_image, image_file, label_map_dict): image_file
            for image_file in image_files
        }
        for future in tqdm(futures, desc="Processing images"):
            result = future.result()
            save_visualized_image(result, result["image_file"])

            # if result and "visualized_image" in result:
            #     # Save the visualized image to the output path
            #     # save_visualized_image(result["visualized_image"], result["image_file"])
            # elif result:
            #     logger.warning(
            #         f"No visualized image found in the result for {result['image_file']}"
            #     )

    logger.info(f"Processed {len(results)} images")
    # Optionally: save or process `results` as needed


if __name__ == "__main__":
    main()
