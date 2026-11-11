"""Greyscale output sets for SAM segmentation (same SAM call + post-processing as SEGMENT).

Writes one folder per set, plus a contact sheet:
    set1_gray_photo/    greyscale photo (1024-px long side)
    set2_sam_mask/      SAM wound mask, 255 = wound, 0 = non-wound (LUTSeg Wound_Masks format)
    set3_expert_mask/   expert wound mask, same format (real images only)
    set4_agreement/     255 = both wound, 170 = SAM only, 85 = expert only, 0 = neither (real only)
    set5_gray_highlight/ greyscale photo, wound full brightness, non-wound dimmed to 35 %

Real images use the prompt on the wound (as if centred under the app's reticle);
phantoms use the image-centre prompt exactly like the pipeline.

    python sam_gray_sets.py OUT_DIR --real "IMG|MASK" ... --phantom IMG ...
"""

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw

import sam_demo as d

SETS = ["set1_gray_photo", "set2_sam_mask", "set3_expert_mask", "set4_agreement", "set5_gray_highlight"]
LABELS = ["1 grey photo", "2 SAM mask", "3 expert mask", "4 agreement", "5 highlight"]
THUMB_H = 220


def save(out, s, name, arr):
    Image.fromarray(arr.astype(np.uint8), "L").save(os.path.join(out, s, os.path.splitext(name)[0] + ".png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--real", nargs="*", default=[])
    ap.add_argument("--phantom", nargs="*", default=[])
    a = ap.parse_args()
    for s in SETS:
        os.makedirs(os.path.join(a.out, s), exist_ok=True)

    items = [(spec.split("|")[0], spec.split("|")[1]) for spec in a.real] + [(p, None) for p in a.phantom]
    sheet_rows = []
    for ip, mp in items:
        img, jpeg = d.prep(ip)
        name = os.path.basename(ip).replace(" ", "_")
        w, h = img.size
        gray = np.asarray(img.convert("L"))
        gt = None
        if mp:
            gt = np.asarray(Image.open(mp).convert("L").resize(img.size, Image.NEAREST)) > 127
            ys, xs = np.nonzero(gt)
            k = int(np.argmin((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2))
            pt = (float(xs[k]), float(ys[k]))
        else:
            pt = (w / 2, h / 2)
        m, score, _ = d.segment(jpeg, (h, w), pt)
        sam = m if m is not None else np.zeros((h, w), bool)

        out = {"set1_gray_photo": gray, "set2_sam_mask": sam * 255}
        if gt is not None:
            out["set3_expert_mask"] = gt * 255
            agree = np.zeros((h, w), np.uint8)
            agree[gt & ~sam] = 85
            agree[sam & ~gt] = 170
            agree[sam & gt] = 255
            out["set4_agreement"] = agree
        out["set5_gray_highlight"] = np.where(sam, gray, gray * 0.35)
        for s, arr in out.items():
            save(a.out, s, name, arr)

        thumbs = []
        for s, lab in zip(SETS, LABELS):
            arr = out.get(s)
            t = Image.new("L", (int(THUMB_H * w / h), THUMB_H + 22), 255)
            if arr is not None:
                t.paste(Image.fromarray(arr.astype(np.uint8), "L").resize((t.width, THUMB_H), Image.LANCZOS), (0, 22))
            else:
                ImageDraw.Draw(t).text((8, THUMB_H // 2), "n/a (no expert mask)", fill=120, font=d.font(13))
            ImageDraw.Draw(t).text((4, 3), lab, fill=0, font=d.font(14))
            thumbs.append(t)
        cap = Image.new("L", (190, THUMB_H + 22), 255)
        dr = ImageDraw.Draw(cap)
        dr.text((6, 30), name[:24], fill=0, font=d.font(14))
        info = f"IoU {d.iou(sam, gt):.2f}" if gt is not None else "phantom"
        dr.text((6, 52), info, fill=80, font=d.font(13))
        dr.text((6, 72), f"SAM score {score or 0:.2f}", fill=80, font=d.font(13))
        sheet_rows.append([cap] + thumbs)
        print(f"{name:28s} {info}", flush=True)

    pad = 6
    widths = [max(r[i].width for r in sheet_rows) for i in range(len(sheet_rows[0]))]
    H = sum(r[0].height for r in sheet_rows) + pad * (len(sheet_rows) + 1)
    sheet = Image.new("L", (sum(widths) + pad * (len(widths) + 1), H), 225)
    y = pad
    for r in sheet_rows:
        x = pad
        for t, cw in zip(r, widths):
            sheet.paste(t, (x, y))
            x += cw + pad
        y += r[0].height + pad
    sheet.save(os.path.join(a.out, "gray_sets_sheet.png"))
    print("wrote", os.path.join(a.out, "gray_sets_sheet.png"), sheet.size)


if __name__ == "__main__":
    main()
