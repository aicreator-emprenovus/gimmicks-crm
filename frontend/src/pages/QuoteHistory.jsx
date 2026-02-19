import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { formatCurrency } from "@/utils/currency";
import { useNavigate, useLocation } from "react-router-dom";
import {
  FileText, Plus, Trash2, Search, Eye, Send, RotateCcw, Archive,
  Download, Loader2, ShoppingBag, Clock, Filter, X, ChevronDown
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_MAP = {
  draft: { label: "Borrador", color: "bg-gray-100 text-gray-700" },
  sent: { label: "Enviada", color: "bg-blue-100 text-blue-700" },
  approved: { label: "Aprobada", color: "bg-green-100 text-green-700" },
  rejected: { label: "Rechazada", color: "bg-red-100 text-red-700" },
  orden_compra: { label: "Orden Compra", color: "bg-purple-100 text-purple-700" },
  pending: { label: "Pendiente", color: "bg-yellow-100 text-yellow-700" }
};

export default function QuoteHistory() {
  const navigate = useNavigate();
  const location = useLocation();
  const isPO = location.pathname.startsWith("/purchase-orders");
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [showTrash, setShowTrash] = useState(false);
  const docType = isPO ? "PO" : "QUOTE";
  const [pdfPreview, setPdfPreview] = useState(null);
  const [sendModal, setSendModal] = useState(null);
  const [activities, setActivities] = useState([]);
  const [showActivities, setShowActivities] = useState(false);
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };
  const newPath = isPO ? "/purchase-orders/new" : "/quotes/new";

  const fetchQuotes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/quotes-v2/`, {
        params: { trash: showTrash, doc_type: docType },
        headers
      });
      setQuotes(res.data || []);
    } catch { toast.error("Error al cargar"); }
    setLoading(false);
  }, [showTrash, docType]);

  useEffect(() => { fetchQuotes(); }, [fetchQuotes]);

  const handleDelete = async (id) => {
    if (!window.confirm(showTrash ? "¿Eliminar permanentemente?" : "¿Mover a papelera?")) return;
    try {
      await axios.delete(`${API_URL}/api/quotes-v2/${id}`, { params: { permanent: showTrash }, headers });
      toast.success(showTrash ? "Eliminado" : "Movido a papelera");
      fetchQuotes();
    } catch { toast.error("Error"); }
  };

  const handleRestore = async (id) => {
    try {
      await axios.post(`${API_URL}/api/quotes-v2/${id}/restore`, {}, { headers });
      toast.success("Restaurado");
      fetchQuotes();
    } catch { toast.error("Error"); }
  };

  const handleGeneratePDF = async (id, type = "PROFORMA") => {
    try {
      const res = await axios.post(`${API_URL}/api/quotes-v2/${id}/generate-pdf`, null, {
        params: { doc_type: type },
        headers
      });
      setPdfPreview({ base64: res.data.pdf_base64, filename: res.data.filename });
    } catch { toast.error("Error al generar PDF"); }
  };

  const handleDownloadPDF = () => {
    if (!pdfPreview) return;
    const link = document.createElement("a");
    link.href = `data:application/pdf;base64,${pdfPreview.base64}`;
    link.download = pdfPreview.filename;
    link.click();
  };

  const handleConvertToPO = async (id) => {
    if (!window.confirm("¿Convertir a Orden de Compra?")) return;
    try {
      await axios.post(`${API_URL}/api/quotes-v2/${id}/convert-to-po`, {}, { headers });
      toast.success("Orden de compra generada");
      setDocType("PO");
      fetchQuotes();
    } catch (e) { toast.error(e.response?.data?.detail || "Error"); }
  };

  const fetchActivities = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/quotes-v2/activities/all`, { headers, params: { limit: 50 } });
      setActivities(res.data || []);
      setShowActivities(true);
    } catch { toast.error("Error al cargar actividades"); }
  };

  const filtered = quotes.filter(q =>
    !search ||
    q.client_name?.toLowerCase().includes(search.toLowerCase()) ||
    q.quote_number?.includes(search) ||
    q.client_email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-4 lg:p-6" data-testid="quotes-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileText size={24} className="text-[#63AC9A]" />
            {docType === "PO" ? "Órdenes de Compra" : "Cotizaciones"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{filtered.length} documentos</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={fetchActivities} data-testid="activities-btn">
            <Clock size={16} className="mr-1" /> Actividad
          </Button>
          <Button variant={showTrash ? "default" : "outline"} size="sm" onClick={() => setShowTrash(!showTrash)} data-testid="toggle-trash-btn">
            <Archive size={16} className="mr-1" /> {showTrash ? "Ver activos" : "Papelera"}
          </Button>
          {!showTrash && (
            <Button size="sm" className="bg-[#63AC9A] hover:bg-[#4F9A87]" onClick={() => navigate(`${newPath}?type=${docType}`)} data-testid="new-quote-btn">
              <Plus size={16} className="mr-1" /> {isPO ? "Nueva OC" : "Nueva Cotizacion"}
            </Button>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <Input placeholder="Buscar por cliente, número..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9 bg-white" data-testid="search-quotes-input" />
        </div>
      </div>

      {/* Quotes List */}
      <div className="space-y-3">
        {loading ? (
          <div className="flex justify-center py-10"><Loader2 size={24} className="animate-spin text-gray-400" /></div>
        ) : filtered.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border p-10 text-center text-gray-400">
            {showTrash ? "No hay documentos en papelera" : "No se encontraron documentos"}
          </div>
        ) : filtered.map(q => (
          <div key={q.id} className="bg-white rounded-xl shadow-sm border p-4 hover:shadow-md transition-shadow" data-testid={`quote-card-${q.id}`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-bold text-gray-900">#{q.quote_number || "---"}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_MAP[q.status]?.color || "bg-gray-100 text-gray-600"}`}>
                    {STATUS_MAP[q.status]?.label || q.status}
                  </span>
                </div>
                <p className="text-sm text-gray-700 font-medium">{q.client_name || "Sin cliente"}</p>
                <div className="flex items-center gap-4 text-xs text-gray-400 mt-1">
                  <span>{q.items?.length || 0} productos</span>
                  <span>{new Date(q.created_at).toLocaleDateString()}</span>
                  {q.created_by_name && <span>por {q.created_by_name}</span>}
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-[#63AC9A]">{formatCurrency(q.total)}</p>
              </div>
              <div className="flex gap-1 flex-wrap">
                {showTrash ? (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => handleRestore(q.id)} className="text-green-600 text-xs" data-testid={`restore-btn-${q.id}`}>
                      <RotateCcw size={14} className="mr-1" /> Restaurar
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(q.id)} className="text-red-600 text-xs">
                      <Trash2 size={14} className="mr-1" /> Eliminar
                    </Button>
                  </>
                ) : (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => navigate(`${newPath}?edit=${q.id}&type=${q.doc_type}`)} className="text-xs" data-testid={`edit-quote-btn-${q.id}`}>
                      Editar
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleGeneratePDF(q.id, q.doc_type === "PO" ? "ORDEN_COMPRA" : "PROFORMA")} className="text-xs" data-testid={`pdf-btn-${q.id}`}>
                      <Eye size={14} className="mr-1" /> PDF
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setSendModal(q)} className="text-xs text-blue-600" data-testid={`send-btn-${q.id}`}>
                      <Send size={14} className="mr-1" /> Enviar
                    </Button>
                    {q.doc_type === "QUOTE" && (
                      <Button variant="ghost" size="sm" onClick={() => handleConvertToPO(q.id)} className="text-xs text-purple-600" data-testid={`convert-po-btn-${q.id}`}>
                        <ShoppingBag size={14} className="mr-1" /> Crear Orden
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(q.id)} className="text-xs text-red-500">
                      <Trash2 size={14} />
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* PDF Preview Modal */}
      {pdfPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="pdf-modal">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="font-bold">{pdfPreview.filename}</h2>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={handleDownloadPDF} data-testid="download-pdf-btn">
                  <Download size={14} className="mr-1" /> Descargar
                </Button>
                <button onClick={() => setPdfPreview(null)} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <iframe
                src={`data:application/pdf;base64,${pdfPreview.base64}`}
                className="w-full h-[70vh] border rounded"
                title="PDF Preview"
              />
            </div>
          </div>
        </div>
      )}

      {/* Send Email Modal */}
      {sendModal && (
        <SendEmailModal
          quote={sendModal}
          onClose={() => setSendModal(null)}
          onSent={() => { setSendModal(null); fetchQuotes(); }}
        />
      )}

      {/* Activities Modal */}
      {showActivities && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="font-bold">Actividad Reciente</h2>
              <button onClick={() => setShowActivities(false)} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {activities.length === 0 ? (
                <p className="text-center text-gray-400 py-4">Sin actividad registrada</p>
              ) : activities.map((a, i) => (
                <div key={i} className="flex items-start gap-2 py-2 border-b last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#63AC9A] mt-2 flex-shrink-0" />
                  <div className="text-sm">
                    <p className="text-gray-700"><span className="font-medium">{a.user_name}</span> {a.action} #{a.document_number}</p>
                    {a.details && <p className="text-xs text-gray-400">{a.details}</p>}
                    <p className="text-xs text-gray-400">{new Date(a.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SendEmailModal({ quote, onClose, onSent }) {
  const [emails, setEmails] = useState([]);
  const [newEmail, setNewEmail] = useState("");
  const [sending, setSending] = useState(false);
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    const initial = [];
    if (quote.client_email) initial.push(quote.client_email);
    // Fetch client to get commercial_email
    if (quote.client_id) {
      axios.get(`${API_URL}/api/clients/${quote.client_id}`, { headers }).then(res => {
        const c = res.data;
        const all = [...initial];
        if (c.commercial_email && !all.includes(c.commercial_email)) all.push(c.commercial_email);
        if (c.email && !all.includes(c.email)) all.push(c.email);
        setEmails(all);
      }).catch(() => setEmails(initial));
    } else {
      setEmails(initial);
    }
  }, []);

  const addEmail = () => {
    const parts = newEmail.split(",").map(e => e.trim()).filter(e => e && !emails.includes(e));
    if (parts.length > 0) {
      setEmails([...emails, ...parts]);
      setNewEmail("");
    }
  };

  const handleSend = async () => {
    if (emails.length === 0) { toast.error("Agregue al menos un email"); return; }
    setSending(true);
    try {
      const endpoint = quote.doc_type === "PO" ? "send-po" : "send-quote";
      await axios.post(`${API_URL}/api/quotes-v2/${quote.id}/${endpoint}`, { emails }, { headers });
      toast.success("Enviado exitosamente");
      onSent();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error al enviar");
    }
    setSending(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="send-email-modal">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-bold">Enviar {quote.doc_type === "PO" ? "Orden de Compra" : "Cotización"} #{quote.quote_number}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
        </div>
        <div className="p-5 space-y-3">
          <div className="flex gap-2">
            <Input type="email" value={newEmail} onChange={e => setNewEmail(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addEmail())} placeholder="Agregar email..." data-testid="add-email-input" />
            <Button variant="outline" onClick={addEmail}>+</Button>
          </div>
          <div className="space-y-1">
            {emails.map((e, i) => (
              <div key={i} className="flex items-center justify-between bg-gray-50 rounded px-3 py-1.5 text-sm">
                <span>{e}</span>
                <button onClick={() => setEmails(emails.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-600"><X size={14} /></button>
              </div>
            ))}
          </div>
        </div>
        <div className="flex justify-end gap-2 p-5 border-t">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button className="bg-[#63AC9A] hover:bg-[#4F9A87]" onClick={handleSend} disabled={sending} data-testid="confirm-send-btn">
            {sending ? <Loader2 size={16} className="animate-spin mr-1" /> : <Send size={16} className="mr-1" />}
            Enviar
          </Button>
        </div>
      </div>
    </div>
  );
}
