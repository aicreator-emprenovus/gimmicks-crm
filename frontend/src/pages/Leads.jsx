import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  User,
  Phone,
  Calendar,
  MessageSquare,
  Edit,
  Trash2,
  Loader2,
  Filter
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const FUNNEL_STAGES = [
  { value: "lead", label: "Lead", color: "bg-blue-100 text-blue-700 border-blue-200" },
  { value: "pedido", label: "Pedido", color: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  { value: "produccion", label: "Producción", color: "bg-purple-100 text-purple-700 border-purple-200" },
  { value: "entregado", label: "Entregado", color: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  { value: "perdido", label: "Perdido", color: "bg-red-100 text-red-700 border-red-200" },
  { value: "cierre", label: "Cierre", color: "bg-green-100 text-green-700 border-green-200" }
];

const CLASSIFICATIONS = [
  { value: "frio", label: "Frío", color: "bg-cyan-100 text-cyan-700" },
  { value: "tibio", label: "Tibio", color: "bg-orange-100 text-orange-700" },
  { value: "caliente", label: "Caliente", color: "bg-red-100 text-red-700" }
];

const SOURCES = [
  { value: "whatsapp", label: "WhatsApp" },
  { value: "meta_ads", label: "Meta Ads" },
  { value: "web", label: "Web" },
  { value: "organico", label: "Orgánico" }
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
    if (!confirm("¿Eliminar este lead?")) return;
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
    setFormData({
      phone_number: "",
      name: "",
      source: "whatsapp",
      notes: ""
    });
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

  const getStageColor = (stage) => {
    return FUNNEL_STAGES.find(s => s.value === stage)?.color || "";
  };

  const getClassificationColor = (classification) => {
    return CLASSIFICATIONS.find(c => c.value === classification)?.color || "";
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return format(new Date(dateStr), "dd/MM/yy HH:mm", { locale: es });
    } catch {
      return "-";
    }
  };

  // Group leads by stage for Kanban view
  const leadsByStage = FUNNEL_STAGES.reduce((acc, stage) => {
    acc[stage.value] = leads.filter(l => l.funnel_stage === stage.value);
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-6" data-testid="leads-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 font-['Manrope']">
            Gestión de Leads
          </h1>
          <p className="text-zinc-500 text-sm">
            Funnel de ventas conversacional
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button
              className="bg-[#7BA899] hover:bg-[#6A9688] gap-2 text-white"
              data-testid="create-lead-btn"
            >
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
                <Label>Teléfono *</Label>
                <Input
                  placeholder="+593999999999"
                  value={formData.phone_number}
                  onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  data-testid="lead-phone-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Nombre</Label>
                <Input
                  placeholder="Nombre del contacto"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  data-testid="lead-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Fuente</Label>
                <Select
                  value={formData.source}
                  onValueChange={(v) => setFormData({ ...formData, source: v })}
                >
                  <SelectTrigger data-testid="lead-source-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SOURCES.map(s => (
                      <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Notas</Label>
                <Textarea
                  placeholder="Notas adicionales..."
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  data-testid="lead-notes-input"
                />
              </div>
              <Button
                onClick={createLead}
                className="w-full bg-[#7BA899] hover:bg-[#6A9688] text-white"
                data-testid="submit-lead-btn"
              >
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
          <Input
            placeholder="Buscar por nombre o teléfono..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
            data-testid="search-leads-input"
          />
        </div>
        <Select value={filterStage} onValueChange={setFilterStage}>
          <SelectTrigger className="w-[160px]" data-testid="filter-stage-select">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Etapa" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {FUNNEL_STAGES.map(s => (
              <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={filterClassification} onValueChange={setFilterClassification}>
          <SelectTrigger className="w-[160px]" data-testid="filter-class-select">
            <SelectValue placeholder="Clasificación" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {CLASSIFICATIONS.map(c => (
              <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Kanban Board */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
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
                  {leadsByStage[stage.value]?.map(lead => (
                    <Card
                      key={lead.id}
                      className="border border-zinc-200 hover:shadow-md transition-shadow cursor-pointer"
                      data-testid={`lead-card-${lead.id}`}
                    >
                      <CardContent className="p-3 space-y-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-full bg-[#7BA899] flex items-center justify-center text-white text-sm font-medium">
                              {lead.name?.charAt(0)?.toUpperCase() || "?"}
                            </div>
                            <div>
                              <p className="font-medium text-zinc-900 text-sm truncate max-w-[100px]">
                                {lead.name || "Sin nombre"}
                              </p>
                              <p className="text-xs text-zinc-500">{lead.phone_number}</p>
                            </div>
                          </div>
                          <Badge className={`${getClassificationColor(lead.classification)} text-xs`}>
                            {lead.classification}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                          <Calendar className="w-3 h-3" />
                          {formatDate(lead.created_at)}
                        </div>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0"
                            onClick={() => openEditDialog(lead)}
                            data-testid={`edit-lead-${lead.id}`}
                          >
                            <Edit className="w-3 h-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-red-500 hover:text-red-600"
                            onClick={() => deleteLead(lead.id)}
                            data-testid={`delete-lead-${lead.id}`}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                          <Select
                            value={lead.funnel_stage}
                            onValueChange={(v) => updateLeadStage(lead.id, v)}
                          >
                            <SelectTrigger className="h-7 text-xs flex-1">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {FUNNEL_STAGES.map(s => (
                                <SelectItem key={s.value} value={s.value} className="text-xs">
                                  {s.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                  {leadsByStage[stage.value]?.length === 0 && (
                    <div className="text-center py-4 text-zinc-400 text-sm">
                      Sin leads
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>
          ))}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingLead} onOpenChange={(open) => !open && setEditingLead(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Manrope']">Editar Lead</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Teléfono</Label>
              <Input
                value={formData.phone_number}
                disabled
                className="bg-zinc-50"
              />
            </div>
            <div className="space-y-2">
              <Label>Nombre</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                data-testid="edit-lead-name"
              />
            </div>
            <div className="space-y-2">
              <Label>Etapa del Funnel</Label>
              <Select
                value={formData.funnel_stage}
                onValueChange={(v) => setFormData({ ...formData, funnel_stage: v })}
              >
                <SelectTrigger data-testid="edit-lead-stage">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FUNNEL_STAGES.map(s => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Clasificación</Label>
              <Select
                value={formData.classification}
                onValueChange={(v) => setFormData({ ...formData, classification: v })}
              >
                <SelectTrigger data-testid="edit-lead-class">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CLASSIFICATIONS.map(c => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Notas</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                data-testid="edit-lead-notes"
              />
            </div>
            <Button
              onClick={updateLead}
              className="w-full bg-emerald-500 hover:bg-emerald-600"
              data-testid="save-lead-btn"
            >
              Guardar Cambios
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
