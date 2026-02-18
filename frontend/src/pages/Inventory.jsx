import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { toast } from "sonner";
import { formatCurrency } from "@/utils/currency";
import {
  Search, Upload, Plus, Trash2, Edit, ChevronLeft, ChevronRight,
  X, Package, Download, Image as ImageIcon, Loader2, ChevronDown, ChevronUp
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Inventory() {
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editProduct, setEditProduct] = useState(null);
  const [limit] = useState(50);
  const [minCost, setMinCost] = useState("");
  const [maxCost, setMaxCost] = useState("");
  const fileInputRef = useRef(null);
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, limit };
      if (search) params.search = search;
      if (category && category !== "Todas") params.category = category;
      if (minCost !== "") params.min_cost = parseFloat(minCost);
      if (maxCost !== "") params.max_cost = parseFloat(maxCost);
      const res = await axios.get(`${API_URL}/api/inventory/`, { params, headers });
      setProducts(res.data.products || []);
      setTotal(res.data.total || 0);
      setPages(res.data.pages || 1);
    } catch (e) {
      toast.error("Error al cargar productos");
    }
    setLoading(false);
  }, [page, limit, search, category, minCost, maxCost]);

  const fetchCategories = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/inventory/categories`, { headers });
      setCategories(res.data || []);
    } catch {}
  };

  useEffect(() => { fetchProducts(); }, [fetchProducts]);
  useEffect(() => { fetchCategories(); }, []);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await axios.post(`${API_URL}/api/inventory/upload`, formData, {
        headers: { ...headers, "Content-Type": "multipart/form-data" }
      });
      toast.success(res.data.message);
      setPage(1);
      fetchProducts();
      fetchCategories();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error al subir archivo");
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDelete = async (code) => {
    if (!window.confirm("¿Eliminar este producto?")) return;
    try {
      await axios.delete(`${API_URL}/api/inventory/${code}`, { headers });
      toast.success("Producto eliminado");
      fetchProducts();
    } catch {
      toast.error("Error al eliminar");
    }
  };

  const handleExport = () => {
    import("xlsx").then(XLSX => {
      const data = products.map(p => ({
        "Código": p.code, "Cód. Proveedor": p.supplier_code, Nombre: p.name,
        "Descripción": p.description, Stock: p.stock, Costo: p.cost,
        PVP: p.price, Proveedor: p.supplier,
        "Categorías": (p.categories || []).join(", "), Imagen: p.image_url
      }));
      const ws = XLSX.utils.json_to_sheet(data);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Inventario");
      XLSX.writeFile(wb, "inventario_gimmicks.xlsx");
    });
  };

  const getImageUrl = (url) => {
    if (!url) return null;
    if (url.startsWith("/api/uploads/")) return `${API_URL}${url}`;
    const driveMatch = url.match(/drive\.google\.com\/file\/d\/([^/\?]+)/);
    if (driveMatch) return `https://drive.google.com/thumbnail?id=${driveMatch[1]}&sz=w200`;
    if (url.match(/drive\.google\.com\/open\?id=(.+)/)) {
      const id = url.match(/id=([^&]+)/)?.[1];
      if (id) return `https://drive.google.com/thumbnail?id=${id}&sz=w200`;
    }
    return url;
  };

  return (
    <div className="p-4 lg:p-6 flex flex-col h-[calc(100vh-64px)]" data-testid="inventory-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4 flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Package size={24} className="text-[#7BA899]" /> Inventario
          </h1>
          <p className="text-sm text-gray-500 mt-1">{total.toLocaleString()} productos</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={handleExport} data-testid="export-btn">
            <Download size={16} className="mr-1" /> Exportar
          </Button>
          <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} disabled={uploading} data-testid="upload-btn">
            {uploading ? <Loader2 size={16} className="mr-1 animate-spin" /> : <Upload size={16} className="mr-1" />}
            {uploading ? "Subiendo..." : "Subir Excel"}
          </Button>
          <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv" onChange={handleUpload} className="hidden" />
          <Button size="sm" className="bg-[#7BA899] hover:bg-[#5E8A7A]" onClick={() => { setEditProduct(null); setShowAddModal(true); }} data-testid="add-product-btn">
            <Plus size={16} className="mr-1" /> Agregar
          </Button>
        </div>
      </div>

      {/* Filters - all in one line */}
      <div className="flex items-center gap-2 mb-4">
        <div className="relative flex-shrink-0 w-[260px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Buscar por código, nombre, categoría..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9 bg-white h-9 text-sm"
            data-testid="search-input"
          />
        </div>
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1); }}
          className="border rounded-lg px-2 py-2 text-sm bg-white h-9 w-[160px] flex-shrink-0"
          data-testid="category-filter"
        >
          <option value="">Todas las categorías</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <Input type="number" step="0.01" placeholder="Min $" value={minCost} onChange={(e) => { setMinCost(e.target.value); setPage(1); }} className="w-[100px] bg-white text-sm h-9 flex-shrink-0" data-testid="min-cost-input" />
        <span className="text-gray-400 text-xs flex-shrink-0">-</span>
        <Input type="number" step="0.01" placeholder="Max $" value={maxCost} onChange={(e) => { setMaxCost(e.target.value); setPage(1); }} className="w-[100px] bg-white text-sm h-9 flex-shrink-0" data-testid="max-cost-input" />
      </div>

      {/* Table with horizontal scroll - fills remaining height */}
      <div className="bg-white rounded-xl shadow-sm border flex flex-col flex-1 min-h-0">
        <div className="overflow-auto flex-1">
          <table className="w-full text-sm min-w-[1100px]" data-testid="inventory-table">
            <thead className="sticky top-0 z-20">
              <tr className="bg-gray-50 text-left border-b">
                <th className="px-2 py-3 font-semibold text-gray-500 w-14 text-center sticky left-0 bg-gray-50 z-10"></th>
                <th className="px-3 py-3 font-semibold text-gray-500 w-16">Imagen</th>
                <th className="px-3 py-3 font-semibold text-gray-500">Cód. Prod</th>
                <th className="px-3 py-3 font-semibold text-gray-500">Código</th>
                <th className="px-3 py-3 font-semibold text-gray-500">Nombre</th>
                <th className="px-3 py-3 font-semibold text-gray-500">Descripción</th>
                <th className="px-3 py-3 font-semibold text-gray-500 text-center">Stock</th>
                <th className="px-3 py-3 font-semibold text-gray-500 text-right">Costo</th>
                <th className="px-3 py-3 font-semibold text-gray-500 text-right">PVP</th>
                <th className="px-3 py-3 font-semibold text-gray-500">Proveedor</th>
                <th className="px-3 py-3 font-semibold text-gray-500">Categorías</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={11} className="text-center py-10 text-gray-400">
                  <Loader2 size={24} className="animate-spin mx-auto" />
                </td></tr>
              ) : products.length === 0 ? (
                <tr><td colSpan={11} className="text-center py-10 text-gray-400">No se encontraron productos</td></tr>
              ) : products.map((p) => (
                <tr key={p.code || p.id} className="border-b hover:bg-gray-50/50 transition-colors" data-testid={`product-row-${p.code}`}>
                  {/* Actions - left side */}
                  <td className="px-2 py-1.5 sticky left-0 bg-white z-10">
                    <div className="flex items-center gap-0.5">
                      <button onClick={() => { setEditProduct(p); setShowAddModal(true); }} className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-blue-600" data-testid={`edit-btn-${p.code}`}>
                        <Edit size={14} />
                      </button>
                      <button onClick={() => handleDelete(p.code)} className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-red-500" data-testid={`delete-btn-${p.code}`}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                  {/* Image */}
                  <td className="px-3 py-1.5">
                    {p.image_url ? (
                      <img src={getImageUrl(p.image_url)} alt="" className="w-10 h-10 object-cover rounded" onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling && (e.target.nextSibling.style.display = 'flex'); }} />
                    ) : null}
                    <div className={`w-10 h-10 bg-gray-100 rounded items-center justify-center ${p.image_url ? 'hidden' : 'flex'}`}>
                      <ImageIcon size={16} className="text-gray-300" />
                    </div>
                  </td>
                  <td className="px-3 py-1.5 font-mono text-xs whitespace-nowrap">{p.code}</td>
                  <td className="px-3 py-1.5 text-gray-500 text-xs">{p.supplier_code || "-"}</td>
                  <td className="px-3 py-1.5 font-medium max-w-[160px] truncate text-sm">{p.name}</td>
                  <td className="px-3 py-1.5 text-gray-500 text-xs max-w-[180px] truncate">{p.description}</td>
                  <td className="px-3 py-1.5 text-center text-sm">{p.stock}</td>
                  <td className="px-3 py-1.5 text-right text-gray-500 text-sm">{formatCurrency(p.cost)}</td>
                  <td className="px-3 py-1.5 text-right font-semibold text-green-700 text-sm">{formatCurrency(p.price)}</td>
                  <td className="px-3 py-1.5 text-gray-500 text-xs whitespace-nowrap">{p.supplier || "-"}</td>
                  {/* Categories - compact with expandable */}
                  <td className="px-3 py-1.5">
                    <CategoryCell categories={p.categories || []} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50 flex-shrink-0" data-testid="pagination">
          <span className="text-sm text-gray-500">
            Mostrando {((page - 1) * limit) + 1}-{Math.min(page * limit, total)} de {total.toLocaleString()}
          </span>
          <div className="flex gap-1">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)} data-testid="prev-page-btn">
              <ChevronLeft size={16} />
            </Button>
            <span className="px-3 py-1 text-sm flex items-center">{page} / {pages}</span>
            <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage(p => p + 1)} data-testid="next-page-btn">
              <ChevronRight size={16} />
            </Button>
          </div>
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showAddModal && (
        <ProductModal
          product={editProduct}
          onClose={() => { setShowAddModal(false); setEditProduct(null); }}
          onSave={() => { setShowAddModal(false); setEditProduct(null); fetchProducts(); fetchCategories(); }}
        />
      )}
    </div>
  );
}

function CategoryCell({ categories }) {
  const [expanded, setExpanded] = useState(false);
  if (!categories.length) return <span className="text-gray-300 text-xs">-</span>;
  const visible = expanded ? categories : categories.slice(0, 3);
  const hasMore = categories.length > 3;

  return (
    <div className="flex items-center gap-1 max-w-[220px]">
      <div className="flex flex-wrap gap-0.5">
        {visible.map((c, i) => (
          <span key={i} className="bg-[#7BA899] text-white text-[10px] leading-tight px-1.5 py-[1px] rounded font-medium whitespace-nowrap">{c}</span>
        ))}
      </div>
      {hasMore && (
        <button onClick={() => setExpanded(!expanded)} className="flex-shrink-0 text-gray-400 hover:text-gray-600 p-0.5" data-testid="expand-categories-btn">
          {expanded ? <ChevronUp size={13} /> : <span className="text-[10px] text-gray-400 whitespace-nowrap">+{categories.length - 3}</span>}
        </button>
      )}
    </div>
  );
}

function ProductModal({ product, onClose, onSave }) {
  const [form, setForm] = useState({
    code: product?.code || "",
    supplier_code: product?.supplier_code || "",
    name: product?.name || "",
    description: product?.description || "",
    price: product?.price || 0,
    cost: product?.cost || 0,
    stock: product?.stock || 0,
    supplier: product?.supplier || "",
    image_url: product?.image_url || "",
    categories: product?.categories || []
  });
  const [saving, setSaving] = useState(false);
  const [catInput, setCatInput] = useState("");
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };
  const isEdit = !!product;

  const handleSave = async () => {
    if (!form.code || !form.name) { toast.error("Código y nombre son requeridos"); return; }
    setSaving(true);
    try {
      if (isEdit) {
        await axios.put(`${API_URL}/api/inventory/${product.code}`, form, { headers });
        toast.success("Producto actualizado");
      } else {
        await axios.post(`${API_URL}/api/inventory/`, form, { headers });
        toast.success("Producto creado");
      }
      onSave();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error al guardar");
    }
    setSaving(false);
  };

  const addCategory = () => {
    if (catInput.trim() && !form.categories.includes(catInput.trim())) {
      setForm({ ...form, categories: [...form.categories, catInput.trim()] });
      setCatInput("");
    }
  };

  const removeCategory = (c) => setForm({ ...form, categories: form.categories.filter(x => x !== c) });

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("image", file);
    try {
      const res = await axios.post(`${API_URL}/api/inventory/upload-image`, formData, {
        headers: { ...headers, "Content-Type": "multipart/form-data" }
      });
      setForm({ ...form, image_url: res.data.image_url });
      toast.success("Imagen subida");
    } catch { toast.error("Error al subir imagen"); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="product-modal">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-bold">{isEdit ? "Editar Producto" : "Nuevo Producto"}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
        </div>
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Código *</label>
              <Input value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} disabled={isEdit} data-testid="product-code-input" />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Cód. Proveedor</label>
              <Input value={form.supplier_code} onChange={e => setForm({ ...form, supplier_code: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Nombre *</label>
            <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="product-name-input" />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Descripción</label>
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">PVP</label>
              <Input type="number" step="0.01" value={form.price} onChange={e => setForm({ ...form, price: parseFloat(e.target.value) || 0 })} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Costo</label>
              <Input type="number" step="0.01" value={form.cost} onChange={e => setForm({ ...form, cost: parseFloat(e.target.value) || 0 })} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Stock</label>
              <Input type="number" value={form.stock} onChange={e => setForm({ ...form, stock: parseInt(e.target.value) || 0 })} />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Proveedor</label>
            <Input value={form.supplier} onChange={e => setForm({ ...form, supplier: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Categorías</label>
            <div className="flex gap-2">
              <Input value={catInput} onChange={e => setCatInput(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addCategory())} placeholder="Agregar categoría..." />
              <Button variant="outline" size="sm" onClick={addCategory}>+</Button>
            </div>
            <div className="flex flex-wrap gap-1 mt-2">
              {form.categories.map(c => (
                <span key={c} className="bg-[#7BA899] text-white text-xs px-2 py-0.5 rounded flex items-center gap-1">
                  {c} <button onClick={() => removeCategory(c)}><X size={12} /></button>
                </span>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1">Imagen</label>
            <div className="flex gap-2 items-center">
              <Input value={form.image_url} onChange={e => setForm({ ...form, image_url: e.target.value })} placeholder="URL o subir imagen" className="flex-1" />
              <label className="cursor-pointer">
                <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                <Button variant="outline" size="sm" type="button" asChild><span><ImageIcon size={14} /></span></Button>
              </label>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 p-5 border-t">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button className="bg-[#7BA899] hover:bg-[#5E8A7A]" onClick={handleSave} disabled={saving} data-testid="save-product-btn">
            {saving ? <Loader2 size={16} className="animate-spin mr-1" /> : null}
            {isEdit ? "Actualizar" : "Crear"}
          </Button>
        </div>
      </div>
    </div>
  );
}
