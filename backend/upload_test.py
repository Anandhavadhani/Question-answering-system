from pathlib import Path
import requests
import fitz

base = Path(r'e:/multimodel_rag/backend')
file_path = base / 'sample.pdf'

# Create a valid 3-page PDF with native text on every page and one embedded image on page 2.
doc = fitz.open()
for i in range(3):
    page = doc.new_page()
    page.insert_text((72, 72), f'Page {i+1} native text content. This is a test PDF page.', fontsize=14)

pix = fitz.Pixmap(fitz.csRGB, 100, 100)
pix.clear_with(0xFF0000)
page = doc[1]
page.insert_image((72, 120, 172, 220), pixmap=pix)
pix = None

doc.save(str(file_path))
doc.close()
print('Created sample PDF:', file_path.exists())
print('File size:', file_path.stat().st_size)

url = 'http://127.0.0.1:8000/documents/upload'
with file_path.open('rb') as f:
    r = requests.post(url, files={'file': ('sample.pdf', f, 'application/pdf')})
print('Upload status:', r.status_code)
print('Upload response:', r.text)

if r.ok:
    data = r.json()
    items = data.get('ingestion_items', [])
    native_texts = [item for item in items if item['type'] == 'native_text']
    page_images = [item for item in items if item['type'] == 'page_image']
    embedded_images = [item for item in items if item['type'] == 'embedded_image']

    print('native_text count:', len(native_texts))
    for item in native_texts:
        print('page', item['page_number'], 'needs_ocr', item['needs_ocr'])
        print('text snippet:', repr(item['text'][:120]))

    print('page_image count:', len(page_images))
    for item in page_images:
        print('page', item['page_number'], 'image_path', item['image_path'])

    print('embedded_image count:', len(embedded_images))
    for item in embedded_images:
        print('page', item['page_number'], 'image_path', item['image_path'])

    for item in page_images + embedded_images:
        p = Path(item['image_path'])
        print('exists', p.exists(), str(p))
