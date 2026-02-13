import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Search,
  Plus,
  Phone,
  Calendar,
  Edit,
  Trash2,
  Loader2,
  Filter,
  Building2,
  MapPin,
  Mail,
  Package,
  DollarSign,
  Eye,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const FUNNEL_STAGES = [
  { value: "lead", label: "Lead", color: "bg-blue-100 text-blue-700 border-blue-200" },
  { value: "pedido", label: "Pedido", color: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  { value: "produccion", label: "Produccion", color: "bg-purple-100 text-purple-700 border-purple-200" },
  { value: "entregado", label: "Entregado", color: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  { value: "perdido", label: "Perdido", color: "bg-red-100 text-red-700 border-red-200" },
  { value: "cierre", label: "Cierre", color: "bg-green-100 text-green-700 border-green-200" }
];

const CLASSIFICATIONS = [
  { value: "frio", label: "Frio", color: "bg-sky-100 text-sky-700 border-sky-300", dot: "bg-sky-500" },
  { value: "tibio", label: "Tibio", color: "bg-amber-100 text-amber-700 border-amber-300", dot: "bg-amber-500" },
  { value: "caliente", label: "Caliente", color: "bg-rose-100 text-rose-700 border-rose-300", dot: "bg-rose-500" }
];

const CATEGORIES = [
  { value: "cotizacion_directa", label: "Cotizacion", color: "text-emerald-600 bg-emerald-50" },
  { value: "solicitud_catalogo", label: "Catalogo", color: "text-blue-600 bg-blue-50" },
  { value: "consulta_ideas", label: "Ideas", color: "text-violet-600 bg-violet-50" },
  { value: "pedido_estacional", label: "Estacional", color: "text-orange-600 bg-orange-50" },
  { value: "otra", label: "Otra", color: "text-zinc-600 bg-zinc-50" }
];

const SOURCES = [
  { value: "whatsapp", label: "WhatsApp" },
  { value: "meta_ads", label: "Meta Ads" },
  { value: "web", label: "Web" },
  { value: "organico", label: "Organico" }
];

export default function Leads() {
  const { getAuthHeaders } = useAuth();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStage, setFilterStage] = useState("all");
  const [filterClassification, setFilterClassification] = useState("all");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [detailLead, setDetailLead] = useState(null);
  const [formData, setFormData] = useState({
    phone_number: "",
    name: "",
    source: "whatsapp",
    notes: ""
  });

  const fetchLeads = async () => {
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append("search", searchTerm);
      if (filterStage && filterStage !== "all") params.append("stage", filterStage);
      if (filterClassification && filterClassification !== "all") params.append("classification", filterClassification);

      const response = await axios.get(`${API_URL}/api/leads?${params}`, {
        headers: getAuthHeaders()
      });
      setLeads(response.data);
    } catch (error) {
      toast.error("Error al cargar leads");
    } finally {
      setLoading(false);
    }
  };

  const createLead = async () => {
    try {
      await axios.post(`${API_URL}/api/leads`, formData, {
        headers: getAuthHeaders()
      });
      toast.success("Lead creado exitosamente");
      setIsCreateOpen(false);
      resetForm();
      fetchLeads();
    } catch (error) {
      toast.error("Error al crear lead");
    }
  };

  const updateLead = async () => {
    if (!editingLead) return;
    try {
      await axios.patch(`${API_URL}/api/leads/${editingLead.id}`, {
        name: formData.name,
        notes: formData.notes,
        funnel_stage: formData.funnel_stage,
        classification: formData.classification
      }, {
        headers: getAuthHeaders()
      });
      toast.success("Lead actualizado");
      setEditingLead(null);
      resetForm();
      fetchLeads();
    } catch (error) {
      toast.error("Error al actualizar lead");
    }
  };

  const deleteLead = async (leadId) => {
    if (!confirm("Eliminar este lead?")) return;
    try {
      await axios.delete(`${API_URL}/api/leads/${leadId}`, {
        headers: getAuthHeaders()
      });
      toast.success("Lead eliminado");
      fetchLeads();
    } catch (error) {
      toast.error("Error al eliminar lead");
    }
  };

  const updateLeadStage = async (leadId, newStage) => {
    try {
      await axios.patch(`${API_URL}/api/leads/${leadId}`, {
        funnel_stage: newStage
      }, {
        headers: getAuthHeaders()
      });
      toast.success("Etapa actualizada");
      fetchLeads();
    } catch (error) {
      toast.error("Error al actualizar etapa");
    }
  };

  const resetForm = () => {
    setFormData({ phone_number: "", name: "", source: "whatsapp", notes: "" });
  };

  const openEditDialog = (lead) => {
    setEditingLead(lead);
    setFormData({
      phone_number: lead.phone_number,
      name: lead.name || "",
      source: lead.source,
      notes: lead.notes || "",
      funnel_stage: lead.funnel_stage,
      classification: lead.classification
    });
  };

  useEffect(() => {
    fetchLeads();
  }, [searchTerm, filterStage, filterClassification]);

  const getStageColor = (stage) => FUNNEL_STAGES.find(s => s.value === stage)?.color || "";
  const getClassification = (val) => CLASSIFICATIONS.find(c => c.value === val) || CLASSIFICATIONS[0];
  const getCategoryLabel = (val) => CATEGORIES.find(c => c.value === val) || null;

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return format(new Date(dateStr), "dd/MM/yy HH:mm", { locale: es });
    } catch {
      return "-";
    }
  };

  const leadsByStage = FUNNEL_STAGES.reduce((acc, stage) => {
    acc[stage.value] = leads.filter(l => l.funnel_stage === stage.value);
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-6" data-testid="leads-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 font-['Manrope']" data-testid="leads-title">
            Gestion de Leads
          </h1>
          <p className="text-zinc-500 text-sm">
            Funnel de ventas con IA
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button className="bg-[#7BA899] hover:bg-[#6A9688] gap-2 text-white" data-testid="create-lead-btn">
              <Plus size={18} />
              Nuevo Lead
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="font-['Manrope']">Crear Nuevo Lead</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Telefono *</Label>
                <Input placeholder="+593999999999" value={formData.phone_number} onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })} data-testid="lead-phone-input" />
              </div>
              <div className="space-y-2">
                <Label>Nombre</Label>
                <Input placeholder="Nombre del contacto" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} data-testid="lead-name-input" />
              </div>
              <div className="space-y-2">
                <Label>Fuente</Label>
                <Select value={formData.source} onValueChange={(v) => setFormData({ ...formData, source: v })}>
                  <SelectTrigger data-testid="lead-source-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {SOURCES.map(s => (<SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Notas</Label>
                <Textarea placeholder="Notas adicionales..." value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} data-testid="lead-notes-input" />
              </div>
              <Button onClick={createLead} className="w-full bg-[#7BA899] hover:bg-[#6A9688] text-white" data-testid="submit-lead-btn">
                Crear Lead
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input placeholder="Buscar por nombre o telefono..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" data-testid="search-leads-input" />
        </div>
        <Select value={filterStage} onValueChange={setFilterStage}>
          <SelectTrigger className="w-[160px]" data-testid="filter-stage-select">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Etapa" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {FUNNEL_STAGES.map(s => (<SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>))}
          </SelectContent>
        </Select>
        <Select value={filterClassification} onValueChange={setFilterClassification}>
          <SelectTrigger className="w-[160px]" data-testid="filter-class-select">
            <SelectValue placeholder="Clasificacion" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {CLASSIFICATIONS.map(c => (<SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>))}
          </SelectContent>
        </Select>
      </div>

      {/* Kanban Board */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-[#7BA899]" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {FUNNEL_STAGES.map(stage => (
            <div key={stage.value} className="space-y-3">
              <div className={`flex items-center gap-2 p-2 rounded-lg ${stage.color} border`}>
                <span className="font-medium text-sm">{stage.label}</span>
                <Badge variant="secondary" className="ml-auto">
                  {leadsByStage[stage.value]?.length || 0}
                </Badge>
              </div>
              <ScrollArea className="h-[500px]">
                <div className="space-y-2 pr-2">
                  {leadsByStage[stage.value]?.map(lead => {
                    const cls = getClassification(lead.classification);
                    const cat = getCategoryLabel(lead.ai_category);
                    return (
                      <Card key={lead.id} className="border border-zinc-200 hover:shadow-md transition-shadow" data-testid={`lead-card-${lead.id}`}>
                        <CardContent className="p-3 space-y-2">
                          {/* Header: avatar + name + quality badge */}
                          <div className="flex items-start justify-between gap-1">
                            <div className="flex items-center gap-2 min-w-0">
                              <div className="w-8 h-8 rounded-full bg-[#7BA899] flex items-center justify-center text-white text-sm font-medium shrink-0">
                                {lead.name?.charAt(0)?.toUpperCase() || "?"}
                              </div>
                              <div className="min-w-0">
                                <p className="font-medium text-zinc-900 text-sm truncate" data-testid={`lead-name-${lead.id}`}>
                                  {lead.name || "Sin nombre"}
                                </p>
                                <p className="text-xs text-zinc-500 flex items-center gap-1">
                                  <Phone className="w-3 h-3" />
                                  {lead.phone_number}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center shrink-0">
                              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold border ${cls.color}`} data-testid={`lead-quality-${lead.id}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${cls.dot}`} />
                                {cls.label}
                              </span>
                            </div>
                          </div>

                          {/* AI Category */}
                          {cat && (
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${cat.color}`} data-testid={`lead-category-${lead.id}`}>
                              {cat.label}
                            </span>
                          )}

                          {/* Key collected data */}
                          <div className="space-y-0.5 text-[11px] text-zinc-500">
                            {lead.empresa && (
                              <div className="flex items-center gap-1"><Building2 className="w-3 h-3" />{lead.empresa}</div>
                            )}
                            {lead.ciudad && (
                              <div className="flex items-center gap-1"><MapPin className="w-3 h-3" />{lead.ciudad}</div>
                            )}
                            {lead.producto_interes && (
                              <div className="flex items-center gap-1"><Package className="w-3 h-3" /><span className="truncate">{lead.producto_interes}</span></div>
                            )}
                          </div>

                          {/* Date */}
                          <div className="flex items-center gap-2 text-xs text-zinc-400">
                            <Calendar className="w-3 h-3" />
                            {formatDate(lead.created_at)}
                          </div>

                          {/* Actions */}
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setDetailLead(lead)} data-testid={`view-lead-${lead.id}`}>
                              <Eye className="w-3 h-3" />
                            </Button>
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => openEditDialog(lead)} data-testid={`edit-lead-${lead.id}`}>
                              <Edit className="w-3 h-3" />
                            </Button>
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-600" onClick={() => deleteLead(lead.id)} data-testid={`delete-lead-${lead.id}`}>
                              <Trash2 className="w-3 h-3" />
                            </Button>
                            <Select value={lead.funnel_stage} onValueChange={(v) => updateLeadStage(lead.id, v)}>
                              <SelectTrigger className="h-7 text-xs flex-1">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {FUNNEL_STAGES.map(s => (<SelectItem key={s.value} value={s.value} className="text-xs">{s.label}</SelectItem>))}
                              </SelectContent>
                            </Select>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                  {leadsByStage[stage.value]?.length === 0 && (
                    <div className="text-center py-4 text-zinc-400 text-sm">Sin leads</div>
                  )}
                </div>
              </ScrollArea>
            </div>
          ))}
        </div>
      )}

      {/* Detail Dialog */}
      <Dialog open={!!detailLead} onOpenChange={(open) => !open && setDetailLead(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-['Manrope'] flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#7BA899] flex items-center justify-center text-white text-lg font-bold">
                {detailLead?.name?.charAt(0)?.toUpperCase() || "?"}
              </div>
              <div>
                <span data-testid="detail-lead-name">{detailLead?.name || "Sin nombre"}</span>
                {detailLead && (
                  <span className={`ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${getClassification(detailLead.classification).color}`}>
                    <span className={`w-2 h-2 rounded-full ${getClassification(detailLead.classification).dot}`} />
                    {getClassification(detailLead.classification).label}
                  </span>
                )}
              </div>
            </DialogTitle>
          </DialogHeader>
          {detailLead && (
            <div className="space-y-4 mt-2" data-testid="lead-detail-content">
              {getCategoryLabel(detailLead.ai_category) && (
                <span className={`inline-block px-3 py-1 rounded-md text-xs font-medium ${getCategoryLabel(detailLead.ai_category).color}`}>
                  Categoria: {getCategoryLabel(detailLead.ai_category).label}
                </span>
              )}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="space-y-1">
                  <span className="text-zinc-400 text-xs flex items-center gap-1"><Phone className="w-3 h-3" />Telefono</span>
                  <p className="text-zinc-800 font-medium" data-testid="detail-lead-phone">{detailLead.phone_number}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-zinc-400 text-xs flex items-center gap-1"><Building2 className="w-3 h-3" />Empresa</span>
                  <p className="text-zinc-800 font-medium">{detailLead.empresa || "-"}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-zinc-400 text-xs flex items-center gap-1"><MapPin className="w-3 h-3" />Ciudad</span>
                  <p className="text-zinc-800 font-medium">{detailLead.ciudad || "-"}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-zinc-400 text-xs flex items-center gap-1"><Mail className="w-3 h-3" />Correo</span>
                  <p className="text-zinc-800 font-medium">{detailLead.correo || "-"}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-zinc-400 text-xs flex items-center gap-1"><Package className="w-3 h-3" />Producto</span>
                  <p className="text-zinc-800 font-medium">{detailLead.producto_interes || "-"}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-zinc-400 text-xs flex items-center gap-1">#Cantidad</span>
                  <p className="text-zinc-800 font-medium">{detailLead.cantidad_estimada || "-"}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-zinc-400 text-xs flex items-center gap-1"><DollarSign className="w-3 h-3" />Presupuesto</span>
                  <p className="text-zinc-800 font-medium">{detailLead.presupuesto || "-"}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-zinc-400 text-xs">Fuente</span>
                  <p className="text-zinc-800 font-medium">{detailLead.source}</p>
                </div>
              </div>
              {detailLead.notes && (
                <div className="text-sm">
                  <span className="text-zinc-400 text-xs">Notas</span>
                  <p className="text-zinc-700 mt-1">{detailLead.notes}</p>
                </div>
              )}
              <div className="text-xs text-zinc-400 pt-2 border-t">
                Creado: {formatDate(detailLead.created_at)} | Actualizado: {formatDate(detailLead.updated_at)}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingLead} onOpenChange={(open) => !open && setEditingLead(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Manrope']">Editar Lead</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Telefono</Label>
              <Input value={formData.phone_number} disabled className="bg-zinc-50" />
            </div>
            <div className="space-y-2">
              <Label>Nombre</Label>
              <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} data-testid="edit-lead-name" />
            </div>
            <div className="space-y-2">
              <Label>Etapa del Funnel</Label>
              <Select value={formData.funnel_stage} onValueChange={(v) => setFormData({ ...formData, funnel_stage: v })}>
                <SelectTrigger data-testid="edit-lead-stage"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {FUNNEL_STAGES.map(s => (<SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Clasificacion</Label>
              <Select value={formData.classification} onValueChange={(v) => setFormData({ ...formData, classification: v })}>
                <SelectTrigger data-testid="edit-lead-class"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CLASSIFICATIONS.map(c => (<SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Notas</Label>
              <Textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} data-testid="edit-lead-notes" />
            </div>
            <Button onClick={updateLead} className="w-full bg-[#7BA899] hover:bg-[#6A9688] text-white" data-testid="save-lead-btn">
              Guardar Cambios
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
