import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Loader2, Search, ChevronLeft, ChevronRight, LogIn, FileUp, ShoppingCart, Trash2, Upload, Download, FileText, Edit } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ACTION_LABELS = {
  login: { label: "Inicio de sesión", icon: LogIn, color: "bg-blue-100 text-blue-700" },
  catalog_upload: { label: "Catálogo subido", icon: FileUp, color: "bg-emerald-100 text-emerald-700" },
  catalog_delete: { label: "Catálogo eliminado", icon: Trash2, color: "bg-red-100 text-red-700" },
  inventory_upload: { label: "Subida masiva", icon: Upload, color: "bg-purple-100 text-purple-700" },
  inventory_download: { label: "Descarga inventario", icon: Download, color: "bg-cyan-100 text-cyan-700" },
  product_create: { label: "Producto creado", icon: ShoppingCart, color: "bg-green-100 text-green-700" },
  product_delete: { label: "Producto eliminado", icon: Trash2, color: "bg-orange-100 text-orange-700" },
  quote_update: { label: "Cotización actualizada", icon: Edit, color: "bg-amber-100 text-amber-700" },
  quote_send: { label: "Cotización enviada", icon: FileText, color: "bg-indigo-100 text-indigo-700" },
};

function ActionBadge({ action }) {
  const info = ACTION_LABELS[action] || { label: action, icon: FileText, color: "bg-zinc-100 text-zinc-700" };
  const Icon = info.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${info.color}`} data-testid={`action-badge-${action}`}>
      <Icon className="w-3 h-3" />
      {info.label}
    </span>
  );
}

export default function ActivityLog() {
  const { getAuthHeaders } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [filterUser, setFilterUser] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [actions, setActions] = useState([]);

  const fetchLogs = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: p, limit: 30 });
      if (filterUser) params.set("user_email", filterUser);
      if (filterAction) params.set("action", filterAction);
      if (filterDateFrom) params.set("date_from", filterDateFrom);
      if (filterDateTo) params.set("date_to", filterDateTo);

      const res = await axios.get(`${API_URL}/api/activity-log?${params}`, { headers: getAuthHeaders() });
      setLogs(res.data.logs);
      setTotalPages(res.data.pages);
      setTotal(res.data.total);
      setPage(p);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [filterUser, filterAction, filterDateFrom, filterDateTo, getAuthHeaders]);

  const fetchActions = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/activity-log/actions`, { headers: getAuthHeaders() });
      setActions(res.data.actions || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchActions(); }, []);
  useEffect(() => { fetchLogs(1); }, [fetchLogs]);

  const handleSearch = () => fetchLogs(1);
  const clearFilters = () => {
    setFilterUser("");
    setFilterAction("");
    setFilterDateFrom("");
    setFilterDateTo("");
  };

  return (
    <div className="space-y-6" data-testid="activity-log-page">
      <div>
        <h1 className="text-2xl font-bold font-['Manrope'] text-zinc-900">Historial de Actividad</h1>
        <p className="text-zinc-500 text-sm mt-1">Registro de cada movimiento del sistema por usuario y fecha.</p>
      </div>

      {/* Filters */}
      <Card className="border border-zinc-200">
        <CardContent className="pt-4 pb-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[180px]">
              <label className="text-xs font-medium text-zinc-500 mb-1 block">Usuario</label>
              <Input
                placeholder="Buscar por email..."
                value={filterUser}
                onChange={(e) => setFilterUser(e.target.value)}
                data-testid="filter-user"
              />
            </div>
            <div className="min-w-[180px]">
              <label className="text-xs font-medium text-zinc-500 mb-1 block">Acción</label>
              <Select value={filterAction} onValueChange={setFilterAction}>
                <SelectTrigger data-testid="filter-action">
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  {actions.map(a => (
                    <SelectItem key={a} value={a}>
                      {ACTION_LABELS[a]?.label || a}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[150px]">
              <label className="text-xs font-medium text-zinc-500 mb-1 block">Desde</label>
              <Input type="date" value={filterDateFrom} onChange={(e) => setFilterDateFrom(e.target.value)} data-testid="filter-date-from" />
            </div>
            <div className="min-w-[150px]">
              <label className="text-xs font-medium text-zinc-500 mb-1 block">Hasta</label>
              <Input type="date" value={filterDateTo} onChange={(e) => setFilterDateTo(e.target.value)} data-testid="filter-date-to" />
            </div>
            <Button onClick={handleSearch} className="gap-1 bg-[#63AC9A] hover:bg-[#5a9d8c]" data-testid="filter-search-btn">
              <Search className="w-4 h-4" /> Buscar
            </Button>
            <Button variant="outline" onClick={clearFilters} data-testid="filter-clear-btn">Limpiar</Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card className="border border-zinc-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-['Manrope'] flex items-center justify-between">
            <span>Registros</span>
            <span className="text-sm font-normal text-zinc-500">{total} resultados</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
            </div>
          ) : logs.length === 0 ? (
            <p className="text-center text-zinc-500 py-10">No hay registros de actividad.</p>
          ) : (
            <div className="divide-y divide-zinc-100">
              {logs.map((log) => (
                <div key={log.id} className="flex items-center gap-4 py-3" data-testid="activity-row">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <ActionBadge action={log.action} />
                      <span className="text-sm font-medium text-zinc-800 truncate">{log.user_name || log.user_email}</span>
                    </div>
                    <p className="text-sm text-zinc-600 mt-0.5 truncate">{log.details}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-zinc-400">
                      {new Date(log.timestamp).toLocaleDateString("es-EC")}
                    </p>
                    <p className="text-xs text-zinc-400">
                      {new Date(log.timestamp).toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => fetchLogs(page - 1)} className="gap-1">
                <ChevronLeft className="w-4 h-4" /> Anterior
              </Button>
              <span className="text-sm text-zinc-500">Página {page} de {totalPages}</span>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => fetchLogs(page + 1)} className="gap-1">
                Siguiente <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
