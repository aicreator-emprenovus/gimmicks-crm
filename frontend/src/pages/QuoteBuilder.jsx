import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { toast } from "sonner";
import { formatCurrency } from "@/utils/currency";
import { useNavigate, useSearchParams, useLocation } from "react-router-dom";
import {
  Plus, Trash2, Search, FileText, X, Loader2, Save, Send,
  Minus, ChevronDown, ChevronUp, ChevronLeft, ChevronRight,
  Image as ImageIcon, Eye, Copy, FilterX, Tag
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function QuoteBuilder() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const editId = searchParams.get("edit");
  const isPORoute = location.pathname.startsWith("/purchase-orders");
  const docType = searchParams.get("type") || (isPORoute ? "PO" : "QUOTE");

  const [clients, setClients] = useState([]);
  const [products, setProducts] = useState([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [prodPage, setProdPage] = useState(1);
  const [prodPages, setProdPages] = useState(1);
  const [productSearch, setProductSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [categories, setCategories] = useState([]);
  const [loadingProducts, setLoadingProducts] = useState(false);

  const [cart, setCart] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientContact, setClientContact] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [paymentTerms, setPaymentTerms] = useState("50% anticipo, 50% contra entrega");
  const [validity, setValidity] = useState("8 dias");
  const [deliveryTime, setDeliveryTime] = useState("Por confirmar");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [otros, setOtros] = useState("");

  const [detailProduct, setDetailProduct] = useState(null);
  const [detailIndex, setDetailIndex] = useState(-1);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };
  const isEdit = !!editId;
  const backPath = isPORoute ? "/purchase-orders" : "/quotes";

  useEffect(() => {
    fetchClients();
    fetchCategories();
    if (editId) loadExisting();
  }, [editId]);

  const fetchClients = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/clients/`, { headers });
      setClients(res.data || []);
    } catch {}
  };

  const fetchCategories = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/inventory/categories`, { headers });
      setCategories(res.data || []);
    } catch {}
  };

  const loadExisting = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/quotes-v2/${editId}`, { headers });
      const q = res.data;
      setSelectedClient({ id: q.client_id, name: q.client_name, email: q.client_email });
      setClientContact(q.client_contact || "");
      setClientEmail(q.client_email || "");
      setPaymentTerms(q.payment_terms || "50% anticipo, 50% contra entrega");
      setValidity(q.validity || "8 dias");
      setDeliveryTime(q.delivery_time || "Por confirmar");
      setCart((q.items || []).map((item, i) => ({
        ...item,
        item_id: item.item_id || `item-${i}`,
        discount_amount: item.discount_amount || 0,
        discount_type: item.discount_type || "$",
        additional_amount: item.additional_amount || 0,
        additional_type: item.additional_type || "$",
        otros: item.otros || ""
      })));
    } catch { toast.error("Error al cargar cotización"); }
    setLoading(false);
  };

  const fetchProducts = useCallback(async () => {
    setLoadingProducts(true);
    try {
      const params = { page: prodPage, limit: 20 };
      if (productSearch) params.search = productSearch;
      if (selectedCategory) params.category = selectedCategory;
      if (minPrice) params.min_cost = parseFloat(minPrice);
      if (maxPrice) params.max_cost = parseFloat(maxPrice);
      const res = await axios.get(`${API_URL}/api/inventory/`, { params, headers });
      setProducts(res.data.products || []);
      setTotalProducts(res.data.total || 0);
      setProdPages(res.data.pages || 1);
    } catch {}
    setLoadingProducts(false);
  }, [prodPage, productSearch, selectedCategory, minPrice, maxPrice]);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  const addToCart = (product) => {
    setCart(prev => [...prev, {
      item_id: `item-${Date.now()}-${Math.random().toString(36).substr(2,5)}`,
      product_id: product.id || "",
      code: product.code,
      name: product.name,
      description: product.description || "",
      quantity: 1,
      unit_price: product.price || 0,
      total_price: product.price || 0,
      image_url: product.image_url || "",
      categories: product.categories || [],
      selected_characteristics: [],
      discount_amount: 0,
      discount_type: "$",
      additional_amount: 0,
      additional_type: "$",
      otros: ""
    }]);
    toast.success(`${product.name} agregado`);
  };

  const duplicateCartItem = (itemId) => {
    const item = cart.find(i => i.item_id === itemId);
    if (!item) return;
    setCart(prev => [...prev, {
      ...item,
      item_id: `item-${Date.now()}-${Math.random().toString(36).substr(2,5)}`
    }]);
  };

  const updateCartItem = (itemId, field, value) => {
    setCart(cart.map(i => {
      if (i.item_id !== itemId) return i;
      const updated = { ...i, [field]: value };
      let base = updated.quantity * updated.unit_price;
      if (updated.discount_amount > 0) {
        if (updated.discount_type === "%") base -= base * (updated.discount_amount / 100);
        else base -= updated.discount_amount;
      }
      if (updated.additional_amount > 0) {
        if (updated.additional_type === "%") base += base * (updated.additional_amount / 100);
        else base += updated.additional_amount;
      }
      updated.total_price = Math.max(0, base);
      return updated;
    }));
  };

  const removeFromCart = (itemId) => setCart(cart.filter(i => i.item_id !== itemId));

  const subtotal = cart.reduce((sum, i) => sum + i.total_price, 0);
  const tax = subtotal * 0.15;
  const total = subtotal + tax;

  const handleSave = async (status = "draft") => {
    if (!selectedClient) { toast.error("Seleccione un cliente"); return; }
    if (cart.length === 0) { toast.error("Agregue al menos un producto"); return; }
    setSaving(true);
    const quoteData = {
      doc_type: docType,
      client_id: selectedClient.id,
      client_name: selectedClient.name,
      client_contact: clientContact,
      client_email: clientEmail || selectedClient.email,
      items: cart,
      subtotal: Math.round(subtotal * 100) / 100,
      tax: Math.round(tax * 100) / 100,
      total: Math.round(total * 100) / 100,
      status,
      payment_terms: paymentTerms,
      validity,
      delivery_time: deliveryTime
    };
    try {
      if (isEdit) {
        await axios.put(`${API_URL}/api/quotes-v2/${editId}`, quoteData, { headers });
        toast.success(docType === "PO" ? "Orden actualizada" : "Cotización actualizada");
      } else {
        await axios.post(`${API_URL}/api/quotes-v2/`, quoteData, { headers });
        toast.success(docType === "PO" ? "Orden creada" : "Cotización creada");
      }
      navigate(backPath);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error al guardar");
    }
    setSaving(false);
  };

  const clearFilters = () => {
    setProductSearch("");
    setSelectedCategory("");
    setMinPrice("");
    setMaxPrice("");
    setProdPage(1);
  };

  const getImageUrl = (url) => {
    if (!url) return null;
    if (url.startsWith("/api/uploads/")) return `${API_URL}${url}`;
    const driveMatch = url.match(/drive\.google\.com\/file\/d\/([^/\?]+)/);
    if (driveMatch) return `https://drive.google.com/thumbnail?id=${driveMatch[1]}&sz=w200`;
    return url;
  };

  const openDetail = (product, index) => {
    setDetailProduct(product);
    setDetailIndex(index);
  };

  const navigateDetail = (dir) => {
    const newIdx = detailIndex + dir;
    if (newIdx >= 0 && newIdx < products.length) {
      setDetailProduct(products[newIdx]);
      setDetailIndex(newIdx);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 size={32} className="animate-spin text-gray-400" /></div>;
  }

  return (
    <div className="flex h-[calc(100vh-64px)]" data-testid="quote-builder-page">
      {/* LEFT: Product Catalog */}
      <div className="flex-1 flex flex-col overflow-hidden p-4">
        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border p-4 mb-3 flex-shrink-0" data-testid="catalog-filters">
          <div className="flex gap-2 mb-2">
            <div className="relative flex-1 min-w-0">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Buscar por código, nombre, categoría..."
                value={productSearch}
                onChange={e => { setProductSearch(e.target.value); setProdPage(1); }}
                className="pl-9 w-full"
                data-testid="catalog-search-input"
              />
            </div>
            <div className="w-[26%] min-w-0 relative">
              <select
                value={selectedCategory}
                onChange={e => { setSelectedCategory(e.target.value); setProdPage(1); }}
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white truncate"
                style={{maxWidth: '100%'}}
                data-testid="catalog-category-filter"
              >
              <option value="">Categorías</option>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div>
              <label className="text-xs text-gray-500">Precio Minimo</label>
              <Input type="number" step="0.01" placeholder="$ Min" value={minPrice} onChange={e => { setMinPrice(e.target.value); setProdPage(1); }} className="h-8 text-sm" data-testid="catalog-min-price" />
            </div>
            <span className="text-gray-400 mt-4">-</span>
            <div>
              <label className="text-xs text-gray-500">Precio Maximo</label>
              <Input type="number" step="0.01" placeholder="$ Max" value={maxPrice} onChange={e => { setMaxPrice(e.target.value); setProdPage(1); }} className="h-8 text-sm" data-testid="catalog-max-price" />
            </div>
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-red-500 mt-4 ml-2 whitespace-nowrap"
              data-testid="clear-filters-btn"
            >
              <FilterX size={14} /> Limpiar filtros
            </button>
          </div>
        </div>

        {/* Product Grid */}
        <div className="flex-1 overflow-y-auto">
          {loadingProducts ? (
            <div className="flex justify-center py-10"><Loader2 size={24} className="animate-spin text-gray-400" /></div>
          ) : products.length === 0 ? (
            <div className="text-center py-10 text-gray-400">No se encontraron productos</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {products.map((p, idx) => (
                <div key={p.code} className="bg-white rounded-xl shadow-sm border overflow-hidden hover:shadow-md transition-shadow" data-testid={`catalog-product-${p.code}`}>
                  <div className="aspect-square bg-gray-100 flex items-center justify-center overflow-hidden">
                    {p.image_url ? (
                      <img src={getImageUrl(p.image_url)} alt="" className="w-full h-full object-cover" onError={e => { e.target.style.display='none'; e.target.nextSibling && (e.target.nextSibling.style.display='flex'); }} />
                    ) : null}
                    <div className={`w-full h-full items-center justify-center text-gray-400 text-sm font-medium ${p.image_url ? 'hidden' : 'flex'}`}>
                      No Image
                    </div>
                  </div>
                  <div className="p-2.5">
                    <p className="text-[11px] text-gray-400 font-mono">{p.code}</p>
                    <div className="flex items-center gap-1">
                      <span className="font-bold text-sm text-[#63AC9A]">{formatCurrency(p.price)}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-800 truncate mt-0.5">{p.name}</p>
                    <div className="flex gap-1.5 mt-2">
                      <button
                        onClick={() => addToCart(p)}
                        className="flex-1 bg-[#63AC9A] hover:bg-[#4F9A87] text-white text-xs font-medium py-1.5 rounded-lg transition-colors"
                        data-testid={`add-product-${p.code}`}
                      >
                        Agregar
                      </button>
                      <button
                        onClick={() => openDetail(p, idx)}
                        className="flex-1 bg-gray-800 hover:bg-gray-900 text-white text-xs font-medium py-1.5 rounded-lg transition-colors"
                        data-testid={`detail-product-${p.code}`}
                      >
                        Detalles
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {/* Pagination */}
          {prodPages > 1 && (
            <div className="flex items-center justify-center gap-2 py-3">
              <Button variant="outline" size="sm" disabled={prodPage <= 1} onClick={() => setProdPage(p => p - 1)}><ChevronLeft size={14} /></Button>
              <span className="text-xs text-gray-500">{prodPage} / {prodPages}</span>
              <Button variant="outline" size="sm" disabled={prodPage >= prodPages} onClick={() => setProdPage(p => p + 1)}><ChevronRight size={14} /></Button>
            </div>
          )}
        </div>
      </div>

      {/* RIGHT: Quote Builder Panel */}
      <div className="w-[340px] flex-shrink-0 border-l bg-white flex flex-col overflow-hidden" data-testid="quote-panel">
        <div className="p-4 border-b flex-shrink-0">
          <h2 className="font-bold text-base flex items-center gap-2">
            <FileText size={18} />
            {isEdit ? "Editar" : "Nueva"} {docType === "PO" ? "Orden" : "Cotizacion"}
          </h2>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Client Selector */}
          <div data-testid="client-selector">
            {selectedClient ? (
              <div className="flex items-center justify-between bg-gray-50 rounded-lg p-2 text-sm">
                <span className="font-medium truncate">{selectedClient.name}</span>
                <button onClick={() => setSelectedClient(null)} className="p-0.5 hover:bg-gray-200 rounded"><X size={14} /></button>
              </div>
            ) : (
              <ClientDropdown clients={clients} onSelect={(c) => {
                setSelectedClient(c);
                setClientEmail(c.email || c.commercial_email || "");
                setClientContact(c.contact_person || "");
              }} />
            )}
          </div>

          {/* Cart Items */}
          {cart.length === 0 ? (
            <p className="text-center text-gray-500 py-4 text-xs">Agregue productos</p>
          ) : (
            <div className="space-y-2">
              {cart.map(item => (
                <CartItemCompact
                  key={item.item_id}
                  item={item}
                  onUpdate={updateCartItem}
                  onRemove={removeFromCart}
                  onDuplicate={duplicateCartItem}
                  getImageUrl={getImageUrl}
                />
              ))}
            </div>
          )}
        </div>

        {/* Summary Footer */}
        <div className="border-t p-4 flex-shrink-0 bg-white">
          <div className="text-sm space-y-1 mb-3">
            <div className="flex justify-between text-gray-500"><span>Subtotal:</span><span>{formatCurrency(subtotal)}</span></div>
            <div className="flex justify-between font-bold text-base">
              <span>Total (Inc. IVA):</span>
              <span>{formatCurrency(total)}</span>
            </div>
          </div>
          <button
            onClick={() => handleSave("draft")}
            disabled={saving}
            className="w-full py-2.5 rounded-xl bg-gray-800 hover:bg-gray-900 text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50 mb-2"
            data-testid="save-quote-btn"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Guardar {docType === "PO" ? "Orden" : "Cotizacion"}
          </button>
          <button
            onClick={() => { setCart([]); setSelectedClient(null); setOtros(""); }}
            className="w-full py-2 rounded-xl border border-red-200 text-red-500 hover:bg-red-50 text-sm font-medium flex items-center justify-center gap-2 transition-colors"
            data-testid="clear-cart-btn"
          >
            <Trash2 size={14} /> Limpiar
          </button>
        </div>
      </div>

      {/* Product Detail Modal */}
      {detailProduct && (
        <ProductDetailModal
          product={detailProduct}
          index={detailIndex}
          total={products.length}
          onClose={() => setDetailProduct(null)}
          onAdd={addToCart}
          onPrev={() => navigateDetail(-1)}
          onNext={() => navigateDetail(1)}
          getImageUrl={getImageUrl}
        />
      )}
    </div>
  );
}

function ClientDropdown({ clients, onSelect }) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const filtered = clients.filter(c =>
    !search || c.name?.toLowerCase().includes(search.toLowerCase()) || c.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="relative">
      <select
        className="w-full border rounded-lg px-3 py-2 text-sm bg-white appearance-none cursor-pointer"
        value=""
        onChange={e => {
          const c = clients.find(cl => cl.id === e.target.value);
          if (c) onSelect(c);
        }}
        data-testid="client-dropdown"
      >
        <option value="">Seleccionar Cliente...</option>
        {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
    </div>
  );
}

function CartItemCompact({ item, onUpdate, onRemove, onDuplicate, getImageUrl }) {
  const [expanded, setExpanded] = useState(true);
  const [showCharsModal, setShowCharsModal] = useState(false);

  return (
    <div className="border rounded-lg p-2 text-xs" data-testid={`cart-item-${item.item_id}`}>
      <div className="flex gap-2 items-start">
        <div className="w-10 h-10 rounded bg-gray-100 flex-shrink-0 overflow-hidden">
          {item.image_url ? (
            <img src={getImageUrl(item.image_url)} alt="" className="w-full h-full object-cover" onError={e => { e.target.style.display='none'; }} />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-300"><ImageIcon size={14} /></div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <div className="min-w-0">
              <p className="font-medium truncate leading-tight">{item.name}</p>
              <p className="text-gray-500">{item.code}</p>
            </div>
            <div className="text-right flex-shrink-0 ml-1">
              <p className="text-gray-500">{formatCurrency(item.unit_price)} x {item.quantity}</p>
              <p className="font-bold text-[#63AC9A]">{formatCurrency(item.total_price)}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 mt-1">
            <button onClick={() => onUpdate(item.item_id, "quantity", Math.max(1, item.quantity - 1))} className="w-6 h-6 border rounded flex items-center justify-center hover:bg-gray-50"><Minus size={10} /></button>
            <input type="number" value={item.quantity} onChange={e => onUpdate(item.item_id, "quantity", Math.max(1, parseInt(e.target.value) || 1))} className="w-10 text-center border rounded h-6 text-xs" />
            <button onClick={() => onUpdate(item.item_id, "quantity", item.quantity + 1)} className="w-6 h-6 border rounded flex items-center justify-center hover:bg-gray-50"><Plus size={10} /></button>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t">
        <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-0.5 text-gray-500 hover:text-gray-700">
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />} {expanded ? "Ocultar" : "Detalles"}
        </button>
        <div className="flex items-center gap-2">
          <button onClick={() => onDuplicate(item.item_id)} className="flex items-center gap-0.5 text-gray-500 hover:text-gray-700" title="Duplicar">
            <Copy size={12} /> Duplicar
          </button>
          <button onClick={() => onRemove(item.item_id)} className="text-red-500 hover:text-red-600" title="Eliminar">
            <Trash2 size={12} />
          </button>
        </div>
      </div>
      {expanded && (
        <div className="mt-2 pt-2 border-t space-y-2">
          {/* Características */}
          <div>
            <p className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-1"><Tag size={12} /> Caracteristicas</p>
            {item.selected_characteristics?.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1">
                {item.selected_characteristics.map(c => (
                  <span key={c} className="bg-[#63AC9A]/15 text-[#63AC9A] text-[10px] px-1.5 py-0.5 rounded">{c}</span>
                ))}
              </div>
            )}
            <button
              onClick={() => setShowCharsModal(true)}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 border rounded-lg text-xs text-gray-600 hover:bg-gray-50 transition-colors"
              data-testid={`manage-chars-${item.item_id}`}
            >
              <Tag size={12} /> Gestionar Caracteristicas
            </button>
          </div>
          {/* % Descuento */}
          <div>
            <p className="text-xs font-semibold text-gray-600 mb-1">Descuento</p>
            <div className="flex gap-1">
              <Input type="number" step="0.01" value={item.discount_amount} onChange={e => onUpdate(item.item_id, "discount_amount", parseFloat(e.target.value) || 0)} className="h-7 text-xs flex-1" />
              <select value={item.discount_type} onChange={e => onUpdate(item.item_id, "discount_type", e.target.value)} className="border rounded h-7 text-xs px-1">
                <option value="$">$</option>
                <option value="%">%</option>
              </select>
            </div>
          </div>
          {/* Valor adicional */}
          <div>
            <p className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-1"><Plus size={12} /> Valor adicional</p>
            <div className="flex gap-1">
              <Input type="number" step="0.01" value={item.additional_amount} onChange={e => onUpdate(item.item_id, "additional_amount", parseFloat(e.target.value) || 0)} className="h-7 text-xs flex-1" />
              <select value={item.additional_type} onChange={e => onUpdate(item.item_id, "additional_type", e.target.value)} className="border rounded h-7 text-xs px-1">
                <option value="$">$</option>
                <option value="%">%</option>
              </select>
            </div>
          </div>
          {/* Otros */}
          <div>
            <p className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-1"><FileText size={12} /> Otros</p>
            <textarea value={item.otros} onChange={e => onUpdate(item.item_id, "otros", e.target.value)} className="w-full border rounded-lg px-2 py-1.5 text-xs resize-none" rows={2} placeholder="Agregar otros u observaciones..." />
          </div>
        </div>
      )}
      {showCharsModal && (
        <CharacteristicsModal
          categories={item.categories || []}
          selected={item.selected_characteristics || []}
          onSave={(chars) => { onUpdate(item.item_id, "selected_characteristics", chars); setShowCharsModal(false); }}
          onClose={() => setShowCharsModal(false)}
        />
      )}
    </div>
  );
}

function CharacteristicsModal({ categories, selected, onSave, onClose }) {
  const [chars, setChars] = useState([...selected]);
  const [newChar, setNewChar] = useState("");

  const toggle = (cat) => {
    setChars(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]);
  };

  const addNew = () => {
    const val = newChar.trim();
    if (val && !chars.includes(val)) {
      setChars(prev => [...prev, val]);
      setNewChar("");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="characteristics-modal">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-bold text-base">Gestionar Caracteristicas</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-1">Caracteristicas Seleccionadas:</p>
            {chars.length === 0 ? (
              <p className="text-sm text-[#63AC9A] italic">Ninguna categoria seleccionada</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {chars.map(c => (
                  <span key={c} className="bg-[#63AC9A] text-white text-xs px-2 py-0.5 rounded flex items-center gap-1">
                    {c} <button onClick={() => toggle(c)}><X size={10} /></button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-1">Caracteristicas del Inventario:</p>
            <div className="border rounded-lg p-2 max-h-40 overflow-y-auto space-y-1">
              {categories.length === 0 ? (
                <p className="text-xs text-gray-400 italic">Sin categorias en este producto</p>
              ) : categories.map(cat => (
                <label key={cat} className="flex items-center gap-2 cursor-pointer py-1 text-sm">
                  <input type="checkbox" checked={chars.includes(cat)} onChange={() => toggle(cat)} className="rounded border-gray-300" />
                  {cat}
                </label>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-1">Agregar Nueva Caracteristica:</p>
            <div className="flex gap-2">
              <Input value={newChar} onChange={e => setNewChar(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addNew())} placeholder="Nombre de la caracteristica..." className="flex-1" />
              <button onClick={addNew} className="w-9 h-9 bg-gray-800 text-white rounded-lg flex items-center justify-center hover:bg-gray-900 flex-shrink-0">
                <Plus size={16} />
              </button>
            </div>
          </div>
        </div>
        <div className="p-4 pt-0">
          <button onClick={() => onSave(chars)} className="w-full py-2.5 rounded-xl bg-gray-800 hover:bg-gray-900 text-white font-medium text-sm transition-colors" data-testid="save-chars-btn">
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

function ProductDetailModal({ product, index, total, onClose, onAdd, onPrev, onNext, getImageUrl }) {
  const imgSrc = getImageUrl(product.image_url);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="product-detail-modal">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 relative">
        {/* Nav arrows outside */}
        {index > 0 && (
          <button onClick={onPrev} className="absolute left-[-50px] top-1/2 -translate-y-1/2 w-10 h-10 bg-white rounded-full shadow-lg flex items-center justify-center hover:bg-gray-50" data-testid="detail-prev-btn">
            <ChevronLeft size={20} />
          </button>
        )}
        {index < total - 1 && (
          <button onClick={onNext} className="absolute right-[-50px] top-1/2 -translate-y-1/2 w-10 h-10 bg-white rounded-full shadow-lg flex items-center justify-center hover:bg-gray-50" data-testid="detail-next-btn">
            <ChevronRight size={20} />
          </button>
        )}

        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-bold text-lg">Detalles del Producto</h2>
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#63AC9A] font-medium">{index + 1} / {total}</span>
            <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded" data-testid="close-detail-btn"><X size={20} /></button>
          </div>
        </div>

        <div className="p-5">
          <div className="flex gap-4">
            {/* Image */}
            <div className="w-36 h-36 bg-gray-100 rounded-xl flex-shrink-0 overflow-hidden flex items-center justify-center">
              {imgSrc ? (
                <img src={imgSrc} alt="" className="w-full h-full object-cover" onError={e => { e.target.style.display='none'; }} />
              ) : (
                <span className="text-gray-400 text-sm">No Image</span>
              )}
            </div>
            {/* Info */}
            <div className="flex-1 min-w-0">
              <h3 className="font-bold text-base">{product.name}</h3>
              <p className="text-xs text-gray-400 mb-2">Cod: {product.code}</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm border-t pt-2">
                <span className="text-gray-500">Cod. Proveedor</span>
                <span className="text-right">{product.supplier_code || "-"}</span>
                <span className="text-gray-500">PVP</span>
                <span className="text-right font-bold text-[#63AC9A]">{formatCurrency(product.price)}</span>
                <span className="text-gray-500">Costo</span>
                <span className="text-right">{formatCurrency(product.cost)}</span>
                <span className="text-gray-500">Stock</span>
                <span className="text-right">{product.stock || 0}</span>
                <span className="text-gray-500">Proveedor</span>
                <span className="text-right">{product.supplier || "-"}</span>
              </div>
            </div>
          </div>

          {product.description && (
            <p className="text-sm text-gray-600 mt-3 pt-3 border-t">{product.description}</p>
          )}

          {product.categories?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {product.categories.map(c => (
                <span key={c} className="bg-[#63AC9A] text-white text-xs px-2 py-0.5 rounded">{c}</span>
              ))}
            </div>
          )}
        </div>

        <div className="flex gap-3 p-5 pt-0">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl bg-gray-800 hover:bg-gray-900 text-white font-medium text-sm transition-colors">
            Cerrar
          </button>
          <button onClick={() => { onAdd(product); }} className="flex-1 py-2.5 rounded-xl bg-[#63AC9A] hover:bg-[#4F9A87] text-white font-medium text-sm transition-colors flex items-center justify-center gap-1" data-testid="detail-add-btn">
            <Plus size={16} /> Agregar
          </button>
        </div>
      </div>
    </div>
  );
}
