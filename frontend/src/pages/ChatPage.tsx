import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import client from '../api/client';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
};

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const [docs, setDocs] = useState<any[]>([]);
  const [sessionId, setSessionId] = useState<string>('');
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  const selectedDoc = useMemo(
    () => docs.find((doc) => (doc.doc_id || doc.id) === selectedDocId) || null,
    [docs, selectedDocId],
  );

  useEffect(() => {
    async function init() {
      try {
        const session = await client.createSession();
        setSessionId(session.session_id || session.id || '');
      } catch (e) {
        setSessionId('');
      }

      try {
        const result: any = await client.listDocuments();
        const documents = Array.isArray(result) ? result : result.items || [];
        setDocs(documents);

        const paramDocId = searchParams.get('doc_id');
        const fallbackDocId = documents[0]?.doc_id || documents[0]?.id || null;
        const nextDocId = paramDocId || fallbackDocId;
        setSelectedDocId(nextDocId);
      } catch (e) {
        setDocs([]);
      }
    }

    init();
  }, [searchParams]);

  async function handleSend() {
    const question = input.trim();
    if (!question || !sessionId || sending) {
      return;
    }

    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', text: question };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setSending(true);

    try {
      const response: any = await client.ask(sessionId, question, selectedDocId || undefined, 'local');
      const reply = response?.answer || 'I could not find an answer in the referenced document.';
      const assistantMessage: ChatMessage = { id: crypto.randomUUID(), role: 'assistant', text: reply };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', text: 'The backend request failed. Please check the server and try again.' },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-shell">
      <div className="chat-main-panel">
        <div className="chat-page-header">
          <div>
            <p className="page-label">RAG Q&A Bot</p>
            <h1 className="chat-title">Hi Anandha! Ask anything about your document.</h1>
            <p className="chat-subtitle">
              I can answer questions about text, tables, charts, diagrams, and more.
            </p>
          </div>
          <div className="page-status-card">
            <div className="status-dot status-ready" />
            <div>
              <div className="status-label">{selectedDoc ? 'Document ready' : 'Waiting for document'}</div>
              <div className="status-note">
                {selectedDoc ? selectedDoc.filename || 'Selected document' : 'Upload a document first'}
              </div>
            </div>
          </div>
        </div>

        <div className="chat-layout">
          <section className="chat-window">
            <div className="conversation-header">
              <div>
                <div className="doc-chip">{selectedDoc ? selectedDoc.filename || 'Selected document' : 'No document selected'}</div>
                <div className="doc-meta">
                  {selectedDoc ? `Processed • ${selectedDoc.pages || 1} pages` : 'Upload a file to enable Q&A'}
                </div>
              </div>
              <button className="new-question-button" type="button" onClick={() => setMessages([])}>
                New question
              </button>
            </div>

            <div className="chat-thread">
              {messages.length === 0 ? (
                <div className="message message-assistant">
                  <div className="assistant-bubble">
                    Ask a question about the uploaded document and I will retrieve the most relevant content from it.
                  </div>
                </div>
              ) : (
                messages.map((message) => (
                  <div key={message.id} className={`message message-${message.role}`}>
                    <div className={message.role === 'user' ? 'message-text' : 'assistant-bubble'}>
                      {message.text}
                    </div>
                    {message.role === 'user' && <div className="message-time">Now</div>}
                  </div>
                ))
              )}
            </div>

            <div className="input-bar">
              <button className="icon-button" type="button" aria-label="Attach file">
                📎
              </button>
              <input
                className="input-field"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder={selectedDoc ? 'Ask a question about your document...' : 'Upload a document first...'}
                aria-label="Ask a question"
                disabled={!selectedDoc || !sessionId || sending}
              />
              <button
                className="send-button"
                type="button"
                aria-label="Send question"
                onClick={handleSend}
                disabled={!selectedDoc || !sessionId || sending}
              >
                {sending ? '…' : '➤'}
              </button>
            </div>
          </section>

          <aside className="chat-info-panel">
            <div className="panel-block">
              <div className="panel-header">
                <h2>Context Sources</h2>
                <span className="badge">{selectedDoc ? 1 : 0}</span>
              </div>
              {selectedDoc ? (
                <div className="source-card">
                  <div className="source-label">{selectedDoc.filename || 'Selected document'}</div>
                  <p>This document is currently selected for the Q&A session.</p>
                  <button type="button" className="source-link" onClick={() => setMessages([])}>
                    Refresh chat
                  </button>
                </div>
              ) : (
                <div className="source-card">
                  <div className="source-label">No document</div>
                  <p>Upload or select a document from the library before asking questions.</p>
                </div>
              )}
            </div>

            <div className="panel-block doc-info-card">
              <div className="panel-header">
                <h2>Document Info</h2>
              </div>
              <div className="info-row">
                <span>File Name</span>
                <strong>{selectedDoc ? selectedDoc.filename || '—' : '—'}</strong>
              </div>
              <div className="info-row">
                <span>Pages</span>
                <strong>{selectedDoc ? selectedDoc.pages || 1 : '—'}</strong>
              </div>
              <div className="info-row">
                <span>Status</span>
                <strong className="status-tag">{selectedDoc ? 'Ready' : 'Waiting'}</strong>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
