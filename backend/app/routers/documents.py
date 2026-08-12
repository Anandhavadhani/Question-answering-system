import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.db import mongo
from app.pipeline.ingestion import ingest_document
from app.pipeline.ocr import run_ocr
from app.pipeline.captioning import simple_caption

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}


@router.get("")
def list_documents() -> List[Dict[str, Any]]:
    """Return all uploaded documents by unique doc_id."""
    docs: Dict[str, Dict[str, Any]] = {}

    for item in mongo.collection.find({}, {"_id": 0, "doc_id": 1, "metadata": 1, "type": 1}):
        doc_id = item.get("doc_id")
        if not doc_id:
            continue

        entry = docs.setdefault(
            doc_id,
            {
                "doc_id": doc_id,
                "filename": "",
                "type": "PDF",
                "pages": 0,
                "status": "ready",
            },
        )

        metadata = item.get("metadata") or {}
        source_file = metadata.get("source_file") or metadata.get("filename")
        if source_file and not entry["filename"]:
            entry["filename"] = source_file

        file_type = (source_file or "").lower()
        if file_type.endswith(".png") or file_type.endswith(".jpg") or file_type.endswith(".jpeg"):
            entry["type"] = "Image"
        elif file_type.endswith(".pdf"):
            entry["type"] = "PDF"

        page = metadata.get("page")
        if isinstance(page, int):
            entry["pages"] = max(entry["pages"], page)

    for entry in docs.values():
        if entry["filename"]:
            entry["pages"] = max(entry["pages"], 1)
        else:
            entry["pages"] = 1

    return sorted(docs.values(), key=lambda d: d["doc_id"], reverse=True)


@router.get("/{doc_id}/status")
def get_document_status(doc_id: str):
    """Return basic upload processing status for a document."""
    exists = mongo.collection.count_documents({"doc_id": doc_id}, limit=1) > 0
    if not exists:
        raise HTTPException(status_code=404, detail="document not found")
    return {"doc_id": doc_id, "status": "ready"}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type: only PDF and image files are allowed.",
        )

    doc_id = str(uuid.uuid4())
    upload_dir = UPLOAD_DIR / doc_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"original{ext}"

    contents = await file.read()
    destination.write_bytes(contents)

    ingestion_items = []
    image_processing = None
    if ext == ".pdf":
        ingestion_items = ingest_document(doc_id, destination)
    else:
        # for image uploads, run OCR and a lightweight captioner
        try:
            ocr_res = run_ocr(destination)
        except Exception:
            ocr_res = {"lines": [], "raw": None}
        caption_res = simple_caption(destination)
        image_processing = {"ocr": ocr_res, "caption": caption_res}

    job_id = str(uuid.uuid4())
    resp = {"doc_id": doc_id, "job_id": job_id, "ingestion_items": ingestion_items}
    if image_processing is not None:
        resp["image_processing"] = image_processing
    return resp
