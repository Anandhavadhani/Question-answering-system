import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

export default function LibraryPage() {
  const navigate = useNavigate();
  const [docs, setDocs] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [typeFilter, setTypeFilter] = useState('All');
  const [sortOrder, setSortOrder] = useState('Newest first');

  useEffect(() => {
    async function load() {
      try {
        const res: any = await client.listDocuments();
        setDocs(Array.isArray(res) ? res : res.items || []);
      } catch (e) {
        setDocs([]);
      }
    }
    load();
  }, []);

  const filteredDocs = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return docs
      .filter((doc) => {
        const label = (doc.filename || doc.name || doc.source_file || '').toLowerCase();
        const status = (doc.status || doc.ingest_status || 'ready').toLowerCase();
        const type = (doc.type || doc.file_type || '').toLowerCase();

        const matchesSearch = !normalizedSearch || label.includes(normalizedSearch);
        const matchesStatus = statusFilter === 'All' || status.includes(statusFilter.toLowerCase());
        const matchesType = typeFilter === 'All' || type.includes(typeFilter.toLowerCase());

        return matchesSearch && matchesStatus && matchesType;
      })
      .sort((a, b) => {
        const aTime = Date.parse(a.uploaded_on || a.created_at || '2025-01-01');
        const bTime = Date.parse(b.uploaded_on || b.created_at || '2025-01-01');
        if (sortOrder === 'Newest first') {
          return bTime - aTime;
        }
        return aTime - bTime;
      });
  }, [docs, search, statusFilter, typeFilter, sortOrder]);

  function goToChat(docId?: string) {
    const params = docId ? `?doc_id=${encodeURIComponent(docId)}` : '';
    navigate(`/chat${params}`);
  }

  return (
    <div className="library-page">
      <div className="page-header">
        <div>
          <p className="page-label">Document Library</p>
          <h1>All your uploaded and processed documents.</h1>
          <p className="page-description">
            Search, filter, and review the documents you can ask questions about.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={() => navigate('/upload')}>
          Upload new
        </button>
      </div>

      <div className="library-panel">
        <div className="filter-row">
          <div className="filter-group">
            <label htmlFor="search" className="filter-label">Search documents</label>
            <input
              id="search"
              className="search-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search documents..."
            />
          </div>

          <div className="filter-group">
            <label htmlFor="status" className="filter-label">Status</label>
            <select
              id="status"
              className="select-field"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option>All</option>
              <option>Ready</option>
              <option>Processing</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="type" className="filter-label">Type</label>
            <select
              id="type"
              className="select-field"
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
            >
              <option>All</option>
              <option>PDF</option>
              <option>Image</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="sort" className="filter-label">Sort</label>
            <select
              id="sort"
              className="select-field"
              value={sortOrder}
              onChange={(event) => setSortOrder(event.target.value)}
            >
              <option>Newest first</option>
              <option>Oldest first</option>
            </select>
          </div>
        </div>

        <div className="table-card">
          <table className="library-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Type</th>
                <th>Pages</th>
                <th>Status</th>
                <th>Uploaded On</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocs.length > 0 ? (
                filteredDocs.map((doc, index) => (
                  <tr key={index}>
                    <td>{doc.filename || doc.name || doc.source_file || 'Untitled'}</td>
                    <td>{doc.type || doc.file_type || (doc.filename?.toLowerCase().endsWith('.pdf') ? 'PDF' : 'Image') || 'Unknown'}</td>
                    <td>{doc.pages || doc.page_count || '-'}</td>
                    <td>
                      <span className={`status-chip ${(doc.status || 'ready').toLowerCase()}`}>
                        {doc.status || 'Ready'}
                      </span>
                    </td>
                    <td>{doc.uploaded_on || doc.created_at || 'N/A'}</td>
                    <td className="actions-cell">
                      <button type="button" className="action-button" onClick={() => goToChat(doc.doc_id || doc.id)}>
                        View
                      </button>
                      <button type="button" className="action-button secondary" onClick={() => goToChat(doc.doc_id || doc.id)}>
                        Ask
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="empty-row">
                    No documents found yet. Upload a file to start asking questions.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
