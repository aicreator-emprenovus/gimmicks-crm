import { useEffect, useState, useRef } from "react";
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
  User,
  Clock,
  Sparkles,
  Loader2,
  MessageSquare,
  Bot,
  Star,
  Trash2,
  Eraser,
  MoreVertical
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

export default function Inbox() {
  const { getAuthHeaders } = useAuth();
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
  const messagesEndRef = useRef(null);

  const fetchConversations = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/conversations`, {
        headers: getAuthHeaders()
      });
      setConversations(response.data);
    } catch (error) {
      toast.error("Error al cargar conversaciones");
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (convId) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/conversations/${convId}/messages`,
        { headers: getAuthHeaders() }
      );
      setMessages(response.data);
    } catch (error) {
      toast.error("Error al cargar mensajes");
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
      const lastUserMessage = [...messages]
        .reverse()
        .find((m) => m.sender === "user");
      
      if (!lastUserMessage) {
        toast.info("No hay mensajes del usuario para analizar");
        return;
      }

      const response = await axios.post(
        `${API_URL}/api/ai/analyze-message`,
        null,
        {
          headers: getAuthHeaders(),
          params: {
            message: lastUserMessage.content?.text || "",
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

  // Delete conversation
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

  // Clear messages
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

  // Toggle star
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
    if (selectedConv) {
      fetchMessages(selectedConv.id);
    }
  }, [selectedConv]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const filteredConversations = conversations.filter(
    (conv) => {
      const matchesSearch = conv.contact_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        conv.phone_number.includes(searchTerm);
      const matchesStarred = filterStarred ? conv.is_starred : true;
      return matchesSearch && matchesStarred;
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
    <div className="flex h-[calc(100vh-6rem)]" data-testid="inbox-page">
      {/* Conversations List */}
      <div className="w-80 border-r border-zinc-200 flex flex-col">
        <div className="p-4 border-b border-zinc-200">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-zinc-900 font-['Manrope']">
              Inbox
            </h2>
            <Button
              variant={filterStarred ? "default" : "ghost"}
              size="sm"
              onClick={() => setFilterStarred(!filterStarred)}
              className={filterStarred ? "bg-amber-500 hover:bg-amber-600" : "text-zinc-500"}
              data-testid="filter-starred-btn"
            >
              <Star className={`w-4 h-4 ${filterStarred ? "fill-white" : ""}`} />
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <Input
              placeholder="Buscar conversación..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 bg-zinc-50 text-zinc-900 border-zinc-200 placeholder:text-zinc-400"
              data-testid="search-conversations"
            />
          </div>
        </div>

        <ScrollArea className="flex-1">
          {loading ? (
            <div className="p-4 text-center">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-emerald-500" />
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="p-4 text-center text-zinc-400">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>{filterStarred ? "No hay conversaciones guardadas" : "No hay conversaciones"}</p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-100">
              {filteredConversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => {
                    setSelectedConv(conv);
                    setAiSuggestion(null);
                  }}
                  className={`w-full p-4 text-left hover:bg-zinc-50 transition-colors ${
                    selectedConv?.id === conv.id ? "bg-emerald-50" : ""
                  }`}
                  data-testid={`conversation-${conv.id}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="relative">
                      <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center text-white font-medium flex-shrink-0">
                        {conv.contact_name?.charAt(0)?.toUpperCase() ||
                          conv.phone_number.slice(-2)}
                      </div>
                      {conv.is_starred && (
                        <Star className="absolute -top-1 -right-1 w-4 h-4 text-amber-500 fill-amber-500" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-zinc-900 truncate">
                          {conv.contact_name || conv.phone_number}
                        </p>
                        <span className="text-xs text-zinc-400">
                          {formatDate(conv.last_message_time)}
                        </span>
                      </div>
                      <p className="text-sm text-zinc-500 truncate mt-0.5">
                        {conv.last_message || "Sin mensajes"}
                      </p>
                      {conv.unread_count > 0 && (
                        <Badge className="mt-1 bg-emerald-500 text-white text-xs">
                          {conv.unread_count} nuevos
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
      <div className="flex-1 flex flex-col">
        {selectedConv ? (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-zinc-200 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center text-white font-medium">
                  {selectedConv.contact_name?.charAt(0)?.toUpperCase() ||
                    selectedConv.phone_number.slice(-2)}
                </div>
                <div>
                  <h3 className="font-semibold text-zinc-900 flex items-center gap-2">
                    {selectedConv.contact_name || selectedConv.phone_number}
                    {selectedConv.is_starred && (
                      <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                    )}
                  </h3>
                  <p className="text-sm text-zinc-500 flex items-center gap-1">
                    <Phone className="w-3 h-3" />
                    {selectedConv.phone_number}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={analyzeWithAI}
                  disabled={analyzing}
                  className="gap-2"
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
                    <Button variant="ghost" size="sm" data-testid="chat-actions-btn">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem onClick={toggleStar} data-testid="toggle-star-btn">
                      <Star className={`w-4 h-4 mr-2 ${selectedConv.is_starred ? "fill-amber-500 text-amber-500" : ""}`} />
                      {selectedConv.is_starred ? "Quitar de guardados" : "Guardar conversación"}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem 
                      onClick={() => setShowClearDialog(true)}
                      className="text-orange-600"
                      data-testid="clear-messages-btn"
                    >
                      <Eraser className="w-4 h-4 mr-2" />
                      Limpiar mensajes
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={() => setShowDeleteDialog(true)}
                      className="text-red-600"
                      data-testid="delete-conversation-btn"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Eliminar conversación
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {/* AI Suggestion Panel */}
            {aiSuggestion && (
              <div className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 border-b border-zinc-200">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-purple-600" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-zinc-900 text-sm">
                      Análisis de IA
                    </p>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                      <div className="bg-white rounded-lg p-2 border border-zinc-200">
                        <span className="text-zinc-500">Intención:</span>
                        <Badge className="ml-1 capitalize">
                          {aiSuggestion.intent}
                        </Badge>
                      </div>
                      <div className="bg-white rounded-lg p-2 border border-zinc-200">
                        <span className="text-zinc-500">Clasificación:</span>
                        <Badge
                          className={`ml-1 capitalize ${
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
                      <div className="bg-white rounded-lg p-2 border border-zinc-200">
                        <span className="text-zinc-500">Productos:</span>
                        <span className="ml-1 text-zinc-900">
                          {aiSuggestion.suggested_products?.length || 0}
                        </span>
                      </div>
                    </div>
                    {aiSuggestion.suggested_response && (
                      <div className="mt-2 p-2 bg-white rounded-lg border border-zinc-200">
                        <p className="text-xs text-zinc-500 mb-1">
                          Respuesta sugerida:
                        </p>
                        <p className="text-sm text-zinc-700">
                          {aiSuggestion.suggested_response}
                        </p>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={useSuggestedResponse}
                          className="mt-2"
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
            <ScrollArea className="flex-1 p-4 chat-container">
              <div className="space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${
                      msg.sender === "business" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[70%] ${
                        msg.sender === "business"
                          ? "message-bubble-user"
                          : "message-bubble-business"
                      }`}
                    >
                      <p>{msg.content?.text || JSON.stringify(msg.content)}</p>
                      <p
                        className={`text-xs mt-1 ${
                          msg.sender === "business"
                            ? "text-emerald-100"
                            : "text-zinc-400"
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
              className="p-4 border-t border-zinc-200 flex gap-2"
            >
              <Input
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Escribe un mensaje..."
                className="flex-1 bg-zinc-50 text-zinc-900 border-zinc-300 placeholder:text-zinc-400"
                disabled={sending}
                data-testid="message-input"
              />
              <Button
                type="submit"
                disabled={sending || !newMessage.trim()}
                className="bg-emerald-500 hover:bg-emerald-600"
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
          <div className="flex-1 flex items-center justify-center text-zinc-400">
            <div className="text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">
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
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar conversación?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. Se eliminarán todos los mensajes de esta conversación permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
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
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Limpiar mensajes?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminarán todos los mensajes de esta conversación. La conversación se mantendrá pero quedará vacía.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
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
