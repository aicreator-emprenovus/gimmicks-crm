import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { Loader2, Search, Package, Copy, Check, FilterX } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;
const LOGO_URL = "https://customer-assets.emergentagent.com/job_quote-crafter-1/artifacts/ee7e6zy2_logo-gimmicks.png";

function fixDriveUrl(url) {
  if (!url) return url;
  let m = url.match(/drive\.google\.com\/file\/d\/([^/]+)/);
  if (m) return `https://lh3.googleusercontent.com/d/${m[1]}`;
  m = url.match(/drive\.google\.com\/open\?id=([^&]+)/);
  if (m) return `https://lh3.googleusercontent.com/d/${m[1]}`;
  m = url.match(/drive\.google\.com\/uc\?.*id=([^&]+)/);
  if (m) return `https://lh3.googleusercontent.com/d/${m[1]}`;
  return url;
}

function CopyCodeButton({ code }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button
      onClick={handleCopy}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
        copied
          ? "bg-emerald-600 text-white"
          : "bg-gray-800 text-white hover:bg-gray-900"
      }`}
      data-testid={`copy-code-${code}`}
    >
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "Copiado" : "Copiar código"}
    </button>
  );
}

export default function PublicCatalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [searchInput, setSearchInput] = useState(searchParams.get("q") || "");
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get("cat") || "");
  const query = searchParams.get("q") || "";
  const catParam = searchParams.get("cat") || "";

  useEffect(() => {
    axios.get(`${API_URL}/api/catalog/public/categories`).then(res => setCategories(res.data || [])).catch(() => {});
  }, []);

  const fetchProducts = async (q, cat) => {
    setLoading(true);
    try {
      const params = { limit: 40 };
      if (q) params.q = q;
      if (cat) params.category = cat;
      const res = await axios.get(`${API_URL}/api/catalog/public`, { params });
      setProducts(res.data);
    } catch {
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (query || catParam) fetchProducts(query, catParam);
    else setLoading(false);
  }, [query, catParam]);

  const handleSearch = (e) => {
    e.preventDefault();
    const params = {};
    if (searchInput.trim()) params.q = searchInput.trim();
    if (selectedCategory) params.cat = selectedCategory;
    setSearchParams(params);
  };

  const handleCategoryChange = (cat) => {
    setSelectedCategory(cat);
    const params = {};
    if (searchInput.trim()) params.q = searchInput.trim();
    if (cat) params.cat = cat;
    setSearchParams(params);
  };

  const clearFilters = () => {
    setSearchInput("");
    setSelectedCategory("");
    setSearchParams({});
    setProducts([]);
  };

  const hasFilters = query || catParam;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-[#1a2332] text-white py-4 px-4 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto flex items-center">
          <img src={LOGO_URL} alt="Gimmicks" className="h-10 object-contain" />
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Search + Category Filters */}
        <div className="bg-white rounded-xl shadow-sm border p-4 mb-5">
          <form onSubmit={handleSearch} className="flex gap-2 mb-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Buscar productos..."
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#63AC9A] focus:border-transparent"
                data-testid="catalog-search"
              />
            </div>
            <button type="submit" className="px-5 py-2.5 bg-[#63AC9A] hover:bg-[#4F9A87] text-white rounded-lg text-sm font-semibold transition-colors">
              Buscar
            </button>
          </form>
          {/* Category chips */}
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-sm font-semibold text-gray-600">Categorias:</span>
            <button
              onClick={() => handleCategoryChange("")}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                !selectedCategory ? "bg-[#63AC9A] text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Todas
            </button>
            {categories.slice(0, 20).map(cat => (
              <button
                key={cat}
                onClick={() => handleCategoryChange(cat)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  selectedCategory === cat ? "bg-[#63AC9A] text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
                data-testid={`cat-filter-${cat}`}
              >
                {cat}
              </button>
            ))}
            {hasFilters && (
              <button onClick={clearFilters} className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-500 ml-2">
                <FilterX size={14} /> Limpiar
              </button>
            )}
          </div>
        </div>

        {hasFilters && (
          <p className="text-gray-600 text-sm mb-4 text-center font-medium" data-testid="catalog-results-info">
            {loading ? "Buscando..." : `${products.length} producto(s) encontrado(s)${query ? ` para "${query}"` : ""}${catParam ? ` en ${catParam}` : ""}`}
          </p>
        )}

        {/* Products Grid */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-[#63AC9A]" />
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Package className="w-16 h-16 mx-auto mb-4 opacity-40" />
            <p className="text-lg font-medium">{hasFilters ? "No se encontraron productos" : "Busca un producto o selecciona una categoria"}</p>
            {hasFilters && <p className="text-sm mt-1 text-gray-500">Intenta con otra palabra clave o categoria</p>}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4" data-testid="catalog-grid">
            {products.map((product) => (
              <div
                key={product.code}
                className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow"
                data-testid={`catalog-product-${product.code}`}
              >
                <div className="aspect-square bg-gray-100 relative overflow-hidden flex items-center justify-center">
                  {product.image_url && product.image_url !== "N/A" ? (
                    <img
                      src={fixDriveUrl(product.image_url)}
                      alt={product.name}
                      className="w-full h-full object-contain p-2"
                      loading="lazy"
                      onError={(e) => { e.target.style.display = "none"; if(e.target.nextSibling) e.target.nextSibling.style.display = "flex"; }}
                    />
                  ) : null}
                  <div className={`${product.image_url && product.image_url !== "N/A" ? "hidden" : "flex"} items-center justify-center w-full h-full text-gray-400`}>
                    <span className="text-sm">Sin imagen</span>
                  </div>
                </div>
                <div className="p-3">
                  <p className="font-semibold text-gray-900 text-sm leading-tight line-clamp-2" data-testid={`product-name-${product.code}`}>
                    {product.name}
                  </p>
                  {product.description && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{product.description}</p>
                  )}
                  <div className="mt-2 flex items-center justify-between gap-2 flex-wrap">
                    <span className="inline-block bg-[#63AC9A]/15 text-[#63AC9A] px-2 py-1 rounded-md text-xs font-bold font-mono" data-testid={`product-code-${product.code}`}>
                      {product.code}
                    </span>
                    <CopyCodeButton code={product.code} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer note */}
        {products.length > 0 && (
          <div className="text-center mt-8 py-4 border-t border-gray-200">
            <p className="text-sm text-gray-600 font-medium">
              Comparte los codigos de los productos que te interesen con tu asesor por WhatsApp
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
