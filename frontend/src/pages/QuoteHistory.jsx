import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { formatCurrency } from "@/utils/currency";
import { useNavigate, useLocation } from "react-router-dom";
import {
  FileText, Plus, Trash2, Search, Eye, Send, RotateCcw, Archive,
  Download, Upload, Loader2, ShoppingBag, Clock, Filter, X, ChevronDown, Save
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/AuthContext";

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
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
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
  const [importing, setImporting] = useState(false);
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState("");
  const [facturaModal, setFacturaModal] = useState(null);
  const [facturaFields, setFacturaFields] = useState({});
  const [savingPOHeader, setSavingPOHeader] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState("");

  const openFacturaModal = async (q) => {
    // First try to load saved PO header data
    let savedData = null;
    try {
      const res = await axios.get(`${API_URL}/api/quotes-v2/${q.id}/po-header`, { headers });
      if (res.data.po_header_data && Object.keys(res.data.po_header_data).length > 0) {
        savedData = res.data.po_header_data;
      }
    } catch (e) { console.error("Load PO header failed:", e); }

    if (savedData && savedData.cliente) {
      // Use saved data
      setFacturaFields(savedData);
    } else {
      // Fall back to client data
      let clientData = {};
      if (q.client_id) {
        try {
          const res = await axios.get(`${API_URL}/api/clients/`, { headers });
          const client = res.data.find(c => c.id === q.client_id);
          if (client) clientData = client;
        } catch (e) { console.error("Load client data failed:", e); }
      }
      const months = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
      const d = q.created_at ? new Date(q.created_at) : new Date();
      const dateStr = `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
      setFacturaFields({
        fecha: dateStr,
        cliente: q.client_name || clientData.name || "",
        direccion: clientData.address || "",
        solicitado_por: clientData.contact_person || q.client_contact || "",
        ruc: clientData.tax_id || "",
        orden_compra_cliente: q.client_name || "",
        factura: q.factura || "",
        telefono: clientData.phone || "",
        correo: clientData.email || q.client_email || "",
      });
    }
    setFacturaModal(q);
  };

  const savePOHeader = async () => {
    if (!facturaModal) return;
    setSavingPOHeader(true);
    try {
      await axios.put(`${API_URL}/api/quotes-v2/${facturaModal.id}/po-header`, facturaFields, { headers });
      toast.success("Datos guardados");
      fetchQuotes();
    } catch { toast.error("Error al guardar"); }
    setSavingPOHeader(false);
  };
  const headers = {};
  const newPath = isPO ? "/purchase-orders/new" : "/quotes/new";

  const handleExportExcel = () => {
    import("xlsx").then(XLSX => {
      const data = [];
      quotes.forEach(q => {
        (q.items || []).forEach(item => {
          const row = {
            "Número": q.quote_number,
            "Cliente": q.client_name,
            "Contacto": q.client_contact,
            "Email Cliente": q.client_email,
            "Código": item.code,
            "Producto": item.name,
            "Descripción": item.description,
            "Cantidad": item.quantity,
            "Precio Unitario": item.unit_price,
            "Total": item.total_price,
            "Estado": q.status,
            "Condiciones de Pago": q.payment_terms,
            "Validez": q.validity,
            "Tiempo de Entrega": q.delivery_time,
            "Creado": q.created_at ? new Date(q.created_at).toLocaleDateString("es-EC") : ""
          };
          if (isPO) {
            row["Factura"] = q.factura && q.factura.trim() ? q.factura : "No asignado";
          }
          data.push(row);
        });
      });
      const ws = XLSX.utils.json_to_sheet(data);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, isPO ? "Ordenes" : "Cotizaciones");
      XLSX.writeFile(wb, isPO ? "ordenes_gimmicks.xlsx" : "cotizaciones_gimmicks.xlsx");
    });
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await axios.post(`${API_URL}/api/import/quotes?doc_type=${docType}`, formData, {
        headers: { ...headers, "Content-Type": "multipart/form-data" }
      });
      toast.success(`Importados: ${res.data.inserted} nuevos, ${res.data.skipped} duplicados omitidos`);
      fetchQuotes();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al importar");
    } finally {
      setImporting(false);
    }
  };

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

  // Reset all filters when navigating between sections
  useEffect(() => {
    setSearch("");
    setSelectedClient("");
    setSelectedProduct("");
  }, [isPO]);

  useEffect(() => {
    const fetchClients = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/clients/`, { headers });
        setClients(res.data || []);
      } catch (e) { console.error("Load clients failed:", e); }
    };
    fetchClients();
  }, []);

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

  const handleGeneratePDF = async (id, type = "PROFORMA", overrides = null) => {
    try {
      const res = await axios.post(`${API_URL}/api/quotes-v2/${id}/generate-pdf`, {
        doc_type: type,
        factura: overrides?.factura || "",
        overrides: overrides
      }, { headers });
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

  const quotedProducts = React.useMemo(() => {
    const map = new Map();
    for (const q of quotes) {
      for (const it of (q.items || [])) {
        if (it.code && it.name && !map.has(it.code)) {
          map.set(it.code, it.name);
        }
      }
    }
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [quotes]);

  const filtered = quotes.filter(q => {
    const matchesSearch = !search ||
      q.client_name?.toLowerCase().includes(search.toLowerCase()) ||
      q.quote_number?.includes(search) ||
      q.client_email?.toLowerCase().includes(search.toLowerCase());
    const matchesClient = !selectedClient || q.client_id === selectedClient;
    const matchesProduct = !selectedProduct || (q.items || []).some(it => it.code === selectedProduct);
    return matchesSearch && matchesClient && matchesProduct;
  });

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
          {isAdmin && (
            <Button variant="outline" size="sm" onClick={handleExportExcel} data-testid="export-quotes-btn">
              <Download size={16} className="mr-1" /> Exportar
            </Button>
          )}
          {isAdmin && (
            <>
              <input type="file" accept=".xlsx" onChange={handleImport} className="hidden" id="import-quotes-file" />
              <Button variant="outline" size="sm" disabled={importing} onClick={() => document.getElementById("import-quotes-file").click()} data-testid="import-quotes-btn">
                {importing ? <Loader2 size={16} className="mr-1 animate-spin" /> : <Upload size={16} className="mr-1" />} Importar
              </Button>
            </>
          )}
          <Button variant="outline" size="sm" onClick={fetchActivities} data-testid="activities-btn">
            <Clock size={16} className="mr-1" /> Actividad
          </Button>
          {isAdmin && (
            <Button variant={showTrash ? "default" : "outline"} size="sm" onClick={() => setShowTrash(!showTrash)} data-testid="toggle-trash-btn">
              <Archive size={16} className="mr-1" /> {showTrash ? "Ver activos" : "Papelera"}
            </Button>
          )}
          {!showTrash && (
            <Button size="sm" className="bg-[#63AC9A] hover:bg-[#4F9A87]" onClick={() => navigate(`${newPath}?type=${docType}`)} data-testid="new-quote-btn">
              <Plus size={16} className="mr-1" /> {isPO ? "Nueva OC" : "Nueva Cotización"}
            </Button>
          )}
        </div>
      </div>

      {/* Search + Client Filter */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <Input placeholder="Buscar por cliente, número..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9 bg-white" data-testid="search-quotes-input" />
        </div>
        <select
          value={selectedClient}
          onChange={e => setSelectedClient(e.target.value)}
          className="h-9 border rounded-md px-3 text-sm bg-white text-gray-700 min-w-[180px]"
          data-testid="client-filter-select"
        >
          <option value="">Todos los clientes</option>
          {clients.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select
          value={selectedProduct}
          onChange={e => setSelectedProduct(e.target.value)}
          className="h-9 border rounded-md px-3 text-sm bg-white text-gray-700 min-w-[200px]"
          data-testid="product-filter-select"
        >
          <option value="">Todos los productos</option>
          {quotedProducts.map(([code, name]) => (
            <option key={code} value={code}>{code} - {name}</option>
          ))}
        </select>
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
                    {q.doc_type === "PO" && (
                      <Button variant="ghost" size="sm" onClick={() => openFacturaModal(q)} className="text-xs text-orange-600" data-testid={`factura-btn-${q.id}`}>
                        <FileText size={14} className="mr-1" /> {q.factura || (q.po_header_data?.factura) || "no asignado"}
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => setSendModal(q)} className="text-xs text-blue-600" data-testid={`send-btn-${q.id}`}>
                      <Send size={14} className="mr-1" /> Enviar
                    </Button>
                    {q.doc_type === "QUOTE" && (
                      <Button variant="ghost" size="sm" onClick={() => handleConvertToPO(q.id)} className="text-xs text-purple-600" data-testid={`convert-po-btn-${q.id}`}>
                        <ShoppingBag size={14} className="mr-1" /> Crear Orden
                      </Button>
                    )}
                    {isAdmin && (
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(q.id)} className="text-xs text-red-500">
                        <Trash2 size={14} />
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Factura Modal */}
      {facturaModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="factura-modal">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white rounded-t-2xl z-10">
              <h2 className="font-bold text-sm">Datos para PDF - OC #{facturaModal.quote_number}</h2>
              <button onClick={() => setFacturaModal(null)} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
            </div>
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-0.5 block">Fecha</label>
                  <Input value={facturaFields.fecha} onChange={e => setFacturaFields({...facturaFields, fecha: e.target.value})} className="h-8 text-sm" data-testid="factura-fecha" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-0.5 block">Orden de Compra Cliente</label>
                  <Input value={facturaFields.orden_compra_cliente} onChange={e => setFacturaFields({...facturaFields, orden_compra_cliente: e.target.value})} className="h-8 text-sm" data-testid="factura-oc-cliente" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-0.5 block">Cliente</label>
                  <Input value={facturaFields.cliente} onChange={e => setFacturaFields({...facturaFields, cliente: e.target.value})} className="h-8 text-sm" data-testid="factura-cliente" />
                </div>
                <div>
                  <label className="text-xs font-medium text-orange-600 mb-0.5 block font-bold">Factura</label>
                  <Input value={facturaFields.factura} onChange={e => setFacturaFields({...facturaFields, factura: e.target.value})} placeholder="Ej: FAC-001-2026" className="h-8 text-sm border-orange-300 focus:ring-orange-400" data-testid="factura-input" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-0.5 block">Dirección</label>
                  <Input value={facturaFields.direccion} onChange={e => setFacturaFields({...facturaFields, direccion: e.target.value})} className="h-8 text-sm" data-testid="factura-direccion" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-0.5 block">Teléfono</label>
                  <Input value={facturaFields.telefono} onChange={e => setFacturaFields({...facturaFields, telefono: e.target.value})} className="h-8 text-sm" data-testid="factura-telefono" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-0.5 block">Solicitado por</label>
                  <Input value={facturaFields.solicitado_por} onChange={e => setFacturaFields({...facturaFields, solicitado_por: e.target.value})} className="h-8 text-sm" data-testid="factura-solicitado" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-0.5 block">Correo</label>
                  <Input value={facturaFields.correo} onChange={e => setFacturaFields({...facturaFields, correo: e.target.value})} className="h-8 text-sm" data-testid="factura-correo" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs font-medium text-gray-500 mb-0.5 block">RUC</label>
                  <Input value={facturaFields.ruc} onChange={e => setFacturaFields({...facturaFields, ruc: e.target.value})} className="h-8 text-sm" data-testid="factura-ruc" />
                </div>
              </div>
              <div className="flex gap-2 mt-2">
                <Button
                  variant="outline"
                  className="flex-1 border-[#63AC9A] text-[#63AC9A] hover:bg-[#63AC9A]/10"
                  onClick={savePOHeader}
                  disabled={savingPOHeader}
                  data-testid="save-po-header-btn"
                >
                  {savingPOHeader ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Save size={14} className="mr-1" />}
                  Guardar Datos
                </Button>
                <Button
                  className="flex-1 bg-[#63AC9A] hover:bg-[#4F9A87] text-white"
                  onClick={() => {
                    handleGeneratePDF(facturaModal.id, "ORDEN_COMPRA", {
                      address: facturaFields.direccion,
                      phone: facturaFields.telefono,
                      email: facturaFields.correo,
                      tax_id: facturaFields.ruc,
                      contact_person: facturaFields.solicitado_por,
                      name: facturaFields.cliente,
                      factura: facturaFields.factura,
                      fecha_override: facturaFields.fecha,
                      orden_compra_cliente: facturaFields.orden_compra_cliente,
                    });
                    setFacturaModal(null);
                  }}
                  data-testid="generate-factura-pdf-btn"
                >
                  <Eye size={14} className="mr-1" /> Generar PDF
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

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
                <div key={a.id || `activity-${i}`} className="flex items-start gap-2 py-2 border-b last:border-0">
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
  const headers = {};

  useEffect(() => {
    const initial = [];
    if (quote.client_email) initial.push(quote.client_email);
    if (quote.client_id) {
      axios.get(`${API_URL}/api/clients/`, { headers }).then(res => {
        const c = (res.data || []).find(cl => cl.id === quote.client_id);
        if (c) {
          const all = [...initial];
          if (c.commercial_email && !all.includes(c.commercial_email)) all.push(c.commercial_email);
          if (c.email && !all.includes(c.email)) all.push(c.email);
          setEmails(all);
        } else {
          setEmails(initial);
        }
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
            <Input type="email" value={newEmail} onChange={e => setNewEmail(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addEmail())} placeholder="Agregar correos (separar con coma)..." data-testid="add-email-input" />
            <Button variant="outline" onClick={addEmail}>+</Button>
          </div>
          <div className="space-y-1">
            {emails.map((e, i) => (
              <div key={`email-${e}`} className="flex items-center justify-between bg-gray-50 rounded px-3 py-1.5 text-sm">
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
