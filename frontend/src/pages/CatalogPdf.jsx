import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { FileText, FileUp, Download, Trash2, Loader2, Upload, AlertTriangle } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function CatalogPdf() {
  const { getAuthHeaders } = useAuth();
  const [catalogInfo, setCatalogInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const fetchInfo = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/catalog/info`, { headers: getAuthHeaders() });
      setCatalogInfo(res.data);
    } catch {
      setCatalogInfo(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchInfo(); }, []);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Solo se permiten archivos PDF");
      return;
    }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await axios.post(`${API_URL}/api/catalog/upload-pdf`, fd, {
        headers: { ...getAuthHeaders(), "Content-Type": "multipart/form-data" }
      });
      toast.success("Catálogo PDF subido correctamente");
      fetchInfo();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al subir el PDF");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("¿Eliminar el catálogo PDF actual?")) return;
    try {
      await axios.delete(`${API_URL}/api/catalog/pdf`, { headers: getAuthHeaders() });
      toast.success("Catálogo eliminado");
      setCatalogInfo({ has_catalog: false });
    } catch {
      toast.error("Error al eliminar");
    }
  };

  const fmt = (bytes) => {
    if (!bytes) return "0 B";
    const k = 1024;
    const s = ["B", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + s[i];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-6 space-y-6" data-testid="catalog-pdf-page">
      <div>
        <h1 className="text-2xl font-bold font-['Manrope'] text-zinc-900">Catálogo PDF</h1>
        <p className="text-zinc-500 text-sm mt-1">
          El catálogo se envía automáticamente por WhatsApp cuando el bot no encuentra productos específicos.
        </p>
      </div>

      {catalogInfo?.has_catalog ? (
        <Card className="border border-zinc-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg font-['Manrope']">
              <FileText className="w-5 h-5 text-emerald-600" />
              Catálogo Actual
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
              <div className="w-14 h-14 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-7 h-7 text-emerald-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-emerald-900 truncate text-base" data-testid="catalog-filename">
                  {catalogInfo.original_name}
                </p>
                <p className="text-sm text-emerald-700 mt-0.5">
                  Tamaño: {fmt(catalogInfo.size_bytes)}
                </p>
                <p className="text-sm text-emerald-700">
                  Subido por: <span className="font-medium">{catalogInfo.uploaded_by}</span>
                </p>
                <p className="text-xs text-emerald-600 mt-0.5">
                  {catalogInfo.uploaded_at ? new Date(catalogInfo.uploaded_at).toLocaleString("es-EC") : ""}
                </p>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <a href={`${API_URL}/api/catalog/pdf`} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline" size="sm" className="gap-1" data-testid="catalog-view-btn">
                    <Download className="w-4 h-4" /> Ver
                  </Button>
                </a>
                <Button variant="destructive" size="sm" className="gap-1" onClick={handleDelete} data-testid="catalog-delete-btn">
                  <Trash2 className="w-4 h-4" /> Eliminar
                </Button>
              </div>
            </div>

            <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg">
              <p className="text-sm text-zinc-600 mb-2">
                <strong>Reemplazar catálogo:</strong> Al subir un nuevo PDF, el anterior será eliminado automáticamente.
              </p>
              <label className="inline-flex cursor-pointer">
                <input type="file" accept=".pdf" className="hidden" onChange={handleUpload} data-testid="catalog-replace-input" />
                <Button variant="outline" size="sm" className="gap-1" disabled={uploading} asChild>
                  <span>
                    {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                    {uploading ? "Subiendo..." : "Reemplazar PDF"}
                  </span>
                </Button>
              </label>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border border-zinc-200">
          <CardContent className="py-10">
            <div className="text-center space-y-4">
              <FileUp className="w-12 h-12 text-zinc-400 mx-auto" />
              <div>
                <p className="font-semibold text-zinc-700 text-lg">No hay catálogo PDF configurado</p>
                <p className="text-sm text-zinc-500 mt-1">
                  Sube un archivo PDF con el catálogo completo de productos.
                </p>
              </div>
              <label className="inline-flex cursor-pointer">
                <input type="file" accept=".pdf" className="hidden" onChange={handleUpload} data-testid="catalog-upload-input" />
                <Button className="gap-2 bg-[#63AC9A] hover:bg-[#5a9d8c]" disabled={uploading} asChild>
                  <span>
                    {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileUp className="w-4 h-4" />}
                    {uploading ? "Subiendo..." : "Subir Catálogo PDF"}
                  </span>
                </Button>
              </label>
            </div>

            <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-yellow-700">
                Sin catálogo PDF, el bot solo informará al cliente que no hay coincidencias en inventario.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
