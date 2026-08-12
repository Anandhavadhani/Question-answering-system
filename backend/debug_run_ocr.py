import traceback
from pathlib import Path

from app.pipeline.ocr import run_ocr

p = Path(__file__).parent / 'scanned_img.png'
print('exists', p.exists(), str(p))
try:
    res = run_ocr(p)
    print('OCR result:', res)
except Exception as e:
    print('OCR exception:')
    traceback.print_exc()
