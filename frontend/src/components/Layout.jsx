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
  Shield
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";

const adminNavItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard", roles: ["admin"] },
  { to: "/inbox", icon: MessageSquare, label: "Inbox", roles: ["admin", "asesor"] },
  { to: "/leads", icon: Users, label: "Leads", roles: ["admin"] },
  { to: "/inventory", icon: Package, label: "Inventario", roles: ["admin", "asesor"] },
  { to: "/users", icon: UserCog, label: "Usuarios", roles: ["admin"] },
  { to: "/settings", icon: Settings, label: "Configuración", roles: ["admin"] },
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
  const navItems = adminNavItems.filter(item => 
    item.roles.includes(user?.role || "asesor")
  );

  const isAdmin = user?.role === "admin";

  return (
    <div className="min-h-screen bg-[#09090b] flex">
      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-zinc-800 rounded-lg text-white"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        data-testid="mobile-menu-btn"
      >
        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-64 lg:w-20 bg-[#09090b] border-r border-zinc-800 transform transition-transform duration-200 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-4 border-b border-zinc-800">
            <img
              src="https://customer-assets.emergentagent.com/job_quote-crafter-1/artifacts/ee7e6zy2_logo-gimmicks.png"
              alt="Gimmicks"
              className="h-10 mx-auto"
              data-testid="sidebar-logo"
            />
          </div>

          {/* Navigation */}
          <nav className="flex-1 py-4">
            <TooltipProvider>
              <ul className="space-y-2 px-2">
                {navItems.map((item) => (
                  <li key={item.to}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <NavLink
                          to={item.to}
                          onClick={() => setSidebarOpen(false)}
                          className={({ isActive }) =>
                            `flex items-center gap-3 px-3 py-3 rounded-lg transition-all duration-200 ${
                              isActive
                                ? "bg-zinc-800 text-white border-l-2 border-emerald-500"
                                : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                            }`
                          }
                          data-testid={`nav-${item.label.toLowerCase()}`}
                        >
                          <item.icon size={22} />
                          <span className="lg:hidden">{item.label}</span>
                        </NavLink>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="hidden lg:block">
                        {item.label}
                      </TooltipContent>
                    </Tooltip>
                  </li>
                ))}
              </ul>
            </TooltipProvider>
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-zinc-800">
            <div className="flex items-center gap-3 mb-3 lg:justify-center">
              <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center text-white font-semibold">
                {user?.name?.charAt(0)?.toUpperCase() || "U"}
              </div>
              <div className="lg:hidden">
                <p className="text-white text-sm font-medium truncate">{user?.name}</p>
                <div className="flex items-center gap-1">
                  {isAdmin ? (
                    <Badge className="bg-purple-500/20 text-purple-300 text-xs border-0">
                      <Shield className="w-3 h-3 mr-1" />
                      Admin
                    </Badge>
                  ) : (
                    <Badge className="bg-blue-500/20 text-blue-300 text-xs border-0">
                      Asesor
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    onClick={handleLogout}
                    className="w-full text-zinc-400 hover:text-white hover:bg-zinc-800 justify-center lg:justify-center"
                    data-testid="logout-btn"
                  >
                    <LogOut size={20} />
                    <span className="lg:hidden ml-2">Cerrar Sesión</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right" className="hidden lg:block">
                  Cerrar Sesión
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="flex-1 p-4 lg:p-6 overflow-auto">
        <div className="bg-white rounded-xl min-h-[calc(100vh-3rem)] shadow-xl animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
