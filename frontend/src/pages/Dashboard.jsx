import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Users,
  MessageSquare,
  TrendingUp,
  Clock,
  ArrowUpRight,
  RefreshCw,
  Loader2
} from "lucide-react";
import { toast } from "sonner";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const FUNNEL_COLORS = {
  lead: "#3b82f6",
  pedido: "#eab308",
  produccion: "#a855f7",
  entregado: "#10b981",
  perdido: "#ef4444",
  cierre: "#22c55e"
};

const SOURCE_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ec4899"];

export default function Dashboard() {
  const { getAuthHeaders } = useAuth();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  const fetchMetrics = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/dashboard/metrics`, {
        headers: getAuthHeaders()
      });
      setMetrics(response.data);
    } catch (error) {
      toast.error("Error al cargar métricas");
    } finally {
      setLoading(false);
    }
  };

  const seedDemoData = async () => {
    setSeeding(true);
    try {
      await axios.post(`${API_URL}/api/seed-demo-data`, {}, {
        headers: getAuthHeaders()
      });
      toast.success("Datos de demostración creados");
      fetchMetrics();
    } catch (error) {
      toast.error("Error al crear datos de demostración");
    } finally {
      setSeeding(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const funnelData = metrics?.leads_by_stage
    ? Object.entries(metrics.leads_by_stage).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
        fill: FUNNEL_COLORS[name] || "#6b7280"
      }))
    : [];

  const sourceData = metrics?.leads_by_source
    ? Object.entries(metrics.leads_by_source).map(([name, value], index) => ({
        name: name.replace("_", " ").charAt(0).toUpperCase() + name.slice(1).replace("_", " "),
        value,
        fill: SOURCE_COLORS[index % SOURCE_COLORS.length]
      }))
    : [];

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px] bg-[#1a1a1d]">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-[#1a1a1d] min-h-screen" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white font-['Manrope']">
            Dashboard
          </h1>
          <p className="text-[#8a8a8a] text-sm">
            Vista general del CRM WhatsApp
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchMetrics}
            className="gap-2 border-[#3d3d40] text-[#8a8a8a] hover:text-white hover:bg-[#2d2d30]"
            data-testid="refresh-metrics-btn"
          >
            <RefreshCw size={16} />
            Actualizar
          </Button>
          <Button
            size="sm"
            onClick={seedDemoData}
            disabled={seeding}
            className="bg-emerald-500 hover:bg-emerald-600 gap-2"
            data-testid="seed-demo-btn"
          >
            {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Cargar Demo
          </Button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-[#2d2d30] border-[#3d3d40] shadow-lg hover:shadow-xl transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[#8a8a8a]">Total Leads</p>
                <p className="text-3xl font-bold text-white font-['Manrope']">
                  {metrics?.total_leads || 0}
                </p>
              </div>
              <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-400" />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-1 text-sm">
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
              <span className="text-emerald-400 font-medium">
                +{metrics?.leads_today || 0}
              </span>
              <span className="text-[#6b6b6b]">hoy</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#2d2d30] border-[#3d3d40] shadow-lg hover:shadow-xl transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[#8a8a8a]">Mensajes Hoy</p>
                <p className="text-3xl font-bold text-white font-['Manrope']">
                  {metrics?.messages_today || 0}
                </p>
              </div>
              <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center">
                <MessageSquare className="w-6 h-6 text-emerald-400" />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-1 text-sm">
              <span className="text-[#6b6b6b]">
                {metrics?.active_conversations || 0} conversaciones activas
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#2d2d30] border-[#3d3d40] shadow-lg hover:shadow-xl transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[#8a8a8a]">Tasa Conversión</p>
                <p className="text-3xl font-bold text-white font-['Manrope']">
                  {metrics?.conversion_rate || 0}%
                </p>
              </div>
              <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-purple-400" />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-1 text-sm">
              <span className="text-[#6b6b6b]">Leads convertidos a cierre</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#2d2d30] border-[#3d3d40] shadow-lg hover:shadow-xl transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[#8a8a8a]">Tiempo Respuesta</p>
                <p className="text-3xl font-bold text-white font-['Manrope']">
                  {metrics?.avg_response_time || 0}m
                </p>
              </div>
              <div className="w-12 h-12 bg-orange-500/20 rounded-xl flex items-center justify-center">
                <Clock className="w-6 h-6 text-orange-400" />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-1 text-sm">
              <span className="text-[#6b6b6b]">Promedio de respuesta</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Funnel Chart */}
        <Card className="bg-[#2d2d30] border-[#3d3d40] shadow-lg">
          <CardHeader className="border-b border-[#3d3d40]">
            <CardTitle className="text-lg font-semibold text-white font-['Manrope']">
              Leads por Etapa del Funnel
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {funnelData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={funnelData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#3d3d40" />
                  <XAxis type="number" stroke="#8a8a8a" fontSize={12} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="#8a8a8a"
                    fontSize={12}
                    width={80}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#2d2d30",
                      border: "1px solid #3d3d40",
                      borderRadius: "8px",
                      color: "#fff"
                    }}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {funnelData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-[#6b6b6b]">
                No hay datos disponibles. Carga datos de demo.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Source Chart */}
        <Card className="bg-[#2d2d30] border-[#3d3d40] shadow-lg">
          <CardHeader className="border-b border-[#3d3d40]">
            <CardTitle className="text-lg font-semibold text-white font-['Manrope']">
              Leads por Fuente
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {sourceData.length > 0 ? (
              <div className="flex items-center">
                <ResponsiveContainer width="60%" height={300}>
                  <PieChart>
                    <Pie
                      data={sourceData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                    >
                      {sourceData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#2d2d30",
                        border: "1px solid #3d3d40",
                        borderRadius: "8px",
                        color: "#fff"
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="w-40% space-y-2">
                  {sourceData.map((item, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: item.fill }}
                      />
                      <span className="text-sm text-[#8a8a8a]">{item.name}</span>
                      <span className="text-sm font-medium text-white ml-auto">
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-[#6b6b6b]">
                No hay datos disponibles. Carga datos de demo.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
