"""OCR utilities."""

from pathlib import Path

try:
	from paddleocr import PaddleOCR
except Exception:
	PaddleOCR = None
try:
	import easyocr
except Exception:
	easyocr = None


def run_ocr(image_path, lang="en"):
	"""Run OCR on an image and return a list of text lines.

	Returns a dict with `lines` (list of strings) and `raw` (full raw OCR result).
	"""
	image_path = Path(image_path)
	if PaddleOCR is None:
		raise RuntimeError("paddleocr is not installed in the environment")

	# Some paddleocr versions do not accept `show_log`; avoid passing it.
	try:
		ocr = PaddleOCR(lang=lang, use_angle_cls=True)
		result = ocr.ocr(str(image_path), cls=True)
		lines = []
		for page in result:
			for line in page:
				try:
					text = line[1][0]
				except Exception:
					text = ""
				if text:
					lines.append(text)
		return {"lines": lines, "raw": result}
	except Exception:
		# fallback to EasyOCR if available
		if easyocr is None:
			raise
		reader = easyocr.Reader([lang], gpu=False)
		res = reader.readtext(str(image_path))
		lines = [t[-2] for t in res]
		return {"lines": lines, "raw": res}
