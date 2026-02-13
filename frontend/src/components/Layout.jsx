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
  Users2,
  ChevronsLeft,
  ChevronsRight,
  FileText
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
  { to: "/settings", icon: Settings, label: "Configuracion", roles: ["admin"] },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

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
        style={{ width: collapsed ? 72 : 200 }}
        className={`fixed lg:static inset-y-0 left-0 z-40 bg-[#1a1a1d] border-r border-[#2d2d30] transition-all duration-200 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className={`border-b border-[#2d2d30] flex items-center justify-center ${collapsed ? "p-3" : "p-4"}`}>
            <img
              src="https://customer-assets.emergentagent.com/job_quote-crafter-1/artifacts/ee7e6zy2_logo-gimmicks.png"
              alt="Gimmicks"
              className={collapsed ? "h-8" : "h-10"}
              data-testid="sidebar-logo"
            />
          </div>

          {/* Collapse toggle */}
          <div className="hidden lg:flex justify-end px-2 pt-2">
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1.5 rounded-lg text-[#6b6b6b] hover:text-white hover:bg-[#2d2d30] transition-colors"
              data-testid="sidebar-toggle-btn"
            >
              {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 py-3 overflow-y-auto">
            <ul className={`space-y-1 ${collapsed ? "px-2" : "px-3"}`}>
              {filteredNavItems.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    onClick={() => setSidebarOpen(false)}
                    title={collapsed ? item.label : undefined}
                    className={({ isActive }) =>
                      `flex items-center ${collapsed ? "justify-center" : "gap-3"} ${collapsed ? "px-2" : "px-3"} py-2.5 rounded-xl transition-all duration-200 group ${
                        isActive
                          ? "bg-gradient-to-r from-[#2d2d30] to-[#3d3d40] text-white border-l-3 border-[#7BA899]"
                          : "text-[#8a8a8a] hover:text-white hover:bg-[#2d2d30]/50"
                      }`
                    }
                    data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                  >
                    <item.icon size={20} className="flex-shrink-0" />
                    {!collapsed && <span className="font-medium text-sm whitespace-nowrap">{item.label}</span>}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          {/* User section */}
          <div className={`border-t border-[#2d2d30] ${collapsed ? "p-2" : "p-3"}`}>
            {collapsed ? (
              <div className="flex flex-col items-center gap-2">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#7BA899] to-[#5E8A7A] flex items-center justify-center text-white font-bold text-sm shadow-lg">
                  {user?.name?.charAt(0)?.toUpperCase() || "A"}
                </div>
                <button
                  onClick={handleLogout}
                  className="p-1.5 rounded-lg text-[#6b6b6b] hover:text-white hover:bg-[#3d3d40] transition-colors"
                  data-testid="logout-btn"
                >
                  <LogOut size={16} />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 p-2 rounded-xl bg-[#2d2d30]/50">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#7BA899] to-[#5E8A7A] flex items-center justify-center text-white font-bold text-sm shadow-lg flex-shrink-0">
                  {user?.name?.charAt(0)?.toUpperCase() || "A"}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-semibold truncate">
                    {user?.name || "Admin Demo"}
                  </p>
                  <p className="text-[#7BA899] text-[10px] font-medium">
                    {isAdmin ? "Administrador" : "Asesor"}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleLogout}
                  className="text-[#6b6b6b] hover:text-white hover:bg-[#3d3d40] rounded-lg h-7 w-7"
                  data-testid="logout-btn"
                >
                  <LogOut size={15} />
                </Button>
              </div>
            )}
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
      <main className="flex-1 overflow-auto bg-[#f5f6f8]">
        <div className="min-h-screen">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
