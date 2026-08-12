import uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from app.pipeline.ocr import run_ocr
from app.pipeline.captioning import simple_caption
from app.pipeline.ingestion import ingest_document

base = Path(__file__).parent
scanned = base / 'scanned_img.png'
print('Running OCR on', scanned)
ocr_res = run_ocr(scanned)
print('OCR lines:')
for l in ocr_res['lines']:
    print(' -', l)

# create a raster chart image with numbers
chart_img = base / 'chart_img.png'
img = Image.new('RGB', (600, 300), 'white')
d = ImageDraw.Draw(img)
try:
    f = ImageFont.truetype('arial.ttf', 20)
except Exception:
    f = None
# draw bars and numbers
values = [120, 260, 190]
x = 50
for v in values:
    d.rectangle([x, 200 - v//1, x+80, 200], fill=(30,144,255))
    d.text((x+10, 200 - v//1 - 25), str(v), fill='black', font=f)
    x += 110
# add title
d.text((50, 20), 'Revenue by Quarter (k$)', fill='black', font=f)
img.save(chart_img)
print('Created chart image', chart_img)

# embed chart image into PDF
pdf_path = base / 'chart_with_image.pdf'
import fitz
doc = fitz.open()
page = doc.new_page()
rect = fitz.Rect(50, 50, 550, 350)
page.insert_image(rect, filename=str(chart_img))
doc.save(str(pdf_path))
print('Saved PDF with embedded image', pdf_path)

# ingest PDF locally
doc_id = str(uuid.uuid4())
items = ingest_document(doc_id, pdf_path)
print('Ingestion produced', len(items), 'items')
embedded = [it for it in items if it['type']=='embedded_image']
print('Embedded images found:', len(embedded))
for e in embedded:
    print(' -', e['image_path'])
    cap = simple_caption(e['image_path'])
    print(' Caption:', cap['caption'])
    print(' OCR lines:', cap['ocr_lines'])
