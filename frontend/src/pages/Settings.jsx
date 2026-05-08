import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  Settings as SettingsIcon,
  Bot,
  MessageSquare,
  Zap,
  Plus,
  Trash2,
  Loader2,
  Webhook,
  Key,
  AlertTriangle,
  CheckCircle2,
  Pencil,
  Download,
  Upload,
  XCircle
} from "lucide-react";
import { toast } from "sonner";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TRIGGER_TYPES = [
  { value: "keyword", label: "Palabra clave", description: "Cuando el mensaje contiene ciertas palabras" },
  { value: "new_lead", label: "Nuevo lead", description: "Cuando llega un nuevo contacto" },
  { value: "ai_intent", label: "Intención IA", description: "Cuando la IA detecta una intención específica" },
  { value: "funnel_change", label: "Cambio de etapa", description: "Cuando un lead cambia de etapa" },
  { value: "no_response", label: "Sin respuesta", description: "Cuando no hay respuesta en X horas" }
];

const ACTION_TYPES = [
  { value: "send_message", label: "Enviar mensaje", description: "Envía un mensaje automático" },
  { value: "ai_response", label: "Respuesta IA", description: "IA procesa y responde inteligentemente" },
  { value: "change_stage", label: "Cambiar etapa", description: "Mueve el lead a otra etapa" },
  { value: "assign_agent", label: "Asignar agente", description: "Asigna a un agente humano" }
];

const EMPTY_FORM = {
  name: "",
  trigger_type: "keyword",
  trigger_value: "",
  action_type: "send_message",
  action_value: "",
  is_active: true
};

export default function Settings() {
  const { getAuthHeaders, user } = useAuth();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [formData, setFormData] = useState({ ...EMPTY_FORM });
  const [waInfo, setWaInfo] = useState({ webhook_url: "", verify_token: "", phone_number_id: "" });
  const [waDiag, setWaDiag] = useState(null);
  const [waDiagLoading, setWaDiagLoading] = useState(false);

  const fetchWaDiag = async () => {
    setWaDiagLoading(true);
    try {
      const r = await axios.get(`${API_URL}/api/webhook/whatsapp/diagnostics`, { headers: getAuthHeaders() });
      setWaDiag(r.data);
    } catch (e) {
      setWaDiag({ error: e.response?.data?.detail || "No se pudo cargar el diagnóstico" });
    } finally {
      setWaDiagLoading(false);
    }
  };

  const fetchWaInfo = async () => {
    try {
      const r = await axios.get(`${API_URL}/api/webhook/whatsapp/info`, { headers: getAuthHeaders() });
      // Use the public origin the user sees rather than the backend host
      const url = r.data.webhook_url || `${window.location.origin}/api/webhook/whatsapp`;
      setWaInfo({
        webhook_url: url.replace(/^https?:\/\/[^/]+/, window.location.origin),
        verify_token: r.data.verify_token || "",
        phone_number_id: r.data.phone_number_id || "",
      });
    } catch (e) {
      // fallback if endpoint not yet deployed
      setWaInfo({
        webhook_url: `${window.location.origin}/api/webhook/whatsapp`,
        verify_token: "",
        phone_number_id: "",
      });
    }
  };
  useEffect(() => { fetchWaInfo(); fetchWaDiag(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchRules = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/automation-rules`, {
        headers: getAuthHeaders()
      });
      setRules(response.data);
    } catch (error) {
      toast.error("Error al cargar reglas");
    } finally {
      setLoading(false);
    }
  };

  const createRule = async () => {
    try {
      await axios.post(`${API_URL}/api/automation-rules`, formData, {
        headers: getAuthHeaders()
      });
      toast.success("Regla creada");
      setIsCreateOpen(false);
      resetForm();
      fetchRules();
    } catch (error) {
      toast.error("Error al crear regla");
    }
  };

  const updateRule = async () => {
    if (!editingRule) return;
    try {
      await axios.patch(
        `${API_URL}/api/automation-rules/${editingRule}`,
        formData,
        { headers: getAuthHeaders() }
      );
      toast.success("Regla actualizada");
      setEditingRule(null);
      resetForm();
      fetchRules();
    } catch (error) {
      toast.error("Error al actualizar regla");
    }
  };

  const openEditDialog = (rule) => {
    setFormData({
      name: rule.name,
      trigger_type: rule.trigger_type,
      trigger_value: rule.trigger_value || "",
      action_type: rule.action_type,
      action_value: rule.action_value,
      is_active: rule.is_active
    });
    setEditingRule(rule.id);
  };

  const toggleRule = async (ruleId, isActive) => {
    try {
      await axios.patch(
        `${API_URL}/api/automation-rules/${ruleId}`,
        null,
        {
          headers: getAuthHeaders(),
          params: { is_active: isActive }
        }
      );
      toast.success(isActive ? "Regla activada" : "Regla desactivada");
      fetchRules();
    } catch (error) {
      toast.error("Error al actualizar regla");
    }
  };

  const deleteRule = async (ruleId) => {
    if (!confirm("¿Eliminar esta regla?")) return;
    try {
      await axios.delete(`${API_URL}/api/automation-rules/${ruleId}`, {
        headers: getAuthHeaders()
      });
      toast.success("Regla eliminada");
      fetchRules();
    } catch (error) {
      toast.error("Error al eliminar regla");
    }
  };

  const exportRulesExcel = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/automation-rules/export-excel`, {
        headers: getAuthHeaders(),
        responseType: "blob"
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "reglas_automatizacion.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Excel descargado");
    } catch (error) {
      toast.error("Error al exportar");
    }
  };

  const importRulesExcel = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formPayload = new FormData();
    formPayload.append("file", file);
    try {
      const res = await axios.post(`${API_URL}/api/automation-rules/import-excel`, formPayload, {
        headers: { ...getAuthHeaders(), "Content-Type": "multipart/form-data" }
      });
      toast.success(res.data.message);
      fetchRules();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Error al importar");
    }
    e.target.value = "";
  };

  const deleteAllRules = async () => {
    if (!confirm(`¿Eliminar TODAS las ${rules.length} reglas? Esta acción no se puede deshacer. Se recomienda descargar el Excel primero.`)) return;
    try {
      const res = await axios.delete(`${API_URL}/api/automation-rules-bulk/delete-all`, {
        headers: getAuthHeaders()
      });
      toast.success(res.data.message);
      fetchRules();
    } catch (error) {
      toast.error("Error al eliminar reglas");
    }
  };

  const resetForm = () => {
    setFormData({ ...EMPTY_FORM });
    setEditingRule(null);
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const ruleFormFields = (
    <div className="space-y-4 mt-4">
      <div className="space-y-2">
        <Label>Nombre de la regla *</Label>
        <Input
          placeholder="Ej: Bienvenida automática"
          value={formData.name}
          onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
          data-testid="rule-name-input"
        />
      </div>
      <div className="space-y-2">
        <Label>Disparador (Trigger)</Label>
        <Select
          value={formData.trigger_type}
          onValueChange={(v) => setFormData(prev => ({ ...prev, trigger_type: v }))}
        >
          <SelectTrigger data-testid="rule-trigger-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TRIGGER_TYPES.map(t => (
              <SelectItem key={t.value} value={t.value}>
                <div>
                  <p>{t.label}</p>
                  <p className="text-xs text-zinc-500">{t.description}</p>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>
          {formData.trigger_type === "keyword" ? "Palabras clave (separadas por coma)" :
           formData.trigger_type === "no_response" ? "Horas de inactividad" :
           formData.trigger_type === "ai_intent" ? "Intención detectada" :
           "Valor del disparador"}
        </Label>
        <Input
          placeholder={
            formData.trigger_type === "keyword" ? "hola, precio, cotización" :
            formData.trigger_type === "no_response" ? "4" :
            formData.trigger_type === "ai_intent" ? "cotizacion_directa" :
            "Valor"
          }
          value={formData.trigger_value}
          onChange={(e) => setFormData(prev => ({ ...prev, trigger_value: e.target.value }))}
          data-testid="rule-trigger-value"
        />
      </div>
      <div className="space-y-2">
        <Label>Acción</Label>
        <Select
          value={formData.action_type}
          onValueChange={(v) => setFormData(prev => ({ ...prev, action_type: v }))}
        >
          <SelectTrigger data-testid="rule-action-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ACTION_TYPES.map(a => (
              <SelectItem key={a.value} value={a.value}>
                <div>
                  <p>{a.label}</p>
                  <p className="text-xs text-zinc-500">{a.description}</p>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>
          {formData.action_type === "send_message" ? "Mensaje a enviar" :
           formData.action_type === "change_stage" ? "Etapa destino (ej: perdido, cliente_potencial)" :
           formData.action_type === "assign_agent" ? "Descripción de la transferencia" :
           "Instrucciones para la IA"}
        </Label>
        <Textarea
          placeholder={
            formData.action_type === "send_message" ? "¡Hola! Gracias por contactarnos..." :
            formData.action_type === "change_stage" ? "perdido" :
            "Descripción de lo que hace esta regla"
          }
          value={formData.action_value}
          onChange={(e) => setFormData(prev => ({ ...prev, action_value: e.target.value }))}
          rows={3}
          data-testid="rule-action-value"
        />
      </div>
      <div className="flex items-center gap-2">
        <Switch
          checked={formData.is_active}
          onCheckedChange={(checked) => setFormData(prev => ({ ...prev, is_active: checked }))}
        />
        <Label>Regla activa</Label>
      </div>
    </div>
  );

  return (
    <div className="p-6 space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 font-['Manrope']">
          Configuración
        </h1>
        <p className="text-zinc-500 text-sm">
          Automatizaciones y configuración del sistema
        </p>
      </div>

      <Tabs defaultValue="automation" className="space-y-6">
        <TabsList className="bg-zinc-100">
          <TabsTrigger value="automation" className="gap-2" data-testid="tab-automation">
            <Zap className="w-4 h-4" />
            Automatización
          </TabsTrigger>
          <TabsTrigger value="whatsapp" className="gap-2" data-testid="tab-whatsapp">
            <MessageSquare className="w-4 h-4" />
            WhatsApp
          </TabsTrigger>
          <TabsTrigger value="ai" className="gap-2" data-testid="tab-ai">
            <Bot className="w-4 h-4" />
            IA
          </TabsTrigger>
        </TabsList>

        <TabsContent value="automation" className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-zinc-900 font-['Manrope']">
                Reglas de Automatización
              </h2>
              <p className="text-sm text-zinc-500">
                {rules.length} regla{rules.length !== 1 ? 's' : ''} configurada{rules.length !== 1 ? 's' : ''}
              </p>
            </div>
            <Dialog open={isCreateOpen} onOpenChange={(open) => { setIsCreateOpen(open); if (!open) resetForm(); }}>
              <DialogTrigger asChild>
                <Button className="bg-[#63AC9A] hover:bg-[#6A9688] gap-2" data-testid="create-rule-btn">
                  <Plus size={18} />
                  Nueva Regla
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle className="font-['Manrope']">Crear Regla de Automatización</DialogTitle>
                </DialogHeader>
                {ruleFormFields}
                <Button
                  onClick={createRule}
                  className="w-full bg-[#63AC9A] hover:bg-[#6A9688]"
                  disabled={!formData.name || !formData.action_value}
                  data-testid="submit-rule-btn"
                >
                  Crear Regla
                </Button>
              </DialogContent>
            </Dialog>
          </div>

          {/* Bulk actions bar */}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-zinc-700 border-zinc-300 hover:bg-zinc-50"
              onClick={exportRulesExcel}
              disabled={rules.length === 0}
              data-testid="export-rules-btn"
            >
              <Download size={15} />
              Descargar Excel
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-zinc-700 border-zinc-300 hover:bg-zinc-50 relative"
              onClick={() => document.getElementById('import-rules-file').click()}
              data-testid="import-rules-btn"
            >
              <Upload size={15} />
              Cargar Excel
            </Button>
            <input
              id="import-rules-file"
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={importRulesExcel}
            />
            {rules.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-red-600 border-red-200 hover:bg-red-50 ml-auto"
                onClick={deleteAllRules}
                data-testid="delete-all-rules-btn"
              >
                <XCircle size={15} />
                Borrar Todas
              </Button>
            )}
          </div>

          {/* Edit Dialog */}
          <Dialog open={!!editingRule} onOpenChange={(open) => { if (!open) resetForm(); }}>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle className="font-['Manrope']">Editar Regla</DialogTitle>
              </DialogHeader>
              {ruleFormFields}
              <Button
                onClick={updateRule}
                className="w-full bg-[#63AC9A] hover:bg-[#6A9688]"
                disabled={!formData.name || !formData.action_value}
                data-testid="save-edit-btn"
              >
                Guardar Cambios
              </Button>
            </DialogContent>
          </Dialog>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-[#63AC9A]" />
            </div>
          ) : rules.length === 0 ? (
            <Card className="border border-zinc-200">
              <CardContent className="p-12 text-center">
                <Zap className="w-16 h-16 mx-auto mb-4 text-zinc-300" />
                <p className="text-lg font-medium text-zinc-900">No hay reglas configuradas</p>
                <p className="text-sm text-zinc-500 mt-1">Crea reglas para automatizar respuestas</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {rules.map((rule) => {
                const triggerLabel = TRIGGER_TYPES.find(t => t.value === rule.trigger_type)?.label || rule.trigger_type;
                const actionLabel = ACTION_TYPES.find(a => a.value === rule.action_type)?.label || rule.action_type;
                return (
                  <Card
                    key={rule.id}
                    className={`border transition-colors ${rule.is_active ? 'border-emerald-200 bg-white' : 'border-zinc-200 bg-zinc-50/50'}`}
                    data-testid={`rule-card-${rule.id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-semibold text-zinc-900 text-sm">{rule.name}</h3>
                            <Badge variant={rule.is_active ? "default" : "secondary"} className="text-xs">
                              {rule.is_active ? "Activa" : "Inactiva"}
                            </Badge>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-2 text-xs">
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-md">
                              <Zap className="w-3 h-3" /> {triggerLabel}
                              {rule.trigger_value && <span className="text-blue-500">({rule.trigger_value})</span>}
                            </span>
                            <span className="text-zinc-300">→</span>
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-50 text-emerald-700 rounded-md">
                              {actionLabel}
                            </span>
                          </div>
                          {rule.action_value && (
                            <p className="mt-2 text-xs text-zinc-500 line-clamp-2">
                              {rule.action_value}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1 ml-3 flex-shrink-0">
                          <Switch
                            checked={rule.is_active}
                            onCheckedChange={(checked) => toggleRule(rule.id, checked)}
                            data-testid={`toggle-rule-${rule.id}`}
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-zinc-500 hover:text-zinc-700"
                            onClick={() => openEditDialog(rule)}
                            data-testid={`edit-rule-${rule.id}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-red-400 hover:text-red-600"
                            onClick={() => deleteRule(rule.id)}
                            data-testid={`delete-rule-${rule.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* WhatsApp Tab */}
        <TabsContent value="whatsapp" className="space-y-6">
          <Card className="border border-zinc-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 font-['Manrope']">
                <Webhook className="w-5 h-5" />
                Configuración de WhatsApp Business
              </CardTitle>
              <CardDescription>
                Conecta tu cuenta de WhatsApp Business API
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-800">Configuración pendiente</p>
                  <p className="text-sm text-yellow-700 mt-1">
                    Para conectar WhatsApp Business API necesitas:
                  </p>
                  <ul className="text-sm text-yellow-700 mt-2 list-disc list-inside">
                    <li>Una cuenta de Meta Business</li>
                    <li>Acceso a WhatsApp Business Cloud API</li>
                    <li>Phone Number ID y Access Token</li>
                  </ul>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Webhook URL</Label>
                  <Input
                    value={waInfo.webhook_url}
                    readOnly
                    className="bg-zinc-50 font-mono text-sm"
                    data-testid="wa-webhook-url"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Verify Token</Label>
                  <Input
                    value={waInfo.verify_token || "(no configurado en el servidor)"}
                    readOnly
                    className="bg-zinc-50 font-mono text-sm"
                    data-testid="wa-verify-token"
                  />
                </div>
              </div>
              {waInfo.phone_number_id && (
                <p className="text-xs text-zinc-500 mt-2 font-mono">
                  Phone Number ID actual: {waInfo.phone_number_id}
                </p>
              )}
              
              <p className="text-sm text-zinc-500">
                Usa esta URL y token de verificación al configurar el webhook en Meta for Developers.
              </p>
            </CardContent>
          </Card>

          {/* Diagnóstico en tiempo real */}
          <Card className="border border-zinc-200" data-testid="wa-diagnostics-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 font-['Manrope']">
                <AlertTriangle className="w-5 h-5" />
                Diagnóstico de WhatsApp
              </CardTitle>
              <CardDescription>
                Estado actual de la conexión con WhatsApp Business API. Si ves un ID retirado, los mensajes y adjuntos no se enviarán al cliente.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {waDiagLoading && (
                <p className="text-sm text-zinc-500">Cargando diagnóstico...</p>
              )}
              {waDiag && waDiag.error && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700" data-testid="wa-diag-error">
                  {waDiag.error}
                </div>
              )}
              {waDiag && !waDiag.error && (
                <>
                  {(() => {
                    const pid = String(waDiag.whatsapp_phone_id || "");
                    const isRetired = pid.startsWith("RETIRED");
                    const isMissing = pid === "MISSING";
                    const ok = !isRetired && !isMissing;
                    return (
                      <div
                        className={`p-3 rounded-lg border text-sm flex items-start gap-2 ${
                          ok
                            ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                            : "bg-red-50 border-red-200 text-red-800"
                        }`}
                        data-testid="wa-diag-phoneid-status"
                      >
                        {ok ? (
                          <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        )}
                        <div>
                          <p className="font-semibold">
                            Phone Number ID: <span className="font-mono">{pid || "(vacío)"}</span>
                          </p>
                          {!ok && (
                            <p className="mt-1">
                              {isRetired
                                ? "Este ID está retirado. Los envíos a clientes están bloqueados. Actualiza la variable de entorno WHATSAPP_PHONE_NUMBER_ID en producción al ID actual del número +593 96 356 0326 (965777766626628) y rediplega."
                                : "No hay Phone Number ID configurado. Define la variable de entorno WHATSAPP_PHONE_NUMBER_ID y rediplega."}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })()}
                  <div className="grid grid-cols-2 gap-2 text-xs text-zinc-600 font-mono">
                    <div>Token WhatsApp: <span className={waDiag.whatsapp_token === "configured" ? "text-emerald-700" : "text-red-700"}>{waDiag.whatsapp_token}</span></div>
                    <div>Emergent LLM: <span className={waDiag.emergent_llm_key === "configured" ? "text-emerald-700" : "text-red-700"}>{waDiag.emergent_llm_key}</span></div>
                    <div>LLM test: <span className="text-zinc-700">{waDiag.llm_test}</span></div>
                    <div>Bot import: <span className="text-zinc-700">{waDiag.bot_import}</span></div>
                    <div>Reglas activas: <span className="text-zinc-700">{waDiag.active_rules}</span></div>
                    <div>Conversaciones: <span className="text-zinc-700">{waDiag.db_conversations}</span></div>
                    <div>Productos: <span className="text-zinc-700">{waDiag.db_products}</span></div>
                    <div>Imágenes producto: <span className="text-zinc-700">{waDiag.db_product_images}</span></div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={fetchWaDiag}
                    disabled={waDiagLoading}
                    data-testid="wa-diag-refresh-btn"
                  >
                    Refrescar diagnóstico
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI Tab */}
        <TabsContent value="ai" className="space-y-6">
          <Card className="border border-zinc-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 font-['Manrope']">
                <Bot className="w-5 h-5" />
                Configuración de IA
              </CardTitle>
              <CardDescription>
                Análisis automático de mensajes con GPT-5.2
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-[#63AC9A] rounded-full animate-pulse"></div>
                  <span className="font-medium text-emerald-800">IA Activa</span>
                </div>
                <p className="text-sm text-emerald-700 mt-2">
                  La integración con GPT-5.2 está configurada usando Emergent LLM Key.
                </p>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
                  <div>
                    <p className="font-medium text-zinc-900">Análisis de intención</p>
                    <p className="text-sm text-zinc-500">
                      Clasifica automáticamente la intención del mensaje
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                
                <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
                  <div>
                    <p className="font-medium text-zinc-900">Clasificación de leads</p>
                    <p className="text-sm text-zinc-500">
                      Determina si el lead es frío, tibio o caliente
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                
                <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
                  <div>
                    <p className="font-medium text-zinc-900">Recomendación de productos</p>
                    <p className="text-sm text-zinc-500">
                      Sugiere productos basados en el mensaje del cliente
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                
                <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
                  <div>
                    <p className="font-medium text-zinc-900">Respuestas sugeridas</p>
                    <p className="text-sm text-zinc-500">
                      Genera respuestas automáticas para el agente
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
