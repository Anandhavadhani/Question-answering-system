# ARCHITECTURE.md — Multimodal RAG Q&A Bot (Phase-by-Phase)

Deployment context: runs locally on your laptop for personal use (single user).

---

## Goal

Build a full-stack Retrieval-Augmented Generation (RAG) application that lets a user upload a PDF or image, then ask natural-language questions about its content — including charts, diagrams, and scanned text — and get accurate, context-grounded answers.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React + Tailwind CSS | Upload UI, chat interface, result display |
| Backend | FastAPI (Python, async) | API layer, orchestrates the RAG pipeline |
| OCR | PaddleOCR | Extract exact text/numbers from images/scanned pages |
| Vision captioning | Groq vision model | Generate semantic descriptions of charts/images |
| Embeddings | BGE (`bge-base-en`) | Convert text/captions into vectors |
| Vector storage | MongoDB Atlas (Vector Search) | Store `{text, embedding, metadata, image_path}` |
| LLM (answering) | Groq LLM (vision-capable) | Answer questions using retrieved text + images |

Overall pipeline:
```
Upload (PDF/Image)
  → 1. INGESTION (split into items: text blocks, page renders, embedded images)
  → 2. UNDERSTANDING (OCR for exact text, Groq captioning for semantic description)
  → 3. EMBEDDING (bge-base-en, run locally)
  → 4. STORAGE (MongoDB Atlas: text, embedding, metadata, image_path)
  → 5. RETRIEVAL (embed question → MongoDB vector search → top-k matches)
  → 6. ANSWERING (retrieved text + image(s) → Groq vision LLM → answer)
```

---

## Folder Structure

```
rag-qa-bot/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint, router registration
│   │   ├── routers/
│   │   │   ├── documents.py         # upload, status, list, delete, reingest
│   │   │   ├── sessions.py          # session create/history
│   │   │   ├── ask.py               # /ask endpoint
│   │   │   └── health.py            # /health
│   │   ├── pipeline/
│   │   │   ├── ingestion.py         # orchestrates ingestion + understanding + chunking
│   │   │   ├── pdf_extract.py       # PyMuPDF: native text, page render, embedded images
│   │   │   ├── ocr.py               # PaddleOCR wrapper
│   │   │   ├── captioning.py        # Groq vision captioning
│   │   │   ├── chunking.py          # text splitter (300–500 tok, 15% overlap)
│   │   │   ├── embedding.py         # bge-base-en wrapper
│   │   │   ├── retrieval.py         # vector search + text search + normalization/fusion
│   │   │   ├── query_rewrite.py     # follow-up question rewriting
│   │   │   └── answer.py            # guardrailed prompt + Groq vision LLM call
│   │   └── db/
│   │       └── mongo.py             # MongoDB client, index setup
│   ├── data/
│   │   ├── uploads/                 # raw uploaded PDFs/images
│   │   └── images/                  # rendered pages + extracted embedded images
│   ├── requirements.txt
│   └── .env                         # MongoDB URI, Groq API key, model names
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── UploadPage.tsx
│   │   │   ├── ChatPage.tsx
│   │   │   └── LibraryPage.tsx
│   │   ├── components/
│   │   │   ├── Dropzone.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── CitationCard.tsx
│   │   │   └── StatusBadge.tsx
│   │   └── api/client.ts            # fetch wrapper for backend endpoints
│   ├── package.json
│   └── .env                         # backend API base URL
│
├── ARCHITECTURE.md
└── BUILD_STEPS.md
```

Folders/files map directly onto the modules named in the pipeline (ingestion, OCR, captioning, chunking, embedding, retrieval, query rewriting, answering) and the endpoints listed in each phase below — nothing here beyond what those phases require.

---

## Phase 1 — FastAPI Skeleton + Upload Endpoint

**Goal:** `/documents/upload` endpoint that stores the file, no processing yet.

- Set up an async FastAPI app.
- `POST /documents/upload`: accept PDF or image, store the raw file, immediately return `doc_id`/`job_id` (no ingestion logic yet — that's added in later phases).
- `GET /health`: basic liveness/readiness check.

---

## Phase 2 — Ingestion: Item Splitting

**Goal:** PDF/image → discrete items: native text extraction, page rendering, embedded image extraction. Verify items are extracted correctly.

- **PDF text extraction**: Use `PyMuPDF` (fitz) to extract native selectable text first — faster and more accurate than OCR. Only route a page to OCR if native text extraction returns empty/near-empty content (i.e. it's a scanned page).
- **Page rendering**: Render every PDF page to an image via `PyMuPDF` or `pdf2image` at 200–300 DPI (200 for speed, 300 if small chart labels need to stay legible). Store rendered page images on disk, referenced by `image_path`.
- **Embedded image extraction**: Separately extract embedded raster images (`page.get_images()` in PyMuPDF) so charts/figures can be processed and cited individually, not just as part of a full-page render.
- **Item types produced per document**: `native_text`, `ocr_text`, `page_image`, `embedded_image`.

---

## Phase 3 — Understanding: OCR + Vision Captioning

**Goal:** Add PaddleOCR (scanned pages only) + Groq captioning to generate text for every item.

- **OCR (PaddleOCR)**: Run only on `page_image`/`embedded_image` items that lack native text. Preprocess (deskew, binarize) for scanned docs to improve accuracy.
- **Vision captioning (Groq)**: Run on every image item (page renders + embedded images) to produce a semantic description — what the chart/diagram shows, axis labels, trend, key callouts. Prompt the vision model explicitly to transcribe any visible numbers/labels verbatim, not just describe them, since these numbers matter for retrieval.
- **Deduplication**: When both OCR and captioning produce output for the same image, keep both but tag them distinctly (`type: ocr_text` vs `type: caption`) rather than merging — they serve different retrieval purposes (exact match vs semantic match).

---

## Phase 4 — Chunking, Embedding & Storage

**Goal:** Apply chunking, generate BGE embeddings, store in MongoDB with both vector and text indexes.

**Chunking:**
- Chunk native text and OCR text into 300–500 token chunks with ~15% overlap (don't chunk captions — keep them as one unit per image).
- Chunk boundaries should respect paragraph/sentence breaks, not cut mid-sentence (use a text splitter like `RecursiveCharacterTextSplitter` logic).
- Each chunk keeps a back-reference to its page number and source item so citations stay accurate after splitting.

**Embedding:**
- Generate embeddings with bge-base-en (via `sentence-transformers` or `FlagEmbedding`) for every chunk and every caption.
- Use the same model and same query-prefix convention BGE recommends (BGE models expect a specific instruction prefix on queries, not on stored passages — apply this consistently or retrieval quality drops).

**Storage (MongoDB Atlas):**
- Schema:
  ```json
  {
    "doc_id": "string",
    "item_id": "string",
    "user_id": "string",
    "type": "native_text | ocr_text | caption",
    "text": "string",
    "embedding": [float, ...],
    "metadata": {"page": int, "source_file": "string", "chunk_index": int},
    "image_path": "string | null"
  }
  ```
- Create a MongoDB Atlas Vector Search index on the `embedding` field.
- Also create a standard text index on the `text` field to support hybrid search via score normalization + fusion (Phase 6).

---

## Phase 5 — `/ask` with Vector-Only Search

**Goal:** Simplest path to a working answer — vector search only, no hybrid/rerank yet.

- `POST /ask`: Body `{session_id, doc_id (optional), question}` → embed question with bge-base-en → MongoDB vector search → top-k matches → return an answer.
- `POST /sessions`: create a new chat session (returns `session_id`).
- `GET /sessions/{session_id}/history`: fetch conversation history for a session.

---

## Phase 6 — Hybrid Search (Score Normalization + Fusion)

**Goal:** Add hybrid search that combines vector and text search using normalized, weighted fusion scores.

- **Hybrid search**: Pure vector search misses exact keyword/number matches (bad for tables, IDs, stats). Run vector search and MongoDB Atlas `$search` (text/keyword) in parallel to get two candidate result sets.
- **Score normalization**: Vector similarity scores and text search scores are on different scales, so normalize each result set's scores to a common range (e.g. min-max normalization to [0, 1]) before combining them.
- **Fusion score**: Combine the normalized vector score and normalized text score per candidate into a single fusion score (e.g. a weighted sum: `fusion_score = w_vector * norm_vector_score + w_text * norm_text_score`), then sort candidates by fusion score to get the final top-k passed to the LLM.
- **Metadata filtering**: Support filtering retrieval to a specific `doc_id`/`user_id` so multi-document users don't get cross-document leakage.
- **Similarity threshold**: Discard candidates below a minimum fusion score rather than always returning top-k — prevents forcing an answer from irrelevant chunks.

---

## Phase 7 — Guardrailed System Prompt + Abstain Logic

**Goal:** Add hallucination guardrails to the answering step.

- System prompt for the Groq vision LLM must explicitly instruct it to:
  - Answer only from the provided retrieved text/images — no outside knowledge.
  - If the retrieved context doesn't contain the answer, respond with an explicit "I don't have enough information in this document to answer that" rather than guessing.
  - Cite the page number / source item for every factual claim in the answer.
  - Flag when retrieved passages conflict with each other instead of silently picking one.
- Enforce the "abstain" behavior in code too: if the top fusion score is below the similarity threshold (Phase 6), skip the LLM call and return the "not found" message directly.

---

## Phase 8 — Session Management + Query Rewriting

**Goal:** Multi-turn conversational memory.

- Maintain per-session chat history (question + answer pairs) in MongoDB or in-memory session store, keyed by `session_id`.
- For multi-turn follow-ups ("what about in 2023?"), first run a query rewriting step: send the recent chat history + new question to a lightweight LLM call that rewrites it into a standalone question before embedding/retrieval. Without this, follow-up questions retrieve poorly because they lack context on their own.
- Pass the last N turns (e.g. 3–5) of conversation history into the final answering prompt so the LLM's phrasing stays consistent with prior answers.

Final `/ask` flow after this phase: rewrite query using session history (if any) → hybrid search (vector + text, scores normalized and combined via fusion score) → threshold check (abstain if below threshold) → pass top-k text + images to Groq vision LLM with the guardrailed system prompt → return answer with citations.

---

## Phase 9 — Frontend: Upload, Chat, Citations

**Goal:** Build React + Tailwind frontend: upload flow, then chat flow, then citation/image display.

- **Upload screen**: drag-and-drop PDF/image, progress indicator during ingestion.
- **Chat interface**: question input, streaming or async answer display.
- **Answer view**: show cited text snippets and thumbnail(s) of the retrieved image/chart alongside the answer.
- **Document library view**: list of uploaded/processed files with ingestion status.

---

## Phase 10 — Polish

**Goal:** Loading states, error states, multi-document support, status polling, deletion/re-ingestion.

- `GET /documents/{doc_id}/status`: poll ingestion status (`pending / processing / ready / failed`).
- `GET /documents`: list all documents for the current user with status + metadata.
- `DELETE /documents/{doc_id}`: delete a document, its stored files, and all associated vector entries.
- `POST /documents/{doc_id}/reingest`: re-run the ingestion pipeline on an existing document.
- `GET /documents/{doc_id}/items/{item_id}/image`: serve a stored page/embedded image (used to render citation thumbnails in the UI).
- `.env` for MongoDB URI, Groq API key, model names.
- Background job handling for ingestion (FastAPI `BackgroundTasks`).
- Basic error handling: unsupported file types, OCR failures, empty vector search results.

---

## Success Criteria

- User can upload a PDF or image and see ingestion complete.
- User can ask a question referencing a chart/number in the document and get a correct answer.
- Answer response includes which page/image the answer was grounded in.
- Pipeline works end-to-end without manual intervention after upload.
