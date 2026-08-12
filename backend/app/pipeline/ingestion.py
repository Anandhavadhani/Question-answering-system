"""Document ingestion orchestration module.

Per request: this module now performs OCR (when needed), captioning,
chunking of native/ocr text, embedding of chunks and captions, and
saving of items to MongoDB.
"""

from pathlib import Path
from uuid import uuid4
from typing import List

from app.pipeline.pdf_extract import (
    extract_embedded_images,
    extract_native_text,
    render_pages,
)
from app.pipeline.ocr import run_ocr
from app.pipeline.captioning import simple_caption
from app.pipeline.chunking import chunk_text
from app.pipeline.embedding import embed_texts
from app.db.mongo import save_items


IMAGE_DIR = Path(__file__).resolve().parents[2] / "data" / "images"


def ingest_document(doc_id: str, file_path: str):
    """Ingest a PDF: extract text/images, chunk, embed, and save to MongoDB.

    Returns a list of saved item summaries.
    """
    file_path = Path(file_path)
    if file_path.suffix.lower() != ".pdf":
        raise ValueError("ingest_document currently supports PDF files only.")

    page_image_dir = IMAGE_DIR / doc_id / "pages"
    embedded_image_dir = IMAGE_DIR / doc_id / "embedded"

    native_text_items = extract_native_text(file_path)
    page_image_items = render_pages(file_path, page_image_dir, dpi=200)
    embedded_image_items = extract_embedded_images(file_path, embedded_image_dir)

    # map page -> image path for easy lookup
    page_to_image = {p["page_number"]: p["image_path"] for p in page_image_items}

    # Collect items to be embedded and saved
    items_to_save: List[dict] = []
    texts_for_embedding: List[str] = []
    embed_targets: List[dict] = []  # parallel list mapping embeddings -> items

    # Process native text pages: chunk and prepare embeddings
    for nt in native_text_items:
        page = nt.get("page_number")
        text = nt.get("text", "")
        source_item_id = str(uuid4())
        if (text or "").strip():
            chunks = chunk_text(text, page, source_item_id)
            for c in chunks:
                item_id = str(uuid4())
                itm = {
                    "item_id": item_id,
                    "type": "native_text",
                    "text": c["text"],
                    "metadata": {"page": c["page_number"], "source_file": file_path.name, "chunk_index": c["chunk_index"]},
                    "image_path": None,
                }
                items_to_save.append(itm)
                texts_for_embedding.append(c["text"])
                embed_targets.append(itm)

    # Process OCR for pages that need it (or where native text was near-empty)
    for nt in native_text_items:
        if not nt.get("needs_ocr"):
            continue
        page = nt.get("page_number")
        image_path = page_to_image.get(page)
        if not image_path:
            continue
        try:
            ocr_res = run_ocr(image_path)
            lines = ocr_res.get("lines", [])
            ocr_text = "\n".join(lines)
        except Exception:
            ocr_text = ""

        if ocr_text.strip():
            source_item_id = str(uuid4())
            chunks = chunk_text(ocr_text, page, source_item_id)
            for c in chunks:
                item_id = str(uuid4())
                itm = {
                    "item_id": item_id,
                    "type": "ocr_text",
                    "text": c["text"],
                    "metadata": {"page": c["page_number"], "source_file": file_path.name, "chunk_index": c["chunk_index"]},
                    "image_path": image_path,
                }
                items_to_save.append(itm)
                texts_for_embedding.append(c["text"])
                embed_targets.append(itm)

    # Process captions for page images
    for p in page_image_items:
        page = p.get("page_number")
        image_path = p.get("image_path")
        try:
            cap_res = simple_caption(image_path)
            caption_text = cap_res.get("caption", "")
        except Exception:
            caption_text = ""
        if caption_text:
            item_id = str(uuid4())
            itm = {
                "item_id": item_id,
                "type": "caption",
                "text": caption_text,
                "metadata": {"page": page, "source_file": file_path.name, "chunk_index": 0},
                "image_path": image_path,
            }
            items_to_save.append(itm)
            texts_for_embedding.append(caption_text)
            embed_targets.append(itm)

    # Process embedded images captions
    for emb in embedded_image_items:
        page = emb.get("page_number")
        image_path = emb.get("image_path")
        try:
            cap_res = simple_caption(image_path)
            caption_text = cap_res.get("caption", "")
        except Exception:
            caption_text = ""
        if caption_text:
            item_id = str(uuid4())
            itm = {
                "item_id": item_id,
                "type": "caption",
                "text": caption_text,
                "metadata": {"page": page, "source_file": file_path.name, "chunk_index": 0},
                "image_path": image_path,
            }
            items_to_save.append(itm)
            texts_for_embedding.append(caption_text)
            embed_targets.append(itm)

    # Generate embeddings in batch for all collected texts
    if texts_for_embedding:
        embeddings = embed_texts(texts_for_embedding)
        # assign embeddings back to the corresponding items
        for emb_vec, target in zip(embeddings, embed_targets):
            target["embedding"] = emb_vec

    # Ensure every item has embedding (if embedding failed, set to None)
    for it in items_to_save:
        if "embedding" not in it:
            it["embedding"] = None

    # Save all items to MongoDB
    save_items(doc_id, items_to_save)

    # Return saved item summaries
    return [{"item_id": it["item_id"], "type": it["type"], "page": it.get("metadata", {}).get("page")} for it in items_to_save]

