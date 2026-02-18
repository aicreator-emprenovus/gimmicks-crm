import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { formatCurrency } from "@/utils/currency";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft, Plus, Trash2, Search, ShoppingCart, FileText,
  X, Loader2, Save, Send, Minus, ChevronDown, ChevronUp
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function QuoteBuilder() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editId = searchParams.get("edit");
  const docType = searchParams.get("type") || "QUOTE";
  const [clients, setClients] = useState([]);
  const [products, setProducts] = useState([]);
  const [productSearch, setProductSearch] = useState("");
  const [clientSearch, setClientSearch] = useState("");
  const [showProductPicker, setShowProductPicker] = useState(false);
  const [cart, setCart] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientContact, setClientContact] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [paymentTerms, setPaymentTerms] = useState("50% anticipo, 50% contra entrega");
  const [validity, setValidity] = useState("8 días");
  const [deliveryTime, setDeliveryTime] = useState("Por confirmar");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };
  const isEdit = !!editId;

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
      setValidity(q.validity || "8 días");
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

  const searchProducts = useCallback(async () => {
    try {
      const params = { page: 1, limit: 50 };
      if (productSearch) params.search = productSearch;
      if (selectedCategory && selectedCategory !== "Todas") params.category = selectedCategory;
      const res = await axios.get(`${API_URL}/api/inventory/`, { params, headers });
      setProducts(res.data.products || []);
    } catch {}
  }, [productSearch, selectedCategory]);

  useEffect(() => {
    if (showProductPicker) searchProducts();
  }, [showProductPicker, searchProducts]);

  const addToCart = (product) => {
    const exists = cart.find(i => i.code === product.code);
    if (exists) {
      setCart(cart.map(i => i.code === product.code ? { ...i, quantity: i.quantity + 1, total_price: (i.quantity + 1) * i.unit_price } : i));
    } else {
      setCart([...cart, {
        item_id: `item-${Date.now()}`,
        product_id: product.id || "",
        code: product.code,
        name: product.name,
        description: product.description || "",
        quantity: 1,
        unit_price: product.price || 0,
        total_price: product.price || 0,
        image_url: product.image_url || "",
        categories: product.categories || [],
        discount_amount: 0,
        discount_type: "$",
        additional_amount: 0,
        additional_type: "$",
        otros: ""
      }]);
    }
    toast.success(`${product.name} agregado`);
  };

  const updateCartItem = (itemId, field, value) => {
    setCart(cart.map(i => {
      if (i.item_id !== itemId) return i;
      const updated = { ...i, [field]: value };
      // Recalculate total
      let base = updated.quantity * updated.unit_price;
      if (updated.discount_amount > 0) {
        if (updated.discount_type === "%") base -= base * (updated.discount_amount / 100);
        else base -= updated.discount_amount * updated.quantity;
      }
      if (updated.additional_amount > 0) {
        if (updated.additional_type === "%") base += base * (updated.additional_amount / 100);
        else base += updated.additional_amount * updated.quantity;
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
        toast.success("Cotización actualizada");
      } else {
        await axios.post(`${API_URL}/api/quotes-v2/`, quoteData, { headers });
        toast.success("Cotización creada");
      }
      navigate("/quotes");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error al guardar");
    }
    setSaving(false);
  };

  const getImageUrl = (url) => {
    if (!url) return null;
    if (url.startsWith("/api/uploads/")) return `${API_URL}${url}`;
    const driveMatch = url.match(/drive\.google\.com\/file\/d\/([^/\?]+)/);
    if (driveMatch) return `https://drive.google.com/thumbnail?id=${driveMatch[1]}&sz=w100`;
    return url;
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 size={32} className="animate-spin text-gray-400" /></div>;
  }

  return (
    <div className="p-4 lg:p-6" data-testid="quote-builder-page">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" size="sm" onClick={() => navigate("/quotes")} data-testid="back-btn">
          <ArrowLeft size={18} />
        </Button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {isEdit ? "Editar" : "Nueva"} {docType === "PO" ? "Orden de Compra" : "Cotización"}
          </h1>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Client + Products */}
        <div className="lg:col-span-2 space-y-4">
          {/* Client Selection */}
          <div className="bg-white rounded-xl shadow-sm border p-4" data-testid="client-section">
            <h3 className="font-semibold text-sm text-gray-700 mb-3">Cliente</h3>
            {selectedClient ? (
              <div className="flex items-center justify-between bg-[#7BA899]/5 rounded-lg p-3">
                <div>
                  <p className="font-medium">{selectedClient.name}</p>
                  <p className="text-xs text-gray-500">{selectedClient.email}</p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setSelectedClient(null)}><X size={16} /></Button>
              </div>
            ) : (
              <div>
                <Input
                  placeholder="Buscar cliente..."
                  value={clientSearch}
                  onChange={(e) => setClientSearch(e.target.value)}
                  data-testid="client-search-input"
                />
                {clientSearch && (
                  <div className="mt-1 border rounded-lg max-h-40 overflow-y-auto bg-white shadow-lg">
                    {clients.filter(c => c.name?.toLowerCase().includes(clientSearch.toLowerCase()) || c.email?.toLowerCase().includes(clientSearch.toLowerCase())).map(c => (
                      <button key={c.id} className="w-full text-left px-3 py-2 hover:bg-gray-50 text-sm border-b last:border-0" onClick={() => {
                        setSelectedClient(c);
                        setClientEmail(c.email || c.commercial_email || "");
                        setClientContact(c.contact_person || "");
                        setClientSearch("");
                      }} data-testid={`client-option-${c.id}`}>
                        <span className="font-medium">{c.name}</span>
                        <span className="text-gray-400 ml-2 text-xs">{c.email}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {selectedClient && (
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div>
                  <label className="text-xs text-gray-500">Contacto</label>
                  <Input value={clientContact} onChange={e => setClientContact(e.target.value)} placeholder="Persona de contacto" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Email para envío</label>
                  <Input value={clientEmail} onChange={e => setClientEmail(e.target.value)} placeholder="Email" />
                </div>
              </div>
            )}
          </div>

          {/* Cart Items */}
          <div className="bg-white rounded-xl shadow-sm border p-4" data-testid="cart-section">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm text-gray-700 flex items-center gap-1">
                <ShoppingCart size={16} /> Productos ({cart.length})
              </h3>
              <Button size="sm" variant="outline" onClick={() => setShowProductPicker(true)} data-testid="add-product-to-cart-btn">
                <Plus size={14} className="mr-1" /> Agregar Producto
              </Button>
            </div>
            {cart.length === 0 ? (
              <p className="text-center text-gray-400 py-8 text-sm">Agregue productos a la cotización</p>
            ) : (
              <div className="space-y-3">
                {cart.map(item => (
                  <CartItem key={item.item_id} item={item} onUpdate={updateCartItem} onRemove={removeFromCart} getImageUrl={getImageUrl} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Summary */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border p-4 sticky top-4" data-testid="summary-section">
            <h3 className="font-semibold text-sm text-gray-700 mb-3">Resumen</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>{formatCurrency(subtotal)}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">IVA (15%)</span><span>{formatCurrency(tax)}</span></div>
              <div className="flex justify-between font-bold text-lg border-t pt-2"><span>Total</span><span className="text-[#7BA899]">{formatCurrency(total)}</span></div>
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Forma de pago</label>
                <Input value={paymentTerms} onChange={e => setPaymentTerms(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Validez</label>
                <Input value={validity} onChange={e => setValidity(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Tiempo de entrega</label>
                <Input value={deliveryTime} onChange={e => setDeliveryTime(e.target.value)} />
              </div>
            </div>
            <div className="mt-4 space-y-2">
              <Button className="w-full bg-[#7BA899] hover:bg-[#5E8A7A]" onClick={() => handleSave("draft")} disabled={saving} data-testid="save-quote-btn">
                {saving ? <Loader2 size={16} className="animate-spin mr-1" /> : <Save size={16} className="mr-1" />}
                Guardar Borrador
              </Button>
              <Button variant="outline" className="w-full" onClick={() => handleSave("sent")} disabled={saving} data-testid="save-and-send-btn">
                <Send size={16} className="mr-1" /> Guardar y Finalizar
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Product Picker Modal */}
      {showProductPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="product-picker-modal">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="font-bold">Seleccionar Productos</h2>
              <button onClick={() => setShowProductPicker(false)} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
            </div>
            <div className="p-4 flex gap-2">
              <div className="relative flex-1">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <Input
                  placeholder="Buscar productos..."
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  className="pl-9"
                  data-testid="product-search-modal-input"
                />
              </div>
              <select value={selectedCategory} onChange={e => setSelectedCategory(e.target.value)} className="border rounded-lg px-2 text-sm">
                <option value="">Todas</option>
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="overflow-y-auto flex-1 p-4 pt-0">
              {products.length === 0 ? (
                <p className="text-center text-gray-400 py-8">No se encontraron productos</p>
              ) : (
                <div className="space-y-2">
                  {products.map(p => (
                    <div key={p.code} className="flex items-center gap-3 p-3 rounded-lg border hover:bg-gray-50 cursor-pointer" onClick={() => addToCart(p)} data-testid={`pick-product-${p.code}`}>
                      {p.image_url ? (
                        <img src={getImageUrl(p.image_url)} alt="" className="w-10 h-10 rounded object-cover" onError={e => { e.target.style.display = 'none'; }} />
                      ) : (
                        <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center text-gray-300"><FileText size={16} /></div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{p.name}</p>
                        <p className="text-xs text-gray-400">{p.code}</p>
                      </div>
                      <span className="text-sm font-medium text-green-700">{formatCurrency(p.price)}</span>
                      <Button size="sm" variant="ghost" className="text-[#7BA899]"><Plus size={16} /></Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CartItem({ item, onUpdate, onRemove, getImageUrl }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border rounded-lg p-3" data-testid={`cart-item-${item.code}`}>
      <div className="flex items-center gap-3">
        {item.image_url ? (
          <img src={getImageUrl(item.image_url)} alt="" className="w-12 h-12 rounded object-cover" onError={e => { e.target.style.display = 'none'; }} />
        ) : (
          <div className="w-12 h-12 rounded bg-gray-100 flex items-center justify-center text-gray-300"><FileText size={16} /></div>
        )}
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{item.name}</p>
          <p className="text-xs text-gray-400">{item.code}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => onUpdate(item.item_id, "quantity", Math.max(1, item.quantity - 1))}><Minus size={14} /></Button>
          <Input type="number" value={item.quantity} onChange={e => onUpdate(item.item_id, "quantity", Math.max(1, parseInt(e.target.value) || 1))} className="w-14 text-center h-7 text-sm" />
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => onUpdate(item.item_id, "quantity", item.quantity + 1)}><Plus size={14} /></Button>
        </div>
        <div className="text-right min-w-[80px]">
          <p className="font-medium text-sm">{formatCurrency(item.total_price)}</p>
          <p className="text-xs text-gray-400">{formatCurrency(item.unit_price)} c/u</p>
        </div>
        <div className="flex gap-1">
          <button onClick={() => setExpanded(!expanded)} className="p-1 hover:bg-gray-100 rounded text-gray-400">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          <button onClick={() => onRemove(item.item_id)} className="p-1 hover:bg-gray-100 rounded text-red-400"><Trash2 size={14} /></button>
        </div>
      </div>
      {expanded && (
        <div className="mt-3 pt-3 border-t grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500">Precio unitario</label>
            <Input type="number" step="0.01" value={item.unit_price} onChange={e => onUpdate(item.item_id, "unit_price", parseFloat(e.target.value) || 0)} className="h-8 text-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Descuento</label>
            <div className="flex gap-1">
              <Input type="number" step="0.01" value={item.discount_amount} onChange={e => onUpdate(item.item_id, "discount_amount", parseFloat(e.target.value) || 0)} className="h-8 text-sm flex-1" />
              <select value={item.discount_type} onChange={e => onUpdate(item.item_id, "discount_type", e.target.value)} className="border rounded h-8 text-xs px-1">
                <option value="$">$</option>
                <option value="%">%</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500">Valor adicional</label>
            <div className="flex gap-1">
              <Input type="number" step="0.01" value={item.additional_amount} onChange={e => onUpdate(item.item_id, "additional_amount", parseFloat(e.target.value) || 0)} className="h-8 text-sm flex-1" />
              <select value={item.additional_type} onChange={e => onUpdate(item.item_id, "additional_type", e.target.value)} className="border rounded h-8 text-xs px-1">
                <option value="$">$</option>
                <option value="%">%</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500">Otros (descripción)</label>
            <Input value={item.otros} onChange={e => onUpdate(item.item_id, "otros", e.target.value)} className="h-8 text-sm" placeholder="Ej: Personalización" />
          </div>
        </div>
      )}
    </div>
  );
}
