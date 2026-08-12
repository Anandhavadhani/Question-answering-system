from PIL import Image, ImageDraw, ImageFont
import pathlib, requests, time

base = pathlib.Path(__file__).parent
scanned_path = base / 'scanned_img.png'
chart_pdf = base / 'chart.pdf'

# create a scanned-like image (just text rasterized)
img = Image.new('RGB', (800, 400), color='white')
d = ImageDraw.Draw(img)
# draw some text but as rasterized image
try:
    f = ImageFont.truetype('arial.ttf', 24)
except Exception:
    f = None
lines = ["This is a scanned document.", "No selectable text present.", "Invoice # 12345", "Total: $1,234.56"]
y = 50
for L in lines:
    d.text((50, y), L, fill='black', font=f)
    y += 40
img.save(scanned_path)
print('Created scanned image', scanned_path.exists())

# upload scanned image
url = 'http://127.0.0.1:8000/documents/upload'
with open(scanned_path, 'rb') as f:
    r = requests.post(url, files={'file': ('scanned_img.png', f, 'image/png')})
print('upload status', r.status_code)
print(r.json())

# create a PDF with a chart-like image that has numbers
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
c = canvas.Canvas(str(chart_pdf), pagesize=letter)
# draw a simple bar chart and numbers
c.setFont('Helvetica', 12)
c.drawString(100, 700, 'Sample Chart')
# bars
data = [100, 230, 180]
x = 100
for v in data:
    c.rect(x, 500, 40, v/1.5, fill=1)
    c.drawString(x, 480, str(v))
    x += 80
c.save()
print('Created chart PDF', chart_pdf.exists())

# upload chart PDF
with open(chart_pdf, 'rb') as f:
    r2 = requests.post(url, files={'file': ('chart.pdf', f, 'application/pdf')})
print('upload status', r2.status_code)
resp = r2.json()
print('pdf resp keys', resp.keys())
items = resp.get('ingestion_items', [])
print('items count', len(items))
# find captions via captioning simple (not stored) - our ingestion doesn't run captioning for PDFs yet
# but embedded images should be extracted and present
embedded = [it for it in items if it['type']=='embedded_image']
print('embedded images count', len(embedded))
if embedded:
    print('embedded example', embedded[0])

print('Done')
