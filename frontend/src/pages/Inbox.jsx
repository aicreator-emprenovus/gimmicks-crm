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
    <div className="flex h-screen bg-[#1a1a1d]" data-testid="inbox-page">
      {/* Conversations List */}
      <div className="w-80 border-r border-[#2d2d30] flex flex-col bg-[#1a1a1d]">
        <div className="p-4 border-b border-[#2d2d30]">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-white font-['Manrope']">
              Inbox
            </h2>
            <Button
              variant={filterStarred ? "default" : "ghost"}
              size="sm"
              onClick={() => setFilterStarred(!filterStarred)}
              className={filterStarred ? "bg-amber-500 hover:bg-amber-600" : "text-[#8a8a8a] hover:text-white hover:bg-[#2d2d30]"}
              data-testid="filter-starred-btn"
            >
              <Star className={`w-4 h-4 ${filterStarred ? "fill-white" : ""}`} />
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6b6b6b]" />
            <Input
              placeholder="Buscar conversación..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 bg-[#2d2d30] text-white border-[#3d3d40] placeholder:text-[#6b6b6b]"
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
            <div className="p-4 text-center text-[#6b6b6b]">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>{filterStarred ? "No hay conversaciones guardadas" : "No hay conversaciones"}</p>
            </div>
          ) : (
            <div className="divide-y divide-[#2d2d30]">
              {filteredConversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => {
                    setSelectedConv(conv);
                    setAiSuggestion(null);
                  }}
                  className={`w-full p-4 text-left hover:bg-[#2d2d30] transition-colors ${
                    selectedConv?.id === conv.id ? "bg-[#2d2d30] border-l-2 border-emerald-500" : ""
                  }`}
                  data-testid={`conversation-${conv.id}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="relative">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-white font-medium flex-shrink-0">
                        {conv.contact_name?.charAt(0)?.toUpperCase() ||
                          conv.phone_number.slice(-2)}
                      </div>
                      {conv.is_starred && (
                        <Star className="absolute -top-1 -right-1 w-4 h-4 text-amber-500 fill-amber-500" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-white truncate">
                          {conv.contact_name || conv.phone_number}
                        </p>
                        <span className="text-xs text-[#6b6b6b]">
                          {formatDate(conv.last_message_time)}
                        </span>
                      </div>
                      <p className="text-sm text-[#8a8a8a] truncate mt-0.5">
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
      <div className="flex-1 flex flex-col bg-[#232326]">
        {selectedConv ? (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-[#2d2d30] flex items-center justify-between bg-[#1a1a1d]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-white font-medium">
                  {selectedConv.contact_name?.charAt(0)?.toUpperCase() ||
                    selectedConv.phone_number.slice(-2)}
                </div>
                <div>
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    {selectedConv.contact_name || selectedConv.phone_number}
                    {selectedConv.is_starred && (
                      <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                    )}
                  </h3>
                  <p className="text-sm text-[#8a8a8a] flex items-center gap-1">
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
                  className="gap-2 bg-purple-500 hover:bg-purple-600 text-white"
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
                    <Button variant="outline" size="sm" className="border-zinc-300 hover:bg-zinc-100" data-testid="chat-actions-btn">
                      <MoreVertical className="w-4 h-4 text-zinc-700" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48 bg-white border border-zinc-200 shadow-lg">
                    <DropdownMenuItem onClick={toggleStar} className="cursor-pointer hover:bg-zinc-100" data-testid="toggle-star-btn">
                      <Star className={`w-4 h-4 mr-2 ${selectedConv.is_starred ? "fill-amber-500 text-amber-500" : "text-zinc-600"}`} />
                      <span className="text-zinc-800">{selectedConv.is_starred ? "Quitar de guardados" : "Guardar conversación"}</span>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator className="bg-zinc-200" />
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
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {/* AI Suggestion Panel */}
            {aiSuggestion && (
              <div className="p-4 bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-b border-[#3d3d40]">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-white text-sm">
                      Análisis de IA
                    </p>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                      <div className="bg-[#2d2d30] rounded-lg p-2 border border-[#3d3d40]">
                        <span className="text-[#8a8a8a]">Intención:</span>
                        <Badge className="ml-1 capitalize bg-purple-500/20 text-purple-300">
                          {aiSuggestion.intent}
                        </Badge>
                      </div>
                      <div className="bg-[#2d2d30] rounded-lg p-2 border border-[#3d3d40]">
                        <span className="text-[#8a8a8a]">Clasificación:</span>
                        <Badge
                          className={`ml-1 capitalize ${
                            aiSuggestion.lead_classification === "caliente"
                              ? "bg-red-500/20 text-red-300"
                              : aiSuggestion.lead_classification === "tibio"
                              ? "bg-orange-500/20 text-orange-300"
                              : "bg-cyan-500/20 text-cyan-300"
                          }`}
                        >
                          {aiSuggestion.lead_classification}
                        </Badge>
                      </div>
                      <div className="bg-[#2d2d30] rounded-lg p-2 border border-[#3d3d40]">
                        <span className="text-[#8a8a8a]">Productos:</span>
                        <span className="ml-1 text-white">
                          {aiSuggestion.suggested_products?.length || 0}
                        </span>
                      </div>
                    </div>
                    {aiSuggestion.suggested_response && (
                      <div className="mt-2 p-2 bg-[#2d2d30] rounded-lg border border-[#3d3d40]">
                        <p className="text-xs text-[#8a8a8a] mb-1">
                          Respuesta sugerida:
                        </p>
                        <p className="text-sm text-white">
                          {aiSuggestion.suggested_response}
                        </p>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={useSuggestedResponse}
                          className="mt-2 border-[#3d3d40] text-white hover:bg-[#3d3d40]"
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
            <ScrollArea className="flex-1 p-4 chat-container bg-[#232326]">
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
                          ? "message-bubble-user"
                          : "message-bubble-business"
                      }`}
                      style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}
                    >
                      <p className="whitespace-pre-wrap">{msg.content?.text || JSON.stringify(msg.content)}</p>
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
              className="p-4 border-t border-[#2d2d30] flex gap-2 bg-[#1a1a1d]"
            >
              <Input
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Escribe un mensaje..."
                className="flex-1 bg-[#2d2d30] text-white border-[#3d3d40] placeholder:text-[#6b6b6b]"
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
          <div className="flex-1 flex items-center justify-center text-[#6b6b6b]">
            <div className="text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium text-white">
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
        <AlertDialogContent className="bg-[#2d2d30] border-[#3d3d40]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">¿Eliminar conversación?</AlertDialogTitle>
            <AlertDialogDescription className="text-[#8a8a8a]">
              Esta acción no se puede deshacer. Se eliminarán todos los mensajes de esta conversación permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-[#3d3d40] text-white border-[#4d4d50] hover:bg-[#4d4d50]">Cancelar</AlertDialogCancel>
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
        <AlertDialogContent className="bg-[#2d2d30] border-[#3d3d40]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">¿Limpiar mensajes?</AlertDialogTitle>
            <AlertDialogDescription className="text-[#8a8a8a]">
              Se eliminarán todos los mensajes de esta conversación. La conversación se mantendrá pero quedará vacía.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-[#3d3d40] text-white border-[#4d4d50] hover:bg-[#4d4d50]">Cancelar</AlertDialogCancel>
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
