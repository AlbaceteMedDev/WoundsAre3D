"""Build the SAM ViT-B model artifact for SageMaker: build/model.tar.gz

    python build_model.py

Downloads facebook/sam-vit-base (Apache-2.0) from Hugging Face (~375 MB) unless
already cached in build/model/, then packs it with code/inference.py in the
layout the Hugging Face inference container expects:

    model.tar.gz
    |-- config.json, preprocessor_config.json, model.safetensors
    `-- code/inference.py

CDK (AIMLStack) uploads the tarball as an asset and points the SageMaker model at it.
"""

import os
import tarfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
MODEL_DIR = os.path.join(BUILD, "model")
REPO = "facebook/sam-vit-base"
FILES = ["config.json", "preprocessor_config.json", "model.safetensors"]


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    for f in FILES:
        dst = os.path.join(MODEL_DIR, f)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            continue
        url = f"https://huggingface.co/{REPO}/resolve/main/{f}"
        print("downloading", url)
        urllib.request.urlretrieve(url, dst)
    out = os.path.join(BUILD, "model.tar.gz")
    with tarfile.open(out, "w:gz") as tar:
        for f in FILES:
            tar.add(os.path.join(MODEL_DIR, f), arcname=f)
        tar.add(os.path.join(HERE, "code", "inference.py"), arcname="code/inference.py")
    print("wrote", out, os.path.getsize(out) // (1 << 20), "MB")


if __name__ == "__main__":
    main()
