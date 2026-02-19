import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { Loader2, Search, Package, Copy, Check } from "lucide-react";

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
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
        copied
          ? "bg-emerald-100 text-emerald-700 border border-emerald-300"
          : "bg-zinc-100 text-zinc-600 hover:bg-[#63AC9A]/10 hover:text-[#63AC9A] border border-zinc-200"
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
  const [searchInput, setSearchInput] = useState(searchParams.get("q") || "");
  const query = searchParams.get("q") || "";

  const fetchProducts = async (q) => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/catalog/public`, { params: { q, limit: 40 } });
      setProducts(res.data);
    } catch {
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (query) fetchProducts(query);
    else setLoading(false);
  }, [query]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSearchParams({ q: searchInput.trim() });
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-[#1a2332] text-white py-4 px-4 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto flex items-center">
          <img src={LOGO_URL} alt="Gimmicks" className="h-10 object-contain" />
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Search */}
        <form onSubmit={handleSearch} className="mb-6">
          <div className="relative max-w-md mx-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Buscar productos..."
              className="w-full pl-10 pr-4 py-3 border border-zinc-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#63AC9A] focus:border-transparent"
              data-testid="catalog-search"
            />
          </div>
        </form>

        {query && (
          <p className="text-zinc-500 text-sm mb-4 text-center" data-testid="catalog-results-info">
            {loading ? "Buscando..." : `${products.length} producto(s) para "${query}"`}
          </p>
        )}

        {/* Products Grid */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-[#63AC9A]" />
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-16 text-zinc-400">
            <Package className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-lg">{query ? "No se encontraron productos" : "Busca un producto para ver opciones"}</p>
            {query && <p className="text-sm mt-1">Intenta con otra palabra clave</p>}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4" data-testid="catalog-grid">
            {products.map((product) => (
              <div
                key={product.code}
                className="bg-white border border-zinc-100 rounded-xl overflow-hidden hover:shadow-lg transition-shadow"
                data-testid={`catalog-product-${product.code}`}
              >
                <div className="aspect-square bg-zinc-50 relative overflow-hidden flex items-center justify-center">
                  {product.image_url && product.image_url !== "N/A" ? (
                    <img
                      src={fixDriveUrl(product.image_url)}
                      alt={product.name}
                      className="w-full h-full object-contain p-2"
                      loading="lazy"
                      onError={(e) => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }}
                    />
                  ) : null}
                  <div className={`${product.image_url && product.image_url !== "N/A" ? "hidden" : "flex"} items-center justify-center w-full h-full`}>
                    <Package className="w-12 h-12 text-zinc-300" />
                  </div>
                </div>
                <div className="p-3">
                  <p className="font-medium text-zinc-900 text-sm leading-tight line-clamp-2" data-testid={`product-name-${product.code}`}>
                    {product.name}
                  </p>
                  {product.description && (
                    <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{product.description}</p>
                  )}
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <div className="inline-block bg-[#63AC9A]/10 text-[#63AC9A] px-2 py-1 rounded-md">
                      <span className="text-xs font-bold font-mono" data-testid={`product-code-${product.code}`}>
                        {product.code}
                      </span>
                    </div>
                    <CopyCodeButton code={product.code} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer note */}
        {products.length > 0 && (
          <div className="text-center mt-8 py-4 border-t border-zinc-100">
            <p className="text-sm text-zinc-500">
              Comparte los códigos de los productos que te interesen con tu asesor por WhatsApp
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
