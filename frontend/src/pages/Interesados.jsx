import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import {
  Search, Loader2, Mail, Phone, Eye, X, ArrowRightCircle,
  User, MapPin, Hash, FileText, StickyNote, MessageCircle,
  Trash2, Building2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/AuthContext";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Interesados() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [interesados, setInteresados] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [detailClient, setDetailClient] = useState(null);
  const headers = {};

  const fetchInteresados = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/clients/`, {
        params: { source: "whatsapp", trash: false },
        headers
      });
      setInteresados(res.data || []);
    } catch { toast.error("Error al cargar interesados"); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchInteresados(); }, [fetchInteresados]);

  const handlePromote = async (id, name) => {
    if (!window.confirm(`¿Promover a "${name}" como Cliente?`)) return;
    try {
      await axios.post(`${API_URL}/api/clients/${id}/promote`, {}, { headers });
      toast.success(`${name} promovido a Cliente`);
      fetchInteresados();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error al promover");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("¿Mover a papelera?")) return;
    try {
      await axios.delete(`${API_URL}/api/clients/${id}`, { headers });
      toast.success("Movido a papelera");
      fetchInteresados();
    } catch { toast.error("Error al eliminar"); }
  };

  const filtered = interesados.filter(c =>
    !search || c.name?.toLowerCase().includes(search.toLowerCase()) ||
    c.email?.toLowerCase().includes(search.toLowerCase()) ||
    c.phone?.includes(search) || c.contact_person?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-4 lg:p-6" data-testid="interesados-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <MessageCircle size={24} className="text-[#25D366]" /> Interesados
          </h1>
          <p className="text-sm text-gray-500 mt-1">{filtered.length} interesados via WhatsApp</p>
        </div>
      </div>

      <div className="relative max-w-md mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <Input
          placeholder="Buscar interesados..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 bg-white"
          data-testid="search-interesados-input"
        />
      </div>

      <div className="grid gap-3 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {loading ? (
          <div className="col-span-full flex justify-center py-10">
            <Loader2 size={24} className="animate-spin text-gray-400" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="col-span-full text-center py-10 text-gray-400">
            No se encontraron interesados
          </div>
        ) : filtered.map(client => (
          <div
            key={client.id}
            className="bg-white rounded-xl shadow-sm border p-3 hover:shadow-md transition-shadow"
            data-testid={`interesado-card-${client.id}`}
          >
            <div className="mb-2">
              <div className="flex items-center gap-1.5">
                <h3 className="font-bold text-gray-900 text-sm truncate flex-1">{client.name}</h3>
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#25D366]/10 flex items-center justify-center" title="Via WhatsApp">
                  <MessageCircle size={12} className="text-[#25D366]" />
                </span>
              </div>
              {client.contact_person && (
                <p className="text-xs text-gray-500 truncate">Contacto: {client.contact_person}</p>
              )}
            </div>
            <div className="space-y-1 text-xs text-gray-600">
              {client.email && (
                <p className="flex items-center gap-1.5 truncate">
                  <Mail size={12} className="text-gray-400 flex-shrink-0" />
                  <span className="truncate">{client.email}</span>
                </p>
              )}
              {client.phone && (
                <p className="flex items-center gap-1.5 truncate">
                  <Phone size={12} className="text-gray-400 flex-shrink-0" />
                  {client.phone}
                </p>
              )}
            </div>
            <div className="flex gap-1 border-t justify-center" style={{ marginTop: "3px", paddingTop: "2px" }}>
              <button
                onClick={() => setDetailClient(client)}
                className="p-2 rounded-lg hover:bg-[#63AC9A]/10 text-[#63AC9A] transition-colors"
                title="Ver información"
                data-testid={`view-interesado-${client.id}`}
              >
                <Eye size={16} />
              </button>
              <button
                onClick={() => handlePromote(client.id, client.name)}
                className="p-2 rounded-lg hover:bg-[#25D366]/10 text-[#25D366] transition-colors"
                title="Promover a Cliente"
                data-testid={`promote-btn-${client.id}`}
              >
                <ArrowRightCircle size={16} />
              </button>
              {isAdmin && (
                <button
                  onClick={() => handleDelete(client.id)}
                  className="p-2 rounded-lg hover:bg-red-50 text-red-500 transition-colors"
                  title="Eliminar"
                  data-testid={`delete-interesado-${client.id}`}
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {detailClient && (
        <InteresadoDetailModal
          client={detailClient}
          onClose={() => setDetailClient(null)}
          onPromote={() => {
            handlePromote(detailClient.id, detailClient.name);
            setDetailClient(null);
          }}
        />
      )}
    </div>
  );
}

function InteresadoDetailModal({ client, onClose, onPromote }) {
  const rows = [
    { icon: User, label: "Persona de contacto", value: client.contact_person },
    { icon: Mail, label: "Email", value: client.email },
    { icon: Phone, label: "Telefono", value: client.phone },
    { icon: MapPin, label: "Ciudad", value: client.city },
    { icon: MapPin, label: "Direccion", value: client.address },
    { icon: Building2, label: "Empresa", value: client.sector_details },
    { icon: Hash, label: "RUC / CI", value: client.tax_id },
    { icon: FileText, label: "Sector", value: client.sector },
    { icon: StickyNote, label: "Notas", value: client.notes },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="interesado-detail-modal">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <MessageCircle size={20} className="text-[#25D366]" /> {client.name}
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded" data-testid="close-interesado-detail">
            <X size={20} />
          </button>
        </div>
        <div className="p-5 space-y-3">
          {rows.map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-start gap-3">
              <Icon size={16} className="text-[#63AC9A] mt-0.5 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs text-gray-400 leading-none mb-0.5">{label}</p>
                <p className="text-sm text-gray-800 break-words">
                  {value || <span className="text-gray-300 italic">No registrado</span>}
                </p>
              </div>
            </div>
          ))}
          {client.created_at && (
            <div className="pt-3 mt-3 border-t text-xs text-gray-400">
              Registrado: {new Date(client.created_at).toLocaleDateString("es-EC", { year: "numeric", month: "long", day: "numeric" })}
            </div>
          )}
        </div>
        <div className="p-5 border-t">
          <Button
            className="w-full bg-[#25D366] hover:bg-[#1da851] text-white"
            onClick={onPromote}
            data-testid="promote-from-detail-btn"
          >
            <ArrowRightCircle size={16} className="mr-2" /> Promover a Cliente
          </Button>
        </div>
      </div>
    </div>
  );
}
