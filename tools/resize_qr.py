from PIL import Image
from pathlib import Path

SRC = Path("InstacartApp/instacart_repo_qr.png")
OUT = Path("InstacartApp/instacart_repo_qr_small.png")
TARGET_WIDTH = 220

if not SRC.exists():
    raise FileNotFoundError(f"Source not found: {SRC}")

img = Image.open(SRC)
# preserve aspect ratio
w, h = img.size
new_w = TARGET_WIDTH
new_h = int(new_w * h / w)
img_small = img.resize((new_w, new_h), Image.LANCZOS)
img_small.save(OUT)
print(f"Wrote resized image -> {OUT}")
