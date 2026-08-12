const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function request(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, opts);
  const ct = res.headers.get('content-type') || '';
  const text = await res.text();

  let data: any = text;
  if (ct.includes('application/json')) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      data = text;
    }
  }

  if (!res.ok) {
    const detail = data && (data.detail || data.message || data.error || JSON.stringify(data));
    throw new Error(detail || `API ${res.status} ${res.statusText}`);
  }

  return ct.includes('application/json') ? data : text;
}

export async function uploadDocument(formData: FormData) {
  return request('/documents/upload', { method: 'POST', body: formData });
}

export async function getDocumentStatus(docId: string) {
  return request(`/documents/${docId}/status`);
}

export async function listDocuments() {
  return request('/documents');
}

export async function createSession() {
  return request('/sessions/', { method: 'POST' });
}

export async function getSessionHistory(sessionId: string) {
  return request(`/sessions/${sessionId}/history`);
}

export async function ask(sessionId: string, question: string, docId?: string, userId?: string) {
  const body = { session_id: sessionId, question, doc_id: docId, user_id: userId };
  return request('/ask/', { method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } });
}

export function getDocumentImageUrl(docId: string, itemId: string) {
  const base = API_BASE || '';
  return `${base}/documents/${docId}/items/${itemId}/image`;
}

export default { uploadDocument, getDocumentStatus, listDocuments, createSession, getSessionHistory, ask, getDocumentImageUrl };
const apiBaseUrl = API_BASE || "http://localhost:8000";

export const apiClient = {
  baseUrl: apiBaseUrl,
};
