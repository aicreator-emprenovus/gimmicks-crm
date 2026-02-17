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
  Pencil
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

  const resetForm = () => {
    setFormData({ ...EMPTY_FORM });
    setEditingRule(null);
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const RuleFormFields = () => (
    <div className="space-y-4 mt-4">
      <div className="space-y-2">
        <Label>Nombre de la regla *</Label>
        <Input
          placeholder="Ej: Bienvenida automática"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          data-testid="rule-name-input"
        />
      </div>
      <div className="space-y-2">
        <Label>Disparador (Trigger)</Label>
        <Select
          value={formData.trigger_type}
          onValueChange={(v) => setFormData({ ...formData, trigger_type: v })}
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
            formData.trigger_type === "ai_intent" ? "solicitud_catalogo" :
            "Valor"
          }
          value={formData.trigger_value}
          onChange={(e) => setFormData({ ...formData, trigger_value: e.target.value })}
          data-testid="rule-trigger-value"
        />
      </div>
      <div className="space-y-2">
        <Label>Acción</Label>
        <Select
          value={formData.action_type}
          onValueChange={(v) => setFormData({ ...formData, action_type: v })}
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
          onChange={(e) => setFormData({ ...formData, action_value: e.target.value })}
          rows={3}
          data-testid="rule-action-value"
        />
      </div>
      <div className="flex items-center gap-2">
        <Switch
          checked={formData.is_active}
          onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
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
                <Button className="bg-[#7BA899] hover:bg-[#6A9688] gap-2" data-testid="create-rule-btn">
                  <Plus size={18} />
                  Nueva Regla
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle className="font-['Manrope']">Crear Regla de Automatización</DialogTitle>
                </DialogHeader>
                <RuleFormFields />
                <Button
                  onClick={createRule}
                  className="w-full bg-[#7BA899] hover:bg-[#6A9688]"
                  disabled={!formData.name || !formData.action_value}
                  data-testid="submit-rule-btn"
                >
                  Crear Regla
                </Button>
              </DialogContent>
            </Dialog>
          </div>

          {/* Edit Dialog */}
          <Dialog open={!!editingRule} onOpenChange={(open) => { if (!open) resetForm(); }}>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle className="font-['Manrope']">Editar Regla</DialogTitle>
              </DialogHeader>
              <RuleFormFields />
              <Button
                onClick={updateRule}
                className="w-full bg-[#7BA899] hover:bg-[#6A9688]"
                disabled={!formData.name || !formData.action_value}
                data-testid="save-edit-btn"
              >
                Guardar Cambios
              </Button>
            </DialogContent>
          </Dialog>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-[#7BA899]" />
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
                    value={`${API_URL}/api/webhook/whatsapp`}
                    readOnly
                    className="bg-zinc-50 font-mono text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Verify Token</Label>
                  <Input
                    value="gimmicks-whatsapp-verify-token"
                    readOnly
                    className="bg-zinc-50 font-mono text-sm"
                  />
                </div>
              </div>
              
              <p className="text-sm text-zinc-500">
                Usa esta URL y token de verificación al configurar el webhook en Meta for Developers.
              </p>
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
                  <div className="w-2 h-2 bg-[#7BA899] rounded-full animate-pulse"></div>
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
