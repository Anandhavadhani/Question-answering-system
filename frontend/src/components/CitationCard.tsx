import React from 'react';
import client from '../api/client';

type Props = {
  docId: string;
  itemId: string;
  snippet?: string;
};

export default function CitationCard({ docId, itemId, snippet }: Props) {
  const imgUrl = client.getDocumentImageUrl(docId, itemId);
  return (
    <div className="flex items-start gap-4 p-3 rounded-md shadow-sm" style={{ background: '#FFFFFF' }}>
      <img src={imgUrl} alt={`item-${itemId}`} className="w-24 h-24 object-cover rounded" />
      <div>
        <div className="text-sm text-gray-700">{snippet}</div>
        <div className="mt-2 text-xs text-gray-500">{`Doc: ${docId} • Item: ${itemId}`}</div>
      </div>
    </div>
  );
}
