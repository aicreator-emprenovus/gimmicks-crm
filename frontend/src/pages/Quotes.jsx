import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Loader2,
  Send,
  Eye,
  Trash2,
  FileText,
  Phone,
  Mail,
  Building2,
  MapPin,
  Package,
  Calendar,
  Edit,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_MAP = {
  pending: { label: "Pendiente", color: "bg-amber-100 text-amber-700 border-amber-300" },
  sent: { label: "Enviada", color: "bg-emerald-100 text-emerald-700 border-emerald-300" },
  approved: { label: "Aprobada", color: "bg-blue-100 text-blue-700 border-blue-300" },
};

export default function Quotes() {
  const { getAuthHeaders } = useAuth();
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("all");
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [editingQuote, setEditingQuote] = useState(null);
  const [editData, setEditData] = useState({ total: 0, notes: "" });
  const [sending, setSending] = useState(null);

  const fetchQuotes = async () => {
    try {
      const params = filterStatus !== "all" ? `?status=${filterStatus}` : "";
      const res = await axios.get(`${API_URL}/api/quotes${params}`, { headers: getAuthHeaders() });
      setQuotes(res.data);
    } catch {
      toast.error("Error al cargar cotizaciones");
    } finally {
      setLoading(false);
    }
  };

  const sendQuote = async (quoteId) => {
    setSending(quoteId);
    try {
      await axios.post(`${API_URL}/api/quotes/${quoteId}/send`, {}, { headers: getAuthHeaders() });
      toast.success("Cotizacion enviada al correo del cliente");
      fetchQuotes();
    } catch (err) {
      const msg = err.response?.data?.detail || "Error al enviar cotizacion";
      toast.error(msg);
    } finally {
      setSending(null);
    }
  };

  const updateQuote = async () => {
    if (!editingQuote) return;
    try {
      await axios.patch(`${API_URL}/api/quotes/${editingQuote.id}`, editData, { headers: getAuthHeaders() });
      toast.success("Cotizacion actualizada");
      setEditingQuote(null);
      fetchQuotes();
    } catch {
      toast.error("Error al actualizar");
    }
  };

  const deleteQuote = async (quoteId) => {
    if (!confirm("Eliminar esta cotizacion?")) return;
    try {
      await axios.delete(`${API_URL}/api/quotes/${quoteId}`, { headers: getAuthHeaders() });
      toast.success("Cotizacion eliminada");
      fetchQuotes();
    } catch {
      toast.error("Error al eliminar");
    }
  };

  useEffect(() => { fetchQuotes(); }, [filterStatus]);

  const formatDate = (d) => {
    if (!d) return "-";
    try { return format(new Date(d), "dd/MM/yy HH:mm", { locale: es }); } catch { return "-"; }
  };

  const getStatus = (s) => STATUS_MAP[s] || STATUS_MAP.pending;

  return (
    <div className="p-6 space-y-6" data-testid="quotes-page">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 font-['Manrope']" data-testid="quotes-title">
            Cotizaciones
          </h1>
          <p className="text-zinc-500 text-sm">Revisa y envia cotizaciones generadas por el bot</p>
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[180px]" data-testid="filter-status-select">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            <SelectItem value="pending">Pendientes</SelectItem>
            <SelectItem value="sent">Enviadas</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-[#7BA899]" />
        </div>
      ) : quotes.length === 0 ? (
        <div className="text-center py-16 text-zinc-400">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No hay cotizaciones</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {quotes.map((q) => {
            const st = getStatus(q.status);
            return (
              <Card key={q.id} className="border border-zinc-200 hover:shadow-md transition-shadow" data-testid={`quote-card-${q.id}`}>
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-zinc-900 text-sm">{q.client_name || "Sin nombre"}</p>
                      <p className="text-xs text-zinc-500 flex items-center gap-1">
                        <Phone className="w-3 h-3" />{q.phone_number}
                      </p>
                    </div>
                    <Badge className={`text-xs border ${st.color}`} data-testid={`quote-status-${q.id}`}>
                      {st.label}
                    </Badge>
                  </div>

                  <div className="space-y-1 text-xs text-zinc-600">
                    {q.client_empresa && <div className="flex items-center gap-1"><Building2 className="w-3 h-3" />{q.client_empresa}</div>}
                    {q.client_correo && <div className="flex items-center gap-1"><Mail className="w-3 h-3" />{q.client_correo}</div>}
                    {q.client_ciudad && <div className="flex items-center gap-1"><MapPin className="w-3 h-3" />{q.client_ciudad}</div>}
                  </div>

                  <div className="text-xs text-zinc-500">
                    <span className="flex items-center gap-1"><Package className="w-3 h-3" />
                      {q.items?.length || 0} producto(s)
                      {q.cantidad && ` - ${q.cantidad} unidades`}
                    </span>
                    {q.personalizacion && <span className="block mt-0.5">Pers: {q.personalizacion}</span>}
                    {q.fecha_entrega && <span className="flex items-center gap-1 mt-0.5"><Calendar className="w-3 h-3" />{q.fecha_entrega}</span>}
                  </div>

                  {q.total > 0 && (
                    <p className="text-sm font-bold text-[#7BA899]">Total: ${q.total.toLocaleString("es-EC", { minimumFractionDigits: 2 })}</p>
                  )}

                  <div className="flex items-center gap-1 text-xs text-zinc-400">
                    <Calendar className="w-3 h-3" />{formatDate(q.created_at)}
                  </div>

                  <div className="flex gap-2 pt-1">
                    <Button size="sm" variant="outline" className="h-8 text-xs gap-1" onClick={() => setSelectedQuote(q)} data-testid={`view-quote-${q.id}`}>
                      <Eye className="w-3 h-3" /> Ver
                    </Button>
                    <Button size="sm" variant="outline" className="h-8 text-xs gap-1" onClick={() => { setEditingQuote(q); setEditData({ total: q.total, notes: q.notes || "" }); }} data-testid={`edit-quote-${q.id}`}>
                      <Edit className="w-3 h-3" /> Editar
                    </Button>
                    {q.status === "pending" && (
                      <Button
                        size="sm"
                        className="h-8 text-xs gap-1 bg-[#7BA899] hover:bg-[#6A9688] text-white"
                        onClick={() => sendQuote(q.id)}
                        disabled={sending === q.id}
                        data-testid={`send-quote-${q.id}`}
                      >
                        {sending === q.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                        Enviar
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-500" onClick={() => deleteQuote(q.id)} data-testid={`delete-quote-${q.id}`}>
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Detail Dialog */}
      <Dialog open={!!selectedQuote} onOpenChange={(o) => !o && setSelectedQuote(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-['Manrope']">Detalle de Cotizacion</DialogTitle>
          </DialogHeader>
          {selectedQuote && (
            <div className="space-y-4 text-sm" data-testid="quote-detail">
              <div className="grid grid-cols-2 gap-3">
                <div><span className="text-zinc-400 text-xs">Cliente</span><p className="font-medium">{selectedQuote.client_name || "-"}</p></div>
                <div><span className="text-zinc-400 text-xs">Empresa</span><p className="font-medium">{selectedQuote.client_empresa || "-"}</p></div>
                <div><span className="text-zinc-400 text-xs">Correo</span><p className="font-medium">{selectedQuote.client_correo || "-"}</p></div>
                <div><span className="text-zinc-400 text-xs">Ciudad</span><p className="font-medium">{selectedQuote.client_ciudad || "-"}</p></div>
                <div><span className="text-zinc-400 text-xs">Cantidad</span><p className="font-medium">{selectedQuote.cantidad || "-"}</p></div>
                <div><span className="text-zinc-400 text-xs">Fecha entrega</span><p className="font-medium">{selectedQuote.fecha_entrega || "-"}</p></div>
                <div className="col-span-2"><span className="text-zinc-400 text-xs">Personalizacion</span><p className="font-medium">{selectedQuote.personalizacion || "-"}</p></div>
              </div>
              <div>
                <span className="text-zinc-400 text-xs">Productos</span>
                <div className="mt-1 space-y-2">
                  {selectedQuote.items?.map((item, i) => (
                    <div key={i} className="bg-zinc-50 p-2 rounded text-xs">
                      <span className="font-mono text-[#7BA899]">{item.code || item.product_id}</span>
                      <span className="ml-2 font-medium">{item.product_name}</span>
                      {item.description && <p className="text-zinc-500 mt-0.5">{item.description}</p>}
                    </div>
                  ))}
                  {(!selectedQuote.items || selectedQuote.items.length === 0) && <p className="text-zinc-400">Sin productos</p>}
                </div>
              </div>
              {selectedQuote.notes && (
                <div><span className="text-zinc-400 text-xs">Notas</span><p>{selectedQuote.notes}</p></div>
              )}
              {selectedQuote.total > 0 && (
                <p className="text-lg font-bold text-[#7BA899]">Total: ${selectedQuote.total.toLocaleString("es-EC", { minimumFractionDigits: 2 })}</p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingQuote} onOpenChange={(o) => !o && setEditingQuote(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Manrope']">Editar Cotizacion</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label>Total ($)</Label>
              <Input type="number" step="0.01" value={editData.total} onChange={(e) => setEditData({ ...editData, total: parseFloat(e.target.value) || 0 })} data-testid="edit-quote-total" />
            </div>
            <div className="space-y-2">
              <Label>Notas</Label>
              <Textarea value={editData.notes} onChange={(e) => setEditData({ ...editData, notes: e.target.value })} placeholder="Notas adicionales para la cotizacion..." data-testid="edit-quote-notes" />
            </div>
            <Button onClick={updateQuote} className="w-full bg-[#7BA899] hover:bg-[#6A9688] text-white" data-testid="save-quote-btn">
              Guardar Cambios
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
