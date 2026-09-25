import { useState, useEffect } from 'react';
import { useI18n } from '../i18n';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  document_type: string;
  category: string;
  status: string;
  ocr_text?: string;
  classification?: string;
  classification_confidence?: number;
  extracted_data?: Record<string, string>;
  linked_entity_type?: string;
  linked_entity_id?: string;
  tags?: string[];
  created_at: string;
}

interface DocStats {
  total: number;
  processed: number;
  failed: number;
  processing: number;
  by_category: Record<string, number>;
}

export default function DocumentsPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [stats, setStats] = useState<DocStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('');

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/documents', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/documents/stats', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([docs, st]) => {
      setDocuments(docs);
      setStats(st);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token]);

  const handleSearch = async () => {
    const params = new URLSearchParams();
    if (searchQuery) params.set('query', searchQuery);
    if (filterCategory) params.set('category', filterCategory);
    const r = await fetch(`/api/v1/documents/search?${params}`, { headers: { Authorization: `Bearer ${token}` } });
    const data = await r.json();
    setDocuments(data.documents);
  };

  const classifyDoc = async (docId: string, category: string) => {
    await fetch(`/api/v1/documents/${docId}/classify`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: docId, category }),
    });
    setDocuments(docs => docs.map(d => d.id === docId ? { ...d, category, classification: category } : d));
  };

  const extractDoc = async (docId: string) => {
    const r = await fetch(`/api/v1/documents/${docId}/extract`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    const updated = await r.json();
    setDocuments(docs => docs.map(d => d.id === docId ? updated : d));
    if (selectedDoc?.id === docId) setSelectedDoc(updated);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'processed': return 'bg-green-100 text-green-700';
      case 'processing': return 'bg-yellow-100 text-yellow-700';
      case 'failed': return 'bg-red-100 text-red-700';
      case 'archived': return 'bg-gray-100 text-gray-500';
      default: return 'bg-blue-100 text-blue-700';
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-gray-500">{t.documentsPage.loading}</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">{t.documentsPage.title}</h2>
        <span className="text-sm text-gray-500">{documents.length} {t.documentsPage.documentsCount}</span>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { label: t.documentsPage.total, value: stats.total, color: 'bg-blue-50 text-blue-700' },
            { label: t.documentsPage.processed, value: stats.processed, color: 'bg-green-50 text-green-700' },
            { label: t.documentsPage.processing, value: stats.processing, color: 'bg-yellow-50 text-yellow-700' },
            { label: t.documentsPage.failed, value: stats.failed, color: 'bg-red-50 text-red-700' },
            { label: t.documentsPage.categories, value: Object.keys(stats.by_category).length, color: 'bg-purple-50 text-purple-700' },
          ].map(s => (
            <div key={s.label} className={`rounded-lg p-4 ${s.color}`}>
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-sm opacity-75">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3">
        <input
          type="text"
          placeholder={t.documentsPage.searchPlaceholder}
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)} className="px-4 py-2 border border-gray-300 rounded-lg">
          <option value="">{t.documentsPage.allCategories}</option>
          <option value="invoice">{t.documentsPage.invoice}</option>
          <option value="receipt">{t.documentsPage.receipt}</option>
          <option value="contract">{t.documentsPage.contract}</option>
          <option value="purchase_order">{t.documentsPage.purchaseOrder}</option>
          <option value="goods_received">{t.documentsPage.goodsReceived}</option>
          <option value="report">{t.documentsPage.report}</option>
          <option value="other">{t.documentsPage.other}</option>
        </select>
        <button onClick={handleSearch} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{t.documentsPage.search}</button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.documentsPage.file}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.documentsPage.category}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.documentsPage.status}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.documentsPage.classification}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.documentsPage.size}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.documentsPage.actions}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {documents.map(doc => (
              <tr key={doc.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedDoc(doc)}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{doc.mime_type.includes('pdf') ? '📄' : doc.mime_type.includes('image') ? '🖼' : '📎'}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{doc.filename}</p>
                      <p className="text-xs text-gray-500">{doc.document_type}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">{doc.category}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor(doc.status)}`}>{doc.status}</span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  {doc.classification || '-'}
                  {doc.classification_confidence != null && <span className="text-xs text-gray-400 ml-1">({(doc.classification_confidence * 100).toFixed(0)}%)</span>}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">{formatSize(doc.file_size)}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button onClick={e => { e.stopPropagation(); extractDoc(doc.id); }} className="text-xs px-2 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100">{t.documentsPage.extract}</button>
                    <select onClick={e => e.stopPropagation()} onChange={e => { e.stopPropagation(); classifyDoc(doc.id, e.target.value); }} className="text-xs px-2 py-1 border rounded">
                      <option value="">{t.documentsPage.classify}</option>
                      <option value="invoice">{t.documentsPage.invoice}</option>
                      <option value="receipt">{t.documentsPage.receipt}</option>
                      <option value="contract">{t.documentsPage.contract}</option>
                      <option value="purchase_order">{t.documentsPage.po}</option>
                    </select>
                  </div>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400">{t.documentsPage.noDocumentsFound}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedDoc && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedDoc(null)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold">{selectedDoc.filename}</h3>
              <button onClick={() => setSelectedDoc(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div><span className="text-gray-500">{t.documentsPage.categoryLabel}</span> {selectedDoc.category}</div>
                <div><span className="text-gray-500">{t.documentsPage.statusLabel}</span> <span className={`px-2 py-0.5 rounded text-xs ${statusColor(selectedDoc.status)}`}>{selectedDoc.status}</span></div>
                <div><span className="text-gray-500">{t.documentsPage.typeLabel}</span> {selectedDoc.document_type}</div>
                <div><span className="text-gray-500">{t.documentsPage.mimeLabel}</span> {selectedDoc.mime_type}</div>
              </div>
              {selectedDoc.extracted_data && Object.keys(selectedDoc.extracted_data).length > 0 && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <p className="font-medium mb-2">{t.documentsPage.extractedData}</p>
                  {Object.entries(selectedDoc.extracted_data).map(([k, v]) => (
                    <div key={k} className="flex justify-between py-1 border-b border-gray-200 last:border-0">
                      <span className="text-gray-600">{k}</span>
                      <span className="font-medium">{v}</span>
                    </div>
                  ))}
                </div>
              )}
              {selectedDoc.ocr_text && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <p className="font-medium mb-2">{t.documentsPage.ocrText}</p>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap max-h-40 overflow-y-auto">{selectedDoc.ocr_text}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
