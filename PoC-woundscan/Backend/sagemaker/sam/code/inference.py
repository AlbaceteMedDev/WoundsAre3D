"""SAM ViT-B inference handler for the SageMaker Hugging Face PyTorch (CPU) container.

Request  (application/json):
    {"image": <base64 JPEG/PNG>, "points": [[x, y], ...], "labels": [1, ...],
     "multimask_output": true}
    Point coordinates are in pixels of the submitted image.
Response (application/json):
    {"masks": [<base64 PNG, 0/255, same size as the input image>, ...],
     "scores": [<predicted IoU>, ...], "size": [w, h], "seconds": t}
"""

import base64
import io
import json
import os
import time

import numpy as np
import torch
from PIL import Image
from transformers import SamModel, SamProcessor

torch.set_num_threads(max(1, os.cpu_count() or 1))


def model_fn(model_dir, context=None):
    model = SamModel.from_pretrained(model_dir, torch_dtype=torch.float32).eval()
    processor = SamProcessor.from_pretrained(model_dir)
    return {"model": model, "processor": processor}


def _png(mask):
    buf = io.BytesIO()
    Image.fromarray(mask.astype(np.uint8) * 255).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def transform_fn(model, input_data, content_type, accept, context=None):
    t0 = time.time()
    if isinstance(input_data, (bytes, bytearray)):
        input_data = input_data.decode("utf-8")
    req = json.loads(input_data)
    image = Image.open(io.BytesIO(base64.b64decode(req["image"]))).convert("RGB")
    points = req.get("points") or [[image.width / 2, image.height / 2]]
    labels = req.get("labels") or [1] * len(points)
    multimask = bool(req.get("multimask_output", True))

    proc, net = model["processor"], model["model"]
    inputs = proc(image, input_points=[[points]], input_labels=[[labels]], return_tensors="pt")
    with torch.inference_mode():
        out = net(**inputs, multimask_output=multimask)
    masks = proc.image_processor.post_process_masks(
        out.pred_masks, inputs["original_sizes"], inputs["reshaped_input_sizes"])[0][0]   # (k, H, W) bool
    scores = out.iou_scores[0, 0].tolist()
    body = {
        "masks": [_png(m.numpy()) for m in masks],
        "scores": [round(float(s), 4) for s in scores],
        "size": [image.width, image.height],
        "seconds": round(time.time() - t0, 2),
    }
    return json.dumps(body), "application/json"
