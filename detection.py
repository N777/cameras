import cv2
import json
from ultralytics import YOLO

ETALON_MODEL_PATH = "yolo11m.pt"
DETECT_MODEL_PATH = "yolo11n.pt"


# ------------------------------------------------------
# IoU calculation
# ------------------------------------------------------
def iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])

    union = area1 + area2 - inter
    return inter / union if union > 0 else 0


# ------------------------------------------------------
# Draw bounding box
# ------------------------------------------------------
def draw_bbox(image, box, label, color):
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
    cv2.putText(image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


# ------------------------------------------------------
# Detect cars with YOLO
# ------------------------------------------------------
def detect_cars(model, image):
    results = model(image)[0]
    car_boxes = []

    for box in results.boxes:
        if int(box.cls[0]) == 2:  # class "car"
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            car_boxes.append([x1, y1, x2, y2])

    return car_boxes


# ------------------------------------------------------
# Normalize boxes
# ------------------------------------------------------
def normalize_boxes(boxes, w, h):
    normalized = []
    for x1, y1, x2, y2 in boxes:
        normalized.append([x1 / w, y1 / h, x2 / w, y2 / h])
    return normalized


# ------------------------------------------------------
# Denormalize boxes
# ------------------------------------------------------
def denormalize_boxes(boxes_norm, w, h):
    restored = []
    for x1, y1, x2, y2 in boxes_norm:
        restored.append([x1 * w, y1 * h, x2 * w, y2 * h])
    return restored


# ------------------------------------------------------
# Save reference JSON
# ------------------------------------------------------
def save_reference_json(json_path, ref_w, ref_h, normalized_boxes):
    data = {
        "reference_width": ref_w,
        "reference_height": ref_h,
        "parking_boxes": normalized_boxes,
    }

    with open(json_path, "w") as f:
        json.dump(data, f)

    print(f"[OK] Saved reference to {json_path}")


# ------------------------------------------------------
# Load reference JSON
# ------------------------------------------------------
def load_reference_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    return data["reference_width"], data["reference_height"], data["parking_boxes"]


# ------------------------------------------------------
# Extract reference boxes from image + save JSON
# ------------------------------------------------------
def create_reference(ref_img, output_json):
    model = YOLO(ETALON_MODEL_PATH)

    ref_h, ref_w = ref_img.shape[:2]

    # detect cars on reference image
    ref_boxes = detect_cars(model, ref_img)

    # convert to normalized coordinates
    ref_boxes_norm = normalize_boxes(ref_boxes, ref_w, ref_h)

    for box in ref_boxes:
        draw_bbox(ref_img, box, "Parking", (0, 255, 0))

    save_reference_json(output_json, ref_w, ref_h, ref_boxes_norm)

    return ref_img


# ------------------------------------------------------
# Detect free spaces using saved reference JSON
# ------------------------------------------------------
def detect_free_spaces(reference_json, cur_img):
    model = YOLO(DETECT_MODEL_PATH)

    # load parking-space reference
    ref_w, ref_h, ref_boxes_norm = load_reference_json(reference_json)

    cur_h, cur_w = cur_img.shape[:2]

    # denormalize boxes to current resolution
    parking_spaces = denormalize_boxes(ref_boxes_norm, cur_w, cur_h)

    # detect current cars
    cur_boxes = detect_cars(model, cur_img)

    free_spaces = []

    # compare each parking space to current cars
    for p in parking_spaces:
        max_iou = 0
        for c in cur_boxes:
            max_iou = max(max_iou, iou(p, c))

        if max_iou < 0.15:
            free_spaces.append(p)

    # draw results
    # for box in parking_spaces:
    #     draw_bbox(cur_img, box, "Parking", (0, 255, 0))

    for box in free_spaces:
        draw_bbox(cur_img, box, "FREE", (0, 0, 255))

    return cur_img

def init_model():
    YOLO(DETECT_MODEL_PATH)
    YOLO(ETALON_MODEL_PATH)

# ------------------------------------------------------
# MAIN
# ------------------------------------------------------
if __name__ == "__main__":
    create_reference()
