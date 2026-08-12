import fitz
from PIL import Image, ImageDraw
import pathlib
import requests
import time

base = pathlib.Path(__file__).parent
pdf_path = base / "sample3.pdf"
img_path = base / "temp_img.png"

# create a small embedded image
img = Image.new("RGB", (300, 150), color=(30, 120, 200))
d = ImageDraw.Draw(img)
d.text((10, 60), "Embedded Image", fill=(255, 255, 255))
img.save(img_path)

# create 3-page PDF with native text and embed image on page 2
doc = fitz.open()
for i in range(3):
    page = doc.new_page()
    text = f"Native text on page {i+1}. This is sample content to validate extraction."
    rect = fitz.Rect(50, 50, 550, 150)
    page.insert_textbox(rect, text, fontsize=12)
    if i == 1:
        # insert the image on page 2
        img_rect = fitz.Rect(50, 200, 350, 350)
        page.insert_image(img_rect, filename=str(img_path))

doc.save(str(pdf_path))
print("Created sample PDF:", pdf_path.exists(), str(pdf_path))

# wait a moment to ensure server is up
time.sleep(0.5)

url = "http://127.0.0.1:8000/documents/upload"
with open(pdf_path, "rb") as f:
    resp = requests.post(url, files={"file": ("sample3.pdf", f, "application/pdf")})

print("Upload status:", resp.status_code)
try:
    data = resp.json()
except Exception:
    print("Response text:\n", resp.text)
    raise

print("Response keys:", list(data.keys()))

doc_id = data.get("doc_id")
items = data.get("ingestion_items", [])
print(f"doc_id={doc_id} items_count={len(items)}")

# print native text items
for it in items:
    if it.get("type") == "native_text":
        print(f"PAGE {it['page_number']} needs_ocr={it['needs_ocr']} text_len={len(it['text'])}")
        print(it['text'])

page_images = [i for i in items if i.get("type") == "page_image"]
embedded_images = [i for i in items if i.get("type") == "embedded_image"]
print("page_images count", len(page_images))
print("embedded_images count", len(embedded_images))

# verify files on disk
image_base = base / "data" / "images" / (doc_id or "")
page_dir = image_base / "pages"
embedded_dir = image_base / "embedded"
print("page_dir exists", page_dir.exists())
print("embedded_dir exists", embedded_dir.exists())
if page_dir.exists():
    files = sorted(page_dir.iterdir())
    print("page files:")
    for p in files:
        print(" -", p.name)
if embedded_dir.exists():
    files = sorted(embedded_dir.iterdir())
    print("embedded files:")
    for p in files:
        print(" -", p.name)

print("Done.")
