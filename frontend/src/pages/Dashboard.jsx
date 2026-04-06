import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/utils/currency";
import {
  Users, Package, FileText, ShoppingBag, MessageSquare,
  TrendingUp, RefreshCw, Loader2, ArrowUpRight,
  ChevronLeft, ChevronRight, CalendarDays
} from "lucide-react";
import { toast } from "sonner";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line
} from "recharts";

const API_URL = process.env.REACT_APP_BACKEND_URL;
const COLORS = ["#63AC9A", "#3b82f6", "#f59e0b", "#8b5cf6", "#ec4899", "#10b981", "#ef4444", "#6366f1"];

export default function Dashboard() {
  const { user: authUser } = useAuth();
  const [stats, setStats] = useState(null);
  const [activityChart, setActivityChart] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [topClients, setTopClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [ordersSummary, setOrdersSummary] = useState(null);
  const [ordersMonth, setOrdersMonth] = useState(() => {
    const now = new Date();
    return { month: now.getMonth() + 1, year: now.getFullYear() };
  });
  const [ordersLoading, setOrdersLoading] = useState(false);
  const headers = {};
  const isAdmin = authUser?.role === "admin";

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, chartRes, prodRes, clientRes] = await Promise.all([
        axios.get(`${API_URL}/api/dashboard-v2/stats`, { headers }),
        axios.get(`${API_URL}/api/dashboard-v2/activity-chart?days=14`, { headers }),
        axios.get(`${API_URL}/api/dashboard-v2/top-products?limit=5`, { headers }),
        axios.get(`${API_URL}/api/dashboard-v2/top-clients?limit=5`, { headers })
      ]);
      setStats(statsRes.data);
      setActivityChart(chartRes.data || []);
      setTopProducts(prodRes.data || []);
      setTopClients(clientRes.data || []);
    } catch {
      toast.error("Error al cargar métricas");
    }
    setLoading(false);
  }, []);

  const fetchOrdersSummary = useCallback(async () => {
    if (!isAdmin) return;
    setOrdersLoading(true);
    try {
      const res = await axios.get(
        `${API_URL}/api/dashboard-v2/orders-by-client?month=${ordersMonth.month}&year=${ordersMonth.year}`,
        { headers }
      );
      setOrdersSummary(res.data);
    } catch {
      // silently fail for non-admin
    }
    setOrdersLoading(false);
  }, [ordersMonth, isAdmin]);

  useEffect(() => { fetchAll(); }, [fetchAll]);
  useEffect(() => { fetchOrdersSummary(); }, [fetchOrdersSummary]);

  if (loading) {
    return <div className="p-6 flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 animate-spin text-[#63AC9A]" /></div>;
  }

  const statCards = [
    { label: "Productos", value: stats?.total_products?.toLocaleString() || "0", icon: Package, color: "bg-[#63AC9A]/15", iconColor: "text-[#63AC9A]", sub: "en inventario" },
    { label: "Clientes", value: stats?.total_clients || 0, icon: Users, color: "bg-blue-50", iconColor: "text-blue-500", sub: "activos" },
    { label: "Cotizaciones", value: stats?.total_quotes || 0, icon: FileText, color: "bg-purple-50", iconColor: "text-purple-500", sub: formatCurrency(stats?.quotes_total_value || 0) },
    { label: "Órdenes de Compra", value: stats?.total_pos || 0, icon: ShoppingBag, color: "bg-orange-50", iconColor: "text-orange-500", sub: formatCurrency(stats?.pos_total_value || 0) },
    { label: "Leads", value: stats?.total_leads || 0, icon: TrendingUp, color: "bg-green-50", iconColor: "text-green-500", sub: "en pipeline" },
    { label: "Conversaciones", value: stats?.active_conversations || 0, icon: MessageSquare, color: "bg-indigo-50", iconColor: "text-indigo-500", sub: "activas WhatsApp" },
  ];

  const chartFormatted = activityChart.map(d => ({
    ...d,
    label: new Date(d.date).toLocaleDateString("es-EC", { day: "2-digit", month: "short" })
  }));

  const MONTH_NAMES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

  const prevMonth = () => {
    setOrdersMonth(prev => {
      if (prev.month === 1) return { month: 12, year: prev.year - 1 };
      return { month: prev.month - 1, year: prev.year };
    });
  };
  const nextMonth = () => {
    const now = new Date();
    setOrdersMonth(prev => {
      const next = prev.month === 12
        ? { month: 1, year: prev.year + 1 }
        : { month: prev.month + 1, year: prev.year };
      if (next.year > now.getFullYear() || (next.year === now.getFullYear() && next.month > now.getMonth() + 1)) return prev;
      return next;
    });
  };

  return (
    <div className="p-4 lg:p-6 space-y-6" data-testid="dashboard-page">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-gray-500 text-sm">Vista general del CRM Gimmicks</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAll} className="gap-2" data-testid="refresh-metrics-btn">
          <RefreshCw size={16} /> Actualizar
        </Button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((s, i) => (
          <Card key={s.label} className="bg-white border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{s.label}</p>
                  <p className="text-3xl font-bold text-gray-800 mt-1">{s.value}</p>
                </div>
                <div className={`w-12 h-12 ${s.color} rounded-xl flex items-center justify-center`}>
                  <s.icon className={`w-6 h-6 ${s.iconColor}`} />
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-2">{s.sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity Chart */}
        <Card className="bg-white shadow-sm">
          <CardHeader className="border-b border-gray-100 pb-3">
            <CardTitle className="text-base font-semibold text-gray-800">Actividad (14 días)</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {chartFormatted.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartFormatted}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="label" fontSize={11} stroke="#9ca3af" />
                  <YAxis fontSize={11} stroke="#9ca3af" allowDecimals={false} />
                  <Tooltip contentStyle={{ borderRadius: "8px", border: "1px solid #e5e7eb" }} />
                  <Bar dataKey="cotizaciones" name="Cotizaciones" fill="#63AC9A" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="ordenes" name="Ordenes" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="leads" name="Leads" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[260px] flex items-center justify-center text-gray-400 text-sm">Sin datos de actividad</div>
            )}
          </CardContent>
        </Card>

        {/* Top Products */}
        <Card className="bg-white shadow-sm">
          <CardHeader className="border-b border-gray-100 pb-3">
            <CardTitle className="text-base font-semibold text-gray-800">Top Productos Cotizados</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {topProducts.length > 0 ? (
              <div className="space-y-3">
                {topProducts.map((p, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: COLORS[i % COLORS.length] }}>{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{p.name || p.code}</p>
                      <p className="text-xs text-gray-400">{p.code} - {p.count} cotizaciones</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-[#63AC9A]">{formatCurrency(p.total_value)}</p>
                      <p className="text-xs text-gray-400">{p.total_quantity} uds</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-gray-400 text-sm">Sin datos de productos</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top Clients */}
      <Card className="bg-white shadow-sm">
        <CardHeader className="border-b border-gray-100 pb-3">
          <CardTitle className="text-base font-semibold text-gray-800">Top Clientes</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          {topClients.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2 font-medium">#</th>
                    <th className="pb-2 font-medium">Cliente</th>
                    <th className="pb-2 font-medium text-right">Cotizaciones</th>
                    <th className="pb-2 font-medium text-right">Valor Total</th>
                  </tr>
                </thead>
                <tbody>
                  {topClients.map((c, i) => (
                    <tr key={c.client_name || `client-${i}`} className="border-b last:border-0">
                      <td className="py-2.5"><span className="w-5 h-5 rounded-full inline-flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: COLORS[i % COLORS.length] }}>{i + 1}</span></td>
                      <td className="py-2.5 font-medium text-gray-800">{c.client_name || "Sin nombre"}</td>
                      <td className="py-2.5 text-right text-gray-600">{c.total_quotes}</td>
                      <td className="py-2.5 text-right font-medium text-[#63AC9A]">{formatCurrency(c.total_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="h-[120px] flex items-center justify-center text-gray-400 text-sm">Sin datos de clientes</div>
          )}
        </CardContent>
      </Card>

      {/* Orders Summary by Client - Admin Only */}
      {isAdmin && (
        <Card className="bg-white shadow-sm" data-testid="orders-by-client-section">
          <CardHeader className="border-b border-gray-100 pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold text-gray-800 flex items-center gap-2">
                <CalendarDays className="w-4 h-4 text-[#63AC9A]" />
                Órdenes por Cliente
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={prevMonth} data-testid="orders-prev-month">
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm font-medium text-gray-700 min-w-[140px] text-center" data-testid="orders-month-label">
                  {MONTH_NAMES[ordersMonth.month - 1]} {ordersMonth.year}
                </span>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={nextMonth} data-testid="orders-next-month">
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4">
            {ordersLoading ? (
              <div className="h-[120px] flex items-center justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-[#63AC9A]" />
              </div>
            ) : ordersSummary?.clients?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="orders-table">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="pb-2 font-medium">Cliente</th>
                      <th className="pb-2 font-medium text-center">Órdenes</th>
                      <th className="pb-2 font-medium text-center">Productos</th>
                      <th className="pb-2 font-medium text-right">Monto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ordersSummary.clients.map((c, i) => (
                      <tr key={c.client_name || `order-${i}`} className="border-b last:border-0">
                        <td className="py-2.5">
                          <p className="font-medium text-gray-800">{c.client_name}</p>
                          {c.phone && <p className="text-xs text-gray-400">{c.phone}</p>}
                        </td>
                        <td className="py-2.5 text-center text-gray-600">{c.total_orders}</td>
                        <td className="py-2.5 text-center text-gray-600">{c.items_count}</td>
                        <td className="py-2.5 text-right font-medium text-[#63AC9A]">{formatCurrency(c.total_amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 border-gray-200">
                      <td className="pt-3 font-semibold text-gray-800">Total del mes</td>
                      <td className="pt-3 text-center font-semibold text-gray-800">{ordersSummary.grand_orders}</td>
                      <td className="pt-3"></td>
                      <td className="pt-3 text-right font-semibold text-[#63AC9A] text-base">{formatCurrency(ordersSummary.grand_total)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <div className="h-[120px] flex items-center justify-center text-gray-400 text-sm">
                Sin órdenes en {MONTH_NAMES[ordersMonth.month - 1]} {ordersMonth.year}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
