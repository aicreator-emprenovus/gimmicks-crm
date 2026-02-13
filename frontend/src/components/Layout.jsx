import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Package,
  Settings,
  LogOut,
  Menu,
  X,
  UserCog,
  FileText,
  ShoppingCart,
  Users2,
  FilePlus,
  ClipboardList
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard", roles: ["admin", "asesor"] },
  { to: "/inbox", icon: MessageSquare, label: "Inbox", roles: ["admin", "asesor"] },
  { to: "/users", icon: Users, label: "Usuarios", roles: ["admin"] },
  { to: "/inventory", icon: Package, label: "Inventario", roles: ["admin", "asesor"] },
  { to: "/leads", icon: Users2, label: "Clientes", roles: ["admin", "asesor"] },
  { to: "/quotes", icon: FileText, label: "Cotizaciones", roles: ["admin", "asesor"] },
  { to: "/orders", icon: ShoppingCart, label: "Órdenes de Compra", roles: ["admin"] },
  { to: "/settings", icon: Settings, label: "Configuración", roles: ["admin"] },
];

const quickActions = [
  { to: "/quotes/new", icon: FilePlus, label: "Nueva Cotización" },
  { to: "/orders/new", icon: ClipboardList, label: "Nueva Orden" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // Filter nav items based on user role
  const filteredNavItems = navItems.filter(item => 
    item.roles.includes(user?.role || "asesor")
  );

  const isAdmin = user?.role === "admin";

  return (
    <div className="min-h-screen bg-[#1a1a1d] flex">
      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-[#2d2d30] rounded-lg text-white"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        data-testid="mobile-menu-btn"
      >
        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-72 bg-[#1a1a1d] border-r border-[#2d2d30] transform transition-transform duration-200 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-[#2d2d30]">
            <img
              src="https://customer-assets.emergentagent.com/job_quote-crafter-1/artifacts/ee7e6zy2_logo-gimmicks.png"
              alt="Gimmicks"
              className="h-12 mx-auto"
              data-testid="sidebar-logo"
            />
            <p className="text-center text-[#6b6b6b] text-xs mt-1 tracking-wider">MARKETING SERVICES</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 py-6 overflow-y-auto">
            <ul className="space-y-1 px-4">
              {filteredNavItems.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    onClick={() => setSidebarOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-200 group ${
                        isActive
                          ? "bg-gradient-to-r from-[#2d2d30] to-[#3d3d40] text-white border-l-4 border-emerald-400"
                          : "text-[#8a8a8a] hover:text-white hover:bg-[#2d2d30]/50"
                      }`
                    }
                    data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                  >
                    <item.icon size={20} className="flex-shrink-0" />
                    <span className="font-medium text-sm">{item.label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>

            {/* Quick Actions */}
            {isAdmin && (
              <div className="mt-8 px-4 space-y-2">
                {quickActions.map((action) => (
                  <NavLink
                    key={action.to}
                    to={action.to}
                    onClick={() => setSidebarOpen(false)}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white font-medium text-sm hover:from-emerald-600 hover:to-emerald-700 transition-all duration-200 shadow-lg shadow-emerald-500/20"
                  >
                    <action.icon size={18} />
                    <span>{action.label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-[#2d2d30]">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-[#2d2d30]/50">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-white font-bold text-lg shadow-lg">
                {user?.name?.charAt(0)?.toUpperCase() || "A"}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-semibold truncate">
                  {user?.name || "Admin Demo"}
                </p>
                <p className="text-[#6b6b6b] text-xs truncate">
                  {user?.email || "demo@gimmicks.com"}
                </p>
                <p className="text-emerald-400 text-xs font-medium">
                  {isAdmin ? "Administrador" : "Asesor"}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                className="text-[#6b6b6b] hover:text-white hover:bg-[#3d3d40] rounded-lg"
                data-testid="logout-btn"
              >
                <LogOut size={18} />
              </Button>
            </div>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-[#1a1a1d]">
        <div className="min-h-screen">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
