"""Vision captioning utilities."""

from app.pipeline.ocr import run_ocr
import re


def simple_caption(image_path):
	"""Generate a simple caption for an image by combining OCR text and a brief heuristic description.

	This is a light-weight fallback captioner: it reports detected text and any extracted numbers.
	"""
	ocr_res = None
	try:
		ocr_res = run_ocr(image_path)
	except Exception:
		ocr_res = {"lines": [], "raw": None}

	lines = ocr_res.get("lines", [])
	text_blob = " ".join(lines)

	# find numbers in the OCR output
	numbers = re.findall(r"\d+[\d,\.]*", text_blob)

	caption_parts = []
	if lines:
		caption_parts.append("Detected text: '" + (lines[0] if lines else "") + "'")
	else:
		caption_parts.append("No text detected")

	if numbers:
		caption_parts.append("Numbers found: " + ", ".join(numbers))

	# simple visual description fallback
	if not lines:
		caption_parts.append("Image appears to be a scanned page or graphic.")

	caption = ". ".join(caption_parts)
	return {"caption": caption, "ocr_lines": lines}
