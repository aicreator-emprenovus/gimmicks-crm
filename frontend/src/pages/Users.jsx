import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import {
  Search,
  Plus,
  Users as UsersIcon,
  Edit,
  Trash2,
  Loader2,
  Shield,
  UserCog
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ROLES = [
  { value: "admin", label: "Administrador", description: "Acceso completo a todas las funciones", color: "bg-purple-100 text-purple-700" },
  { value: "asesor", label: "Asesor", description: "Chat y catálogo (solo lectura)", color: "bg-blue-100 text-blue-700" }
];

export default function Users() {
  const { getAuthHeaders } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    name: "",
    role: "asesor"
  });

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/users`, {
        headers: getAuthHeaders()
      });
      setUsers(response.data);
    } catch (error) {
      toast.error("Error al cargar usuarios");
    } finally {
      setLoading(false);
    }
  };

  const createUser = async () => {
    if (!formData.email || !formData.password || !formData.name) {
      toast.error("Todos los campos son requeridos");
      return;
    }
    try {
      await axios.post(`${API_URL}/api/users`, formData, {
        headers: getAuthHeaders()
      });
      toast.success("Usuario creado exitosamente");
      setIsCreateOpen(false);
      resetForm();
      fetchUsers();
    } catch (error) {
      const message = error.response?.data?.detail || "Error al crear usuario";
      toast.error(message);
    }
  };

  const updateUser = async () => {
    if (!editingUser) return;
    try {
      const updateData = {
        name: formData.name,
        role: formData.role
      };
      if (formData.password) {
        updateData.password = formData.password;
      }
      
      await axios.patch(`${API_URL}/api/users/${editingUser.id}`, updateData, {
        headers: getAuthHeaders()
      });
      toast.success("Usuario actualizado");
      setEditingUser(null);
      resetForm();
      fetchUsers();
    } catch (error) {
      toast.error("Error al actualizar usuario");
    }
  };

  const deleteUser = async (userId) => {
    if (!confirm("¿Eliminar este usuario? Esta acción no se puede deshacer.")) return;
    try {
      await axios.delete(`${API_URL}/api/users/${userId}`, {
        headers: getAuthHeaders()
      });
      toast.success("Usuario eliminado");
      fetchUsers();
    } catch (error) {
      const message = error.response?.data?.detail || "Error al eliminar usuario";
      toast.error(message);
    }
  };

  const resetForm = () => {
    setFormData({
      email: "",
      password: "",
      name: "",
      role: "asesor"
    });
  };

  const openEditDialog = (user) => {
    setEditingUser(user);
    setFormData({
      email: user.email,
      password: "",
      name: user.name,
      role: user.role
    });
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = users.filter(
    (user) =>
      user.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getRoleInfo = (role) => {
    return ROLES.find(r => r.value === role) || ROLES[1];
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return format(new Date(dateStr), "dd/MM/yy HH:mm", { locale: es });
    } catch {
      return "-";
    }
  };

  return (
    <div className="p-6 space-y-6" data-testid="users-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 font-['Manrope']">
            Gestión de Usuarios
          </h1>
          <p className="text-zinc-500 text-sm">
            Administra los accesos al sistema
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button
              className="bg-emerald-500 hover:bg-emerald-600 gap-2"
              data-testid="create-user-btn"
            >
              <Plus size={18} />
              Nuevo Usuario
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="font-['Manrope']">Crear Nuevo Usuario</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Nombre Completo *</Label>
                <Input
                  placeholder="Juan Pérez"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  data-testid="user-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Email *</Label>
                <Input
                  type="email"
                  placeholder="correo@gimmicks.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  data-testid="user-email-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Contraseña *</Label>
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  data-testid="user-password-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Rol</Label>
                <Select
                  value={formData.role}
                  onValueChange={(v) => setFormData({ ...formData, role: v })}
                >
                  <SelectTrigger data-testid="user-role-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map(role => (
                      <SelectItem key={role.value} value={role.value}>
                        <div className="flex items-center gap-2">
                          {role.value === "admin" ? <Shield className="w-4 h-4" /> : <UserCog className="w-4 h-4" />}
                          <div>
                            <p className="font-medium">{role.label}</p>
                            <p className="text-xs text-zinc-500">{role.description}</p>
                          </div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                onClick={createUser}
                className="w-full bg-emerald-500 hover:bg-emerald-600"
                data-testid="submit-user-btn"
              >
                Crear Usuario
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
        <Input
          placeholder="Buscar por nombre o email..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-9"
          data-testid="search-users-input"
        />
      </div>

      {/* Users Table */}
      <Card className="border border-zinc-100">
        <CardHeader className="border-b border-zinc-100">
          <CardTitle className="flex items-center gap-2 font-['Manrope']">
            <UsersIcon className="w-5 h-5" />
            Usuarios del Sistema
            <Badge variant="secondary" className="ml-2">
              {filteredUsers.length} usuarios
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-12 text-zinc-400">
              <UsersIcon className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">No hay usuarios</p>
              <p className="text-sm mt-1">Crea el primer usuario del sistema</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-zinc-50">
                  <TableHead>Usuario</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Rol</TableHead>
                  <TableHead>Creado</TableHead>
                  <TableHead className="w-24">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.map((user) => (
                  <TableRow key={user.id} data-testid={`user-row-${user.id}`}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center text-white font-medium">
                          {user.name?.charAt(0)?.toUpperCase() || "?"}
                        </div>
                        <span className="font-medium text-zinc-900">{user.name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-zinc-600">{user.email}</TableCell>
                    <TableCell>
                      <Badge className={getRoleInfo(user.role).color}>
                        {user.role === "admin" && <Shield className="w-3 h-3 mr-1" />}
                        {getRoleInfo(user.role).label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-zinc-500 text-sm">
                      {formatDate(user.created_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0"
                          onClick={() => openEditDialog(user)}
                          data-testid={`edit-user-${user.id}`}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                          onClick={() => deleteUser(user.id)}
                          data-testid={`delete-user-${user.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={!!editingUser} onOpenChange={(open) => !open && setEditingUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Manrope']">Editar Usuario</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                value={formData.email}
                disabled
                className="bg-zinc-50"
              />
            </div>
            <div className="space-y-2">
              <Label>Nombre Completo</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                data-testid="edit-user-name"
              />
            </div>
            <div className="space-y-2">
              <Label>Nueva Contraseña (dejar vacío para mantener)</Label>
              <Input
                type="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                data-testid="edit-user-password"
              />
            </div>
            <div className="space-y-2">
              <Label>Rol</Label>
              <Select
                value={formData.role}
                onValueChange={(v) => setFormData({ ...formData, role: v })}
              >
                <SelectTrigger data-testid="edit-user-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map(role => (
                    <SelectItem key={role.value} value={role.value}>
                      {role.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              onClick={updateUser}
              className="w-full bg-emerald-500 hover:bg-emerald-600"
              data-testid="save-user-btn"
            >
              Guardar Cambios
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
