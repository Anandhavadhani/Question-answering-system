import React, { useState, useRef } from 'react';
import client from '../api/client';

export default function UploadPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function uploadSelectedFile(file: File) {
    setUploading(true);
    setStatus('Uploading');
    const fd = new FormData();
    fd.append('file', file);

    try {
      const resp: any = await client.uploadDocument(fd);
      const createdId = resp.doc_id || resp.id || resp.docId || null;
      setDocId(createdId || 'uploaded');
      setStatus('Processing');

      const interval = setInterval(async () => {
        try {
          const s: any = await client.getDocumentStatus(createdId);
          const nextStatus = s.status || s;
          setStatus(typeof nextStatus === 'string' ? nextStatus : 'Ready');
          if (nextStatus === 'ready' || nextStatus === 'failed' || nextStatus === 'processed') {
            clearInterval(interval);
            setUploading(false);
          }
        } catch (e) {
          clearInterval(interval);
          setStatus('Unable to verify upload status. Please refresh and try again.');
          setUploading(false);
        }
      }, 3000);
    } catch (e: any) {
      const message = e?.message || 'Upload failed.';
      const detail = message.includes('API') ? 'Upload failed. Check the backend and file type.' : message;
      setStatus(detail);
      setUploading(false);
    }
  }

  function handleFile(file: File) {
    if (!file) return;
    setSelectedFile(file);
    setStatus(`Selected: ${file.name}`);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(true);
  }

  function onDragLeave() {
    setDragActive(false);
  }

  function onBrowseClick() {
    fileRef.current?.click();
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
    e.target.value = '';
  }

  return (
    <div className="upload-page">
      <div className="page-header">
        <div>
          <p className="page-label">Upload Document</p>
          <h1>Upload PDF or image files to ask questions about their content.</h1>
          <p className="page-description">
            We extract text, tables, charts, and images so your documents are searchable and answerable.
          </p>
        </div>
        <div className="status-box">
          <div className="status-title">Upload status</div>
          <div className="status-value">{uploading ? 'Working...' : status || 'Waiting for upload'}</div>
          {docId && <div className="status-note">Doc ID: {docId}</div>}
        </div>
      </div>

      <div className="upload-grid">
        <section className="upload-panel">
          <div
            className={`upload-dropzone ${dragActive ? 'drag-active' : ''}`}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
          >
            <div className="upload-icon">☁️</div>
            <div className="upload-title">Drag & drop your files here</div>
            <div className="upload-subtitle">or click to browse</div>
            <div className="upload-meta">Supports PDF, PNG, JPG, JPEG · Max file size: 50 MB</div>

            {selectedFile ? (
              <div className="upload-selected-file">Selected file: {selectedFile.name}</div>
            ) : null}

            <div className="upload-actions">
              <button className="browse-button" type="button" onClick={onBrowseClick}>
                Browse files
              </button>
              <button
                className="primary-button upload-submit-button"
                type="button"
                onClick={() => selectedFile && uploadSelectedFile(selectedFile)}
                disabled={!selectedFile || uploading}
              >
                {uploading ? 'Uploading...' : 'Upload file'}
              </button>
            </div>

            <input
              ref={fileRef}
              type="file"
              hidden
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.gif"
              onChange={onFileChange}
            />
          </div>

          <div className="upload-tips">
            <div className="tip-card">
              <div className="tip-emoji">📄</div>
              <div>
                <strong>PDF with Text</strong>
                <p>Text-based PDFs give the best results.</p>
              </div>
            </div>
            <div className="tip-card">
              <div className="tip-emoji">🖨️</div>
              <div>
                <strong>Scanned Documents</strong>
                <p>We use OCR to extract text accurately.</p>
              </div>
            </div>
            <div className="tip-card">
              <div className="tip-emoji">📈</div>
              <div>
                <strong>Charts & Diagrams</strong>
                <p>We understand visuals with image captioning.</p>
              </div>
            </div>
          </div>
        </section>

        <aside className="upload-info-panel">
          <div className="info-card">
            <div className="panel-title">What happens next?</div>
            <ol className="steps-list">
              <li>
                <span>1</span>
                <div>
                  <strong>Ingestion</strong>
                  <p>We split your document into pages, text blocks and images.</p>
                </div>
              </li>
              <li>
                <span>2</span>
                <div>
                  <strong>Understanding</strong>
                  <p>OCR extracts text and AI describes charts / images.</p>
                </div>
              </li>
              <li>
                <span>3</span>
                <div>
                  <strong>Embedding</strong>
                  <p>Content is converted into vector embeddings.</p>
                </div>
              </li>
              <li>
                <span>4</span>
                <div>
                  <strong>Storage</strong>
                  <p>Stored in your vector store for fast retrieval.</p>
                </div>
              </li>
              <li>
                <span>5</span>
                <div>
                  <strong>Ready to Ask</strong>
                  <p>You can now ask questions about your document.</p>
                </div>
              </li>
            </ol>
          </div>

          <div className="note-card">
            <strong>Your data stays private</strong>
            <p>Files are used only for this session and are not shared externally.</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
