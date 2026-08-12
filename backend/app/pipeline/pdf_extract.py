"""PDF extraction utilities."""

from pathlib import Path

import fitz


def extract_native_text(pdf_path):
    """Extract native text from every page of a PDF.

    Returns a list of dicts with page_number, text, and needs_ocr.
    A page is marked as needing OCR when its native text is empty or near-empty.
    """
    pdf_path = Path(pdf_path)
    results = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            text = page.get_text() or ""
            stripped_text = text.strip()
            needs_ocr = len(stripped_text) < 20
            results.append(
                {
                    "page_number": page_index,
                    "text": text,
                    "needs_ocr": needs_ocr,
                }
            )
    return results


def render_pages(pdf_path, output_dir, dpi=200):
    """Render each PDF page to a PNG image at the requested DPI.

    Returns a list of dicts with page_number and image_path.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    with fitz.open(pdf_path) as doc:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for page_index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image_path = output_dir / f"page_{page_index}.png"
            pix.save(str(image_path))
            results.append(
                {
                    "page_number": page_index,
                    "image_path": str(image_path),
                }
            )
    return results


def extract_embedded_images(pdf_path, output_dir):
    """Extract embedded raster images from every PDF page.

    Returns a list of dicts with page_number and image_path.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            images = page.get_images(full=True)
            for image_index, image_info in enumerate(images, start=1):
                xref = image_info[0]
                image_data = doc.extract_image(xref)
                if not image_data:
                    continue
                image_bytes = image_data.get("image")
                image_ext = image_data.get("ext", "png")
                image_path = output_dir / f"page_{page_index}_image_{image_index}.{image_ext}"
                Path(image_path).write_bytes(image_bytes)
                results.append(
                    {
                        "page_number": page_index,
                        "image_path": str(image_path),
                    }
                )
    return results
