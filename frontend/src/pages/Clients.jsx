import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import {
  Users, Plus, Edit, Trash2, Search, X, RotateCcw, Archive,
  Mail, Phone, MapPin, Building2, Loader2, History, Eye,
  FileText, User, Hash, StickyNote, Download
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const SECTORS = [
  "Tecnología", "Alimentos", "Educación", "Salud", "Retail",
  "Construcción", "Turismo", "Servicios", "Manufactura",
  "Gobierno", "Energía", "Otro"
];

export default function Clients() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [showTrash, setShowTrash] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editClient, setEditClient] = useState(null);
  const [selectedClient, setSelectedClient] = useState(null);
  const [detailClient, setDetailClient] = useState(null);
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchClients = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/clients/`, { params: { trash: showTrash }, headers });
      setClients(res.data || []);
    } catch { toast.error("Error al cargar clientes"); }
    setLoading(false);
  }, [showTrash]);

  useEffect(() => { fetchClients(); }, [fetchClients]);

  const handleDelete = async (id) => {
    if (!window.confirm(showTrash ? "¿Eliminar permanentemente?" : "¿Mover a papelera?")) return;
    try {
      await axios.delete(`${API_URL}/api/clients/${id}`, { params: { permanent: showTrash }, headers });
      toast.success(showTrash ? "Eliminado permanentemente" : "Movido a papelera");
      fetchClients();
    } catch { toast.error("Error al eliminar"); }
  };

  const handleRestore = async (id) => {
    try {
      await axios.post(`${API_URL}/api/clients/${id}/restore`, {}, { headers });
      toast.success("Cliente restaurado");
      fetchClients();
    } catch { toast.error("Error al restaurar"); }
  };

  const filtered = clients.filter(c =>
    !search || c.name?.toLowerCase().includes(search.toLowerCase()) ||
    c.email?.toLowerCase().includes(search.toLowerCase()) ||
    c.phone?.includes(search) || c.contact_person?.toLowerCase().includes(search.toLowerCase())
  );

  const handleExportExcel = () => {
    import("xlsx").then(XLSX => {
      const data = filtered.map(c => ({
        "Empresa / Nombre": c.name,
        "Contacto": c.contact_person,
        "Email": c.email,
        "Email Comercial": c.commercial_email,
        "Teléfono": c.phone,
        "Ciudad": c.city,
        "Dirección": c.address,
        "RUC / CI": c.tax_id,
        "Sector": c.sector,
        "Notas": c.notes,
        "Creado": c.created_at ? new Date(c.created_at).toLocaleDateString("es-EC") : ""
      }));
      const ws = XLSX.utils.json_to_sheet(data);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Clientes");
      XLSX.writeFile(wb, "clientes_gimmicks.xlsx");
    });
  };

  return (
    <div className="p-4 lg:p-6" data-testid="clients-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Building2 size={24} className="text-[#63AC9A]" /> Clientes
          </h1>
          <p className="text-sm text-gray-500 mt-1">{filtered.length} clientes</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExportExcel} data-testid="export-clients-btn">
            <Download size={16} className="mr-1" /> Exportar
          </Button>
          <Button variant={showTrash ? "default" : "outline"} size="sm" onClick={() => setShowTrash(!showTrash)} data-testid="toggle-trash-btn">
            <Archive size={16} className="mr-1" /> {showTrash ? "Ver activos" : "Papelera"}
          </Button>
          {!showTrash && (
            <Button size="sm" className="bg-[#63AC9A] hover:bg-[#5E8A7A]" onClick={() => { setEditClient(null); setShowModal(true); }} data-testid="add-client-btn">
              <Plus size={16} className="mr-1" /> Nuevo Cliente
            </Button>
          )}
        </div>
      </div>

      <div className="relative max-w-md mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <Input placeholder="Buscar clientes..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9 bg-white" data-testid="search-clients-input" />
      </div>

      <div className="grid gap-3 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {loading ? (
          <div className="col-span-full flex justify-center py-10"><Loader2 size={24} className="animate-spin text-gray-400" /></div>
        ) : filtered.length === 0 ? (
          <div className="col-span-full text-center py-10 text-gray-400">
            {showTrash ? "No hay clientes en papelera" : "No se encontraron clientes"}
          </div>
        ) : filtered.map(client => (
          <div key={client.id} className="bg-white rounded-xl shadow-sm border p-3 hover:shadow-md transition-shadow" data-testid={`client-card-${client.id}`}>
            <div className="mb-2">
              <h3 className="font-bold text-gray-900 text-sm truncate">{client.name}</h3>
              {client.contact_person && <p className="text-xs text-gray-500 truncate">Contacto: {client.contact_person}</p>}
            </div>
            <div className="space-y-1 text-xs text-gray-600">
              {client.email && <p className="flex items-center gap-1.5 truncate"><Mail size={12} className="text-gray-400 flex-shrink-0" /> <span className="truncate">{client.email}</span></p>}
              {client.phone && <p className="flex items-center gap-1.5 truncate"><Phone size={12} className="text-gray-400 flex-shrink-0" /> {client.phone}</p>}
            </div>
            <div className="flex gap-1 border-t justify-center" style={{marginTop:'3px',paddingTop:'2px'}}>
              {showTrash ? (
                <>
                  <button onClick={() => handleRestore(client.id)} className="p-2 rounded-lg hover:bg-green-50 text-green-600 transition-colors" title="Restaurar">
                    <RotateCcw size={16} />
                  </button>
                  <button onClick={() => handleDelete(client.id)} className="p-2 rounded-lg hover:bg-red-50 text-red-500 transition-colors" title="Eliminar">
                    <Trash2 size={16} />
                  </button>
                </>
              ) : (
                <>
                  <button onClick={() => setDetailClient(client)} className="p-2 rounded-lg hover:bg-[#63AC9A]/10 text-[#63AC9A] transition-colors" title="Ver información" data-testid={`view-btn-${client.id}`}>
                    <Eye size={16} />
                  </button>
                  <button onClick={() => setSelectedClient(client)} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors" title="Historial" data-testid={`history-btn-${client.id}`}>
                    <History size={16} />
                  </button>
                  <button onClick={() => { setEditClient(client); setShowModal(true); }} className="p-2 rounded-lg hover:bg-blue-50 text-blue-600 transition-colors" title="Editar" data-testid={`edit-client-btn-${client.id}`}>
                    <Edit size={16} />
                  </button>
                  <button onClick={() => handleDelete(client.id)} className="p-2 rounded-lg hover:bg-red-50 text-red-500 transition-colors" title="Eliminar">
                    <Trash2 size={16} />
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <ClientModal
          client={editClient}
          onClose={() => { setShowModal(false); setEditClient(null); }}
          onSave={() => { setShowModal(false); setEditClient(null); fetchClients(); }}
        />
      )}

      {selectedClient && (
        <ClientHistoryModal
          client={selectedClient}
          onClose={() => setSelectedClient(null)}
        />
      )}

      {detailClient && (
        <ClientDetailModal
          client={detailClient}
          onClose={() => setDetailClient(null)}
        />
      )}
    </div>
  );
}

function ClientModal({ client, onClose, onSave }) {
  const isEdit = !!client;
  const [form, setForm] = useState({
    id: client?.id || undefined,
    name: client?.name || "",
    email: client?.email || "",
    commercial_email: client?.commercial_email || "",
    phone: client?.phone || "",
    contact_person: client?.contact_person || "",
    address: client?.address || "",
    city: client?.city || "",
    tax_id: client?.tax_id || "",
    sector: client?.sector || "",
    sector_details: client?.sector_details || "",
    notes: client?.notes || ""
  });
  const [saving, setSaving] = useState(false);
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const handleSave = async () => {
    if (!form.name || !form.email) { toast.error("Nombre y email son requeridos"); return; }
    setSaving(true);
    try {
      if (isEdit) {
        await axios.put(`${API_URL}/api/clients/${client.id}`, form, { headers });
        toast.success("Cliente actualizado");
      } else {
        await axios.post(`${API_URL}/api/clients/`, form, { headers });
        toast.success("Cliente creado");
      }
      onSave();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error al guardar");
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="client-modal">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-bold">{isEdit ? "Editar Cliente" : "Nuevo Cliente"}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Nombre / Empresa *</label>
            <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="client-name-input" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Email *</label>
              <Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} data-testid="client-email-input" />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Email comercial</label>
              <Input type="email" value={form.commercial_email} onChange={e => setForm({ ...form, commercial_email: e.target.value })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Teléfono</label>
              <Input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Persona de contacto</label>
              <Input value={form.contact_person} onChange={e => setForm({ ...form, contact_person: e.target.value })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Ciudad</label>
              <Input value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">RUC / CI</label>
              <Input value={form.tax_id} onChange={e => setForm({ ...form, tax_id: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Dirección</label>
            <Input value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Sector</label>
            <select value={form.sector} onChange={e => setForm({ ...form, sector: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="">Seleccionar...</option>
              {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Notas</label>
            <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
          </div>
        </div>
        <div className="flex justify-end gap-2 p-5 border-t">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button className="bg-[#63AC9A] hover:bg-[#5E8A7A]" onClick={handleSave} disabled={saving} data-testid="save-client-btn">
            {saving ? <Loader2 size={16} className="animate-spin mr-1" /> : null}
            {isEdit ? "Actualizar" : "Crear"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ClientHistoryModal({ client, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get(`${API_URL}/api/clients/${client.id}/history`, { headers });
        setData(res.data);
      } catch { toast.error("Error al cargar historial"); }
      setLoading(false);
    })();
  }, [client.id]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-bold">Historial: {client.name}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
        </div>
        <div className="p-5">
          {loading ? (
            <div className="flex justify-center py-5"><Loader2 size={24} className="animate-spin text-gray-400" /></div>
          ) : (
            <>
              <h3 className="font-semibold text-sm text-gray-700 mb-2">Cotizaciones ({data?.quotes?.length || 0})</h3>
              {data?.quotes?.length > 0 ? (
                <div className="space-y-2 mb-4">
                  {data.quotes.map(q => (
                    <div key={q.id} className="bg-gray-50 rounded-lg p-3 text-sm">
                      <div className="flex justify-between"><span className="font-medium">#{q.quote_number}</span><span className="text-gray-500">{q.doc_type}</span></div>
                      <div className="text-gray-500 text-xs">{new Date(q.created_at).toLocaleDateString()}</div>
                    </div>
                  ))}
                </div>
              ) : <p className="text-gray-400 text-sm mb-4">Sin cotizaciones</p>}
              <h3 className="font-semibold text-sm text-gray-700 mb-2">Actividad ({data?.activities?.length || 0})</h3>
              {data?.activities?.length > 0 ? (
                <div className="space-y-2">
                  {data.activities.map(a => (
                    <div key={a.id} className="text-sm text-gray-600 flex items-start gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#63AC9A] mt-1.5 flex-shrink-0" />
                      <div>
                        <span>{a.details}</span>
                        <div className="text-xs text-gray-400">{new Date(a.timestamp).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : <p className="text-gray-400 text-sm">Sin actividad</p>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}


function ClientDetailModal({ client, onClose }) {
  const rows = [
    { icon: User, label: "Persona de contacto", value: client.contact_person },
    { icon: Mail, label: "Email", value: client.email },
    { icon: Mail, label: "Email comercial", value: client.commercial_email },
    { icon: Phone, label: "Teléfono", value: client.phone },
    { icon: MapPin, label: "Ciudad", value: client.city },
    { icon: MapPin, label: "Dirección", value: client.address },
    { icon: Hash, label: "RUC / CI", value: client.tax_id },
    { icon: FileText, label: "Sector", value: client.sector },
    { icon: StickyNote, label: "Notas", value: client.notes },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="client-detail-modal">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Eye size={20} className="text-[#63AC9A]" /> {client.name}
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded" data-testid="close-detail-modal-btn"><X size={20} /></button>
        </div>
        <div className="p-5 space-y-3">
          {rows.map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-start gap-3">
              <Icon size={16} className="text-[#63AC9A] mt-0.5 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs text-gray-400 leading-none mb-0.5">{label}</p>
                <p className="text-sm text-gray-800 break-words">{value || <span className="text-gray-300 italic">No registrado</span>}</p>
              </div>
            </div>
          ))}
          {client.created_at && (
            <div className="pt-3 mt-3 border-t text-xs text-gray-400">
              Creado: {new Date(client.created_at).toLocaleDateString("es-EC", { year: "numeric", month: "long", day: "numeric" })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
