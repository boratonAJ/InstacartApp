from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path("InstacartApp/architecture/instacart_arch.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

W, H = 1200, 800
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
except Exception:
    font = ImageFont.load_default()
    font_bold = font

# helper to draw rectangles with title and items
def draw_box(x, y, w, h, title, items):
    d.rounded_rectangle([x, y, x + w, y + h], radius=8, outline="#333", width=2, fill="#f7f9fb")
    d.text((x + 10, y + 8), title, fill="#111", font=font_bold)
    oy = y + 36
    for it in items:
        d.text((x + 14, oy), u"• " + it, fill="#222", font=font)
        oy += 20

# draw boxes
draw_box(40, 40, 320, 140, "Data Layer", ["orders.csv", "products.csv", "order_products__prior.csv", "aisles.csv", "departments.csv"]) 

draw_box(420, 40, 320, 100, "Ingestion / Storage", ["Parquet / Local FS", "Optional: Postgres/SQLite"]) 

draw_box(40, 220, 700, 180, "Preprocessing & Feature Engineering", ["Join & Clean", "Derived Features (user/product)", "Sequence Embeddings (RNN/SGNS)"]) 

draw_box(40, 420, 700, 180, "Modeling", ["LightGBM / XGBoost", "Neural Nets", "Sequence Models", "Blending / Stacking"]) 

draw_box(780, 220, 340, 180, "Evaluation & Serving", ["Validation & CV", "Metrics: F1 / AUC", "Flask App / Batch Scoring"]) 

# arrows
def arrow(p1, p2):
    d.line([p1, p2], fill="#333", width=2)
    # arrow head
    ax, ay = p2
    d.polygon([(ax, ay), (ax-8, ay-10), (ax-8, ay+10)], fill="#333")

arrow((200, 180), (200, 220))  # data layer down to preprocessing
arrow((580, 80), (580, 220))   # ingestion down to preprocessing
arrow((400, 340), (400, 420))  # preprocessing to modeling
arrow((560, 420), (880, 340))  # modeling to serving

# title
d.text((380, 10), "High-level Architecture: Instacart Modeling Pipeline", fill="#111", font=font_bold)

img.save(OUT)
print(f"Wrote {OUT}")
