import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  Send,
  Phone,
  Sparkles,
  Loader2,
  MessageSquare,
  Bot,
  Star,
  Trash2,
  Eraser,
  MoreVertical,
  Filter,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  X,
  RefreshCw
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const STAGE_CONFIG = {
  lead: { label: "Lead", color: "bg-blue-100 text-blue-700" },
  cliente_potencial: { label: "Potencial", color: "bg-yellow-100 text-yellow-700" },
  cotizacion_generada: { label: "Cotizado", color: "bg-purple-100 text-purple-700" },
  pedido: { label: "Pedido", color: "bg-emerald-100 text-emerald-700" },
  produccion: { label: "Producción", color: "bg-orange-100 text-orange-700" },
  entregado: { label: "Entregado", color: "bg-teal-100 text-teal-700" },
  perdido: { label: "Perdido", color: "bg-red-100 text-red-700" },
};

export default function Inbox() {
  const { getAuthHeaders, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [conversations, setConversations] = useState([]);
  const [selectedConv, setSelectedConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showClearDialog, setShowClearDialog] = useState(false);
  const [filterStarred, setFilterStarred] = useState(false);
  const [filterStage, setFilterStage] = useState(null);
  const [syncIndicator, setSyncIndicator] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const messagesEndRef = useRef(null);
  const prevMessageCountRef = useRef(0);

  const triggerSync = async () => {
    setSyncing(true);
    try {
      await axios.post(`${API_URL}/api/sync/production`, {}, { headers: getAuthHeaders() });
      await fetchConversations();
      toast.success("Datos sincronizados con producción");
    } catch {
      toast.error("Error al sincronizar");
    } finally {
      setSyncing(false);
    }
  };

  const fetchConversations = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/conversations`, {
        headers: getAuthHeaders()
      });
      setConversations(response.data);
    } catch (error) {
      if (!conversations.length) toast.error("Error al cargar conversaciones");
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (convId, isPolling = false) => {
    try {
      if (isPolling) setSyncIndicator(true);
      const response = await axios.get(
        `${API_URL}/api/conversations/${convId}/messages`,
        { headers: getAuthHeaders() }
      );
      const newMsgs = response.data;
      setMessages(prev => {
        if (newMsgs.length !== prev.length) {
          prevMessageCountRef.current = prev.length;
          return newMsgs;
        }
        return prev;
      });
    } catch (error) {
      if (!isPolling) toast.error("Error al cargar mensajes");
    } finally {
      if (isPolling) setTimeout(() => setSyncIndicator(false), 500);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConv) return;

    setSending(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/conversations/${selectedConv.id}/messages`,
        {
          conversation_id: selectedConv.id,
          content: newMessage,
          message_type: "text"
        },
        { headers: getAuthHeaders() }
      );
      setMessages([...messages, response.data]);
      setNewMessage("");
      setAiSuggestion(null);
      fetchConversations();
    } catch (error) {
      console.error("Send message error:", error.response?.data || error);
      toast.error(error.response?.data?.detail || "Error al enviar mensaje");
    } finally {
      setSending(false);
    }
  };

  const analyzeWithAI = async () => {
    if (messages.length === 0) return;

    setAnalyzing(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/ai/analyze-message`,
        null,
        {
          headers: getAuthHeaders(),
          params: {
            message: "",
            conversation_id: selectedConv?.id
          }
        }
      );

      setAiSuggestion(response.data);
      toast.success("Análisis completado");
    } catch (error) {
      toast.error("Error al analizar con IA");
    } finally {
      setAnalyzing(false);
    }
  };

  const useSuggestedResponse = () => {
    if (aiSuggestion?.suggested_response) {
      setNewMessage(aiSuggestion.suggested_response);
    }
  };

  const deleteConversation = async () => {
    if (!selectedConv) return;
    try {
      await axios.delete(
        `${API_URL}/api/conversations/${selectedConv.id}`,
        { headers: getAuthHeaders() }
      );
      toast.success("Conversación eliminada");
      setSelectedConv(null);
      setMessages([]);
      fetchConversations();
    } catch (error) {
      toast.error("Error al eliminar conversación");
    }
    setShowDeleteDialog(false);
  };

  const clearMessages = async () => {
    if (!selectedConv) return;
    try {
      await axios.delete(
        `${API_URL}/api/conversations/${selectedConv.id}/messages`,
        { headers: getAuthHeaders() }
      );
      toast.success("Mensajes eliminados");
      setMessages([]);
      fetchConversations();
    } catch (error) {
      toast.error("Error al limpiar mensajes");
    }
    setShowClearDialog(false);
  };

  const toggleStar = async () => {
    if (!selectedConv) return;
    try {
      const response = await axios.patch(
        `${API_URL}/api/conversations/${selectedConv.id}/star`,
        {},
        { headers: getAuthHeaders() }
      );
      toast.success(response.data.message);
      setSelectedConv({ ...selectedConv, is_starred: response.data.is_starred });
      fetchConversations();
    } catch (error) {
      toast.error("Error al guardar conversación");
    }
  };

  useEffect(() => {
    fetchConversations();
    const interval = setInterval(fetchConversations, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const phone = searchParams.get("phone");
    if (phone && conversations.length > 0 && !selectedConv) {
      const match = conversations.find(c => c.phone_number === phone);
      if (match) {
        setSelectedConv(match);
        setSearchParams({}, { replace: true });
      }
    }
  }, [conversations, searchParams]);

  useEffect(() => {
    if (selectedConv) {
      fetchMessages(selectedConv.id);
      const msgInterval = setInterval(() => fetchMessages(selectedConv.id, true), 5000);
      return () => clearInterval(msgInterval);
    }
  }, [selectedConv]);

  useEffect(() => {
    if (messages.length > prevMessageCountRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    prevMessageCountRef.current = messages.length;
  }, [messages]);

  const filteredConversations = conversations.filter(
    (conv) => {
      const matchesSearch = conv.contact_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        conv.phone_number.includes(searchTerm);
      const matchesStarred = filterStarred ? conv.is_starred : true;
      const matchesStage = filterStage ? conv.funnel_stage === filterStage : true;
      return matchesSearch && matchesStarred && matchesStage;
    }
  );

  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    try {
      return format(new Date(dateStr), "HH:mm", { locale: es });
    } catch {
      return "";
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      return format(new Date(dateStr), "dd MMM", { locale: es });
    } catch {
      return "";
    }
  };

  return (
    <div className="flex h-screen" data-testid="inbox-page">
      {/* Conversations List */}
      <div className="w-80 border-r border-gray-200 flex flex-col bg-white">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800 font-['Manrope']">
              Inbox
            </h2>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={triggerSync}
                disabled={syncing}
                className="text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                data-testid="sync-production-btn"
                title="Sincronizar con producción"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
              </Button>
              <Button
                variant={filterStarred ? "default" : "ghost"}
                size="sm"
                onClick={() => setFilterStarred(!filterStarred)}
                className={filterStarred ? "bg-amber-500 hover:bg-amber-600" : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"}
                data-testid="filter-starred-btn"
              >
                <Star className={`w-4 h-4 ${filterStarred ? "fill-white" : ""}`} />
              </Button>
            </div>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Buscar conversación..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 bg-gray-50 text-gray-800 border-gray-200 placeholder:text-gray-400"
              data-testid="search-conversations"
            />
          </div>
          <div className="flex flex-wrap gap-1 mt-2" data-testid="stage-filters">
            <button
              onClick={() => setFilterStage(null)}
              className={`px-2 py-0.5 text-xs rounded-full transition-colors ${!filterStage ? "bg-[#63AC9A] text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
              data-testid="filter-all"
            >
              Todos
            </button>
            {Object.entries(STAGE_CONFIG).map(([key, cfg]) => (
              <button
                key={key}
                onClick={() => setFilterStage(filterStage === key ? null : key)}
                className={`px-2 py-0.5 text-xs rounded-full transition-colors ${filterStage === key ? "bg-[#63AC9A] text-white" : `${cfg.color} hover:opacity-80`}`}
                data-testid={`filter-${key}`}
              >
                {cfg.label}
              </button>
            ))}
          </div>
        </div>

        <ScrollArea className="flex-1">
          {loading ? (
            <div className="p-4 text-center">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#63AC9A]" />
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="p-4 text-center text-gray-400">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p>{filterStarred ? "No hay conversaciones guardadas" : "No hay conversaciones"}</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filteredConversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => {
                    setSelectedConv(conv);
                    setAiSuggestion(null);
                  }}
                  className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                    selectedConv?.id === conv.id ? "bg-[#63AC9A]/10 border-l-2 border-[#63AC9A]" : ""
                  }`}
                  data-testid={`conversation-${conv.id}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="relative">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#63AC9A] to-[#4F9A87] flex items-center justify-center text-white font-medium flex-shrink-0">
                        {conv.contact_name?.charAt(0)?.toUpperCase() ||
                          conv.phone_number.slice(-2)}
                      </div>
                      {conv.is_starred && (
                        <Star className="absolute -top-1 -right-1 w-4 h-4 text-amber-500 fill-amber-500" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-gray-800 truncate">
                          {conv.contact_name || conv.phone_number}
                        </p>
                        <span className="text-xs text-gray-400">
                          {formatDate(conv.last_message_time)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 mt-0.5 break-words">
                        {conv.last_message || "Sin mensajes"}
                      </p>
                      {conv.unread_count > 0 && (
                        <Badge className="mt-1 bg-[#63AC9A] text-white text-xs">
                          {conv.unread_count} nuevos
                        </Badge>
                      )}
                      {conv.funnel_stage && STAGE_CONFIG[conv.funnel_stage] && (
                        <Badge className={`mt-1 ml-1 text-xs ${STAGE_CONFIG[conv.funnel_stage].color}`} data-testid={`stage-badge-${conv.id}`}>
                          {STAGE_CONFIG[conv.funnel_stage].label}
                        </Badge>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-[#f0f2f5]">
        {selectedConv ? (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-white">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#63AC9A] to-[#4F9A87] flex items-center justify-center text-white font-medium">
                  {selectedConv.contact_name?.charAt(0)?.toUpperCase() ||
                    selectedConv.phone_number.slice(-2)}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    {selectedConv.contact_name || selectedConv.phone_number}
                    {selectedConv.is_starred && (
                      <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                    )}
                  </h3>
                  <p className="text-sm text-gray-500 flex items-center gap-1">
                    <Phone className="w-3 h-3" />
                    {selectedConv.phone_number}
                    {syncIndicator && (
                      <span className="ml-2 flex items-center gap-1 text-xs text-[#63AC9A]" data-testid="sync-indicator">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Sincronizando
                      </span>
                    )}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={analyzeWithAI}
                  disabled={analyzing}
                  className="gap-2 bg-[#63AC9A] hover:bg-[#6A9688] text-white border-[#63AC9A]"
                  data-testid="analyze-ai-btn"
                >
                  {analyzing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  Analizar con IA
                </Button>
                
                {/* Actions Menu */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="border-gray-300 hover:bg-gray-100" data-testid="chat-actions-btn">
                      <MoreVertical className="w-4 h-4 text-gray-600" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48 bg-white border border-gray-200 shadow-lg">
                    <DropdownMenuItem onClick={toggleStar} className="cursor-pointer hover:bg-gray-50" data-testid="toggle-star-btn">
                      <Star className={`w-4 h-4 mr-2 ${selectedConv.is_starred ? "fill-amber-500 text-amber-500" : "text-gray-500"}`} />
                      <span className="text-gray-700">{selectedConv.is_starred ? "Quitar de guardados" : "Guardar conversación"}</span>
                    </DropdownMenuItem>
                    {user?.role === "admin" && (
                      <>
                        <DropdownMenuSeparator className="bg-gray-100" />
                        <DropdownMenuItem 
                          onClick={() => setShowClearDialog(true)}
                          className="cursor-pointer hover:bg-orange-50"
                          data-testid="clear-messages-btn"
                        >
                          <Eraser className="w-4 h-4 mr-2 text-orange-600" />
                          <span className="text-orange-600 font-medium">Limpiar mensajes</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          onClick={() => setShowDeleteDialog(true)}
                          className="cursor-pointer hover:bg-red-50"
                          data-testid="delete-conversation-btn"
                        >
                          <Trash2 className="w-4 h-4 mr-2 text-red-600" />
                          <span className="text-red-600 font-medium">Eliminar conversación</span>
                        </DropdownMenuItem>
                      </>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {/* AI Analysis Panel */}
            {aiSuggestion && (
              <div className="p-4 bg-[#63AC9A]/10 border-b border-[#63AC9A]/20">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[#63AC9A]/20 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-[#4F9A87]" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-gray-800 text-sm">
                        Análisis de conversación
                      </p>
                      <button
                        onClick={() => setAiSuggestion(null)}
                        className="p-1 rounded-md hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
                        data-testid="close-ai-panel"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                      <div className="bg-white rounded-lg p-2 border border-gray-200">
                        <span className="text-gray-500 block">Intención</span>
                        <Badge className="mt-0.5 capitalize bg-[#63AC9A]/15 text-[#4F9A87]">
                          {aiSuggestion.intent}
                        </Badge>
                      </div>
                      <div className="bg-white rounded-lg p-2 border border-gray-200">
                        <span className="text-gray-500 block">Clasificación</span>
                        <Badge
                          className={`mt-0.5 capitalize ${
                            aiSuggestion.lead_classification === "caliente"
                              ? "bg-red-100 text-red-700"
                              : aiSuggestion.lead_classification === "tibio"
                              ? "bg-orange-100 text-orange-700"
                              : "bg-cyan-100 text-cyan-700"
                          }`}
                        >
                          {aiSuggestion.lead_classification}
                        </Badge>
                      </div>
                      <div className="bg-white rounded-lg p-2 border border-gray-200">
                        <span className="text-gray-500 block">Cotización</span>
                        <Badge className={`mt-0.5 ${
                          aiSuggestion.quote_status === "ya_cotizado" ? "bg-emerald-100 text-emerald-700" :
                          aiSuggestion.quote_status === "listo_para_cotizar" ? "bg-amber-100 text-amber-700" :
                          aiSuggestion.quote_status === "datos_parciales" ? "bg-blue-100 text-blue-700" :
                          "bg-gray-100 text-gray-600"
                        }`}>
                          {aiSuggestion.quote_status === "ya_cotizado" ? "Ya cotizado" :
                           aiSuggestion.quote_status === "listo_para_cotizar" ? "Listo para cotizar" :
                           aiSuggestion.quote_status === "datos_parciales" ? "Datos parciales" :
                           "Sin datos"}
                        </Badge>
                      </div>
                    </div>
                    {/* Next action */}
                    {aiSuggestion.next_action && (
                      <div className="mt-2 p-2 bg-amber-50 rounded-lg border border-amber-200 flex items-start gap-2">
                        <ArrowRight className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-xs font-medium text-amber-800">Acción recomendada</p>
                          <p className="text-xs text-amber-700 mt-0.5">{aiSuggestion.next_action}</p>
                        </div>
                      </div>
                    )}
                    {/* Missing data */}
                    {aiSuggestion.missing_data?.length > 0 && (
                      <div className="mt-2 p-2 bg-blue-50 rounded-lg border border-blue-200 flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-xs font-medium text-blue-800">Datos faltantes</p>
                          <p className="text-xs text-blue-700 mt-0.5">{aiSuggestion.missing_data.join(", ")}</p>
                        </div>
                      </div>
                    )}
                    {/* Analysis notes */}
                    {aiSuggestion.analysis_notes && (
                      <p className="mt-2 text-xs text-gray-600 italic">{aiSuggestion.analysis_notes}</p>
                    )}
                    {aiSuggestion.suggested_response && (
                      <div className="mt-2 p-2 bg-white rounded-lg border border-gray-200">
                        <p className="text-xs text-gray-500 mb-1">
                          Respuesta sugerida:
                        </p>
                        <p className="text-sm text-gray-800">
                          {aiSuggestion.suggested_response}
                        </p>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={useSuggestedResponse}
                          className="mt-2 border-[#63AC9A] text-[#4F9A87] hover:bg-[#63AC9A]/10"
                          data-testid="use-suggestion-btn"
                        >
                          Usar esta respuesta
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Messages */}
            <ScrollArea className="flex-1 p-4 chat-container-light">
              <div className="space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${
                      msg.sender === "business" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[70%] break-words overflow-hidden ${
                        msg.sender === "business"
                          ? "msg-bubble-sent"
                          : "msg-bubble-received"
                      }`}
                      style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}
                    >
                      <p className="whitespace-pre-wrap">{msg.content?.text || JSON.stringify(msg.content)}</p>
                      <p
                        className={`text-xs mt-1 ${
                          msg.sender === "business"
                            ? "text-white/70"
                            : "text-gray-400"
                        }`}
                      >
                        {formatTime(msg.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Message Input */}
            <form
              onSubmit={sendMessage}
              className="p-4 border-t border-gray-200 flex gap-2 bg-white"
            >
              <Input
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Escribe un mensaje..."
                className="flex-1 bg-gray-50 text-gray-800 border-gray-200 placeholder:text-gray-400"
                disabled={sending}
                data-testid="message-input"
              />
              <Button
                type="submit"
                disabled={sending || !newMessage.trim()}
                className="bg-[#63AC9A] hover:bg-[#6A9688] text-white"
                data-testid="send-message-btn"
              >
                {sending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium text-gray-600">
                Selecciona una conversación
              </p>
              <p className="text-sm">
                para ver los mensajes
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white border-gray-200">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-gray-800">¿Eliminar conversación?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-500">
              Esta acción no se puede deshacer. Se eliminarán todos los mensajes de esta conversación permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200">Cancelar</AlertDialogCancel>
            <AlertDialogAction 
              onClick={deleteConversation}
              className="bg-red-600 hover:bg-red-700"
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Clear Messages Confirmation Dialog */}
      <AlertDialog open={showClearDialog} onOpenChange={setShowClearDialog}>
        <AlertDialogContent className="bg-white border-gray-200">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-gray-800">¿Limpiar mensajes?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-500">
              Se eliminarán todos los mensajes de esta conversación. La conversación se mantendrá pero quedará vacía.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200">Cancelar</AlertDialogCancel>
            <AlertDialogAction 
              onClick={clearMessages}
              className="bg-orange-600 hover:bg-orange-700"
            >
              Limpiar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
