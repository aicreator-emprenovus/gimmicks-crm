import { useEffect, useState, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Search,
  Upload,
  Plus,
  Package,
  Loader2,
  Trash2,
  Image,
  FileSpreadsheet,
  CheckCircle,
  AlertCircle
} from "lucide-react";
import { toast } from "sonner";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Inventory() {
  const { getAuthHeaders } = useAuth();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);
  const [formData, setFormData] = useState({
    code: "",
    name: "",
    description: "",
    category_1: "",
    category_2: "",
    category_3: "",
    price: "",
    stock: 0,
    image_url: ""
  });

  const fetchProducts = async () => {
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append("search", searchTerm);

      const response = await axios.get(`${API_URL}/api/products?${params}`, {
        headers: getAuthHeaders()
      });
      setProducts(response.data);
    } catch (error) {
      toast.error("Error al cargar productos");
    } finally {
      setLoading(false);
    }
  };

  const createProduct = async () => {
    try {
      const payload = {
        ...formData,
        price: formData.price ? parseFloat(formData.price) : null,
        stock: parseInt(formData.stock) || 0
      };
      await axios.post(`${API_URL}/api/products`, payload, {
        headers: getAuthHeaders()
      });
      toast.success("Producto creado");
      setIsCreateOpen(false);
      resetForm();
      fetchProducts();
    } catch (error) {
      toast.error("Error al crear producto");
    }
  };

  const deleteProduct = async (productId) => {
    if (!confirm("¿Eliminar este producto?")) return;
    try {
      await axios.delete(`${API_URL}/api/products/${productId}`, {
        headers: getAuthHeaders()
      });
      toast.success("Producto eliminado");
      fetchProducts();
    } catch (error) {
      toast.error("Error al eliminar producto");
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error("El archivo debe ser Excel (.xlsx o .xls)");
      return;
    }

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API_URL}/api/products/upload`, formData, {
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "multipart/form-data"
        }
      });
      setUploadResult(response.data);
      toast.success("Productos cargados exitosamente");
      fetchProducts();
    } catch (error) {
      const message = error.response?.data?.detail || "Error al cargar archivo";
      toast.error(message);
      setUploadResult({ error: message });
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const resetForm = () => {
    setFormData({
      code: "",
      name: "",
      description: "",
      category_1: "",
      category_2: "",
      category_3: "",
      price: "",
      stock: 0,
      image_url: ""
    });
  };

  useEffect(() => {
    fetchProducts();
  }, [searchTerm]);

  return (
    <div className="p-6 space-y-6" data-testid="inventory-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 font-['Manrope']">
            Inventario
          </h1>
          <p className="text-zinc-500 text-sm">
            Gestiona tu catálogo de productos
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="file"
            ref={fileInputRef}
            accept=".xlsx,.xls"
            onChange={handleFileUpload}
            className="hidden"
            data-testid="file-upload-input"
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="gap-2"
            data-testid="upload-excel-btn"
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload size={18} />
            )}
            Cargar Excel
          </Button>
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button
                className="bg-emerald-500 hover:bg-emerald-600 gap-2"
                data-testid="add-product-btn"
              >
                <Plus size={18} />
                Nuevo Producto
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle className="font-['Manrope']">Crear Producto</DialogTitle>
              </DialogHeader>
              <ScrollArea className="max-h-[60vh]">
                <div className="space-y-4 mt-4 pr-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Código *</Label>
                      <Input
                        placeholder="SKU-001"
                        value={formData.code}
                        onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                        data-testid="product-code-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Stock</Label>
                      <Input
                        type="number"
                        value={formData.stock}
                        onChange={(e) => setFormData({ ...formData, stock: e.target.value })}
                        data-testid="product-stock-input"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Nombre *</Label>
                    <Input
                      placeholder="Nombre del producto"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      data-testid="product-name-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Descripción</Label>
                    <Textarea
                      placeholder="Descripción del producto..."
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      data-testid="product-desc-input"
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Categoría 1</Label>
                      <Input
                        placeholder="Tipo"
                        value={formData.category_1}
                        onChange={(e) => setFormData({ ...formData, category_1: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Categoría 2</Label>
                      <Input
                        placeholder="Material"
                        value={formData.category_2}
                        onChange={(e) => setFormData({ ...formData, category_2: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Categoría 3</Label>
                      <Input
                        placeholder="Uso"
                        value={formData.category_3}
                        onChange={(e) => setFormData({ ...formData, category_3: e.target.value })}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Precio</Label>
                      <Input
                        type="number"
                        step="0.01"
                        placeholder="0.00"
                        value={formData.price}
                        onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                        data-testid="product-price-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>URL Imagen</Label>
                      <Input
                        placeholder="https://..."
                        value={formData.image_url}
                        onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                      />
                    </div>
                  </div>
                  <Button
                    onClick={createProduct}
                    className="w-full bg-emerald-500 hover:bg-emerald-600"
                    data-testid="submit-product-btn"
                  >
                    Crear Producto
                  </Button>
                </div>
              </ScrollArea>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Upload Result */}
      {uploadResult && (
        <Card className={`border ${uploadResult.error ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'}`}>
          <CardContent className="p-4 flex items-center gap-3">
            {uploadResult.error ? (
              <>
                <AlertCircle className="w-5 h-5 text-red-500" />
                <p className="text-red-700">{uploadResult.error}</p>
              </>
            ) : (
              <>
                <CheckCircle className="w-5 h-5 text-emerald-500" />
                <p className="text-emerald-700">
                  {uploadResult.message} - {uploadResult.created} creados, {uploadResult.updated} actualizados
                </p>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
        <Input
          placeholder="Buscar por código, nombre o descripción..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-9"
          data-testid="search-products-input"
        />
      </div>

      {/* Products Table */}
      <Card className="border border-zinc-100">
        <CardHeader className="border-b border-zinc-100">
          <CardTitle className="flex items-center gap-2 font-['Manrope']">
            <Package className="w-5 h-5" />
            Catálogo de Productos
            <Badge variant="secondary" className="ml-2">
              {products.length} productos
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-12 text-zinc-400">
              <FileSpreadsheet className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">No hay productos</p>
              <p className="text-sm mt-1">
                Carga un archivo Excel con tu catálogo
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow className="bg-zinc-50">
                    <TableHead className="w-16">Imagen</TableHead>
                    <TableHead>Código</TableHead>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Categoría</TableHead>
                    <TableHead className="text-right">Precio</TableHead>
                    <TableHead className="text-right">Stock</TableHead>
                    <TableHead className="w-16"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {products.map((product) => (
                    <TableRow key={product.id} data-testid={`product-row-${product.id}`}>
                      <TableCell>
                        {product.image_url ? (
                          <img
                            src={product.image_url}
                            alt={product.name}
                            className="w-10 h-10 object-cover rounded-lg"
                            onError={(e) => {
                              e.target.onerror = null;
                              e.target.src = "https://via.placeholder.com/40";
                            }}
                          />
                        ) : (
                          <div className="w-10 h-10 bg-zinc-100 rounded-lg flex items-center justify-center">
                            <Image className="w-4 h-4 text-zinc-400" />
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {product.code}
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium text-zinc-900">{product.name}</p>
                          {product.description && (
                            <p className="text-xs text-zinc-500 truncate max-w-[200px]">
                              {product.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {product.category_1 && (
                            <Badge variant="outline" className="text-xs">
                              {product.category_1}
                            </Badge>
                          )}
                          {product.category_2 && (
                            <Badge variant="outline" className="text-xs">
                              {product.category_2}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        {product.price ? `$${product.price.toFixed(2)}` : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge
                          variant={product.stock > 0 ? "default" : "destructive"}
                          className={product.stock > 0 ? "bg-emerald-100 text-emerald-700" : ""}
                        >
                          {product.stock}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                          onClick={() => deleteProduct(product.id)}
                          data-testid={`delete-product-${product.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
