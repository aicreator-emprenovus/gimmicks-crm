import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { toast } from "sonner";
import { Eye, EyeOff, Loader2 } from "lucide-react";

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        toast.success("¡Bienvenido!");
      } else {
        await register(email, password, name);
        toast.success("¡Cuenta creada exitosamente!");
      }
      navigate("/dashboard");
    } catch (error) {
      const message = error.response?.data?.detail || "Error de autenticación";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-white rounded-xl shadow-2xl overflow-hidden">
        <CardHeader className="bg-zinc-900 p-6 text-center">
          <img
            src="https://customer-assets.emergentagent.com/job_quote-crafter-1/artifacts/ee7e6zy2_logo-gimmicks.png"
            alt="Gimmicks Logo"
            className="h-16 mx-auto mb-2"
            data-testid="login-logo"
          />
          <p className="text-zinc-400 text-sm mt-2">CRM WhatsApp Business</p>
        </CardHeader>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="name" className="text-zinc-700 font-medium">
                  Nombre Completo
                </Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Tu nombre"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required={!isLogin}
                  className="bg-white border-zinc-200 text-zinc-900 focus:ring-emerald-500"
                  data-testid="register-name-input"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-zinc-700 font-medium">
                Email Corporativo
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="correo@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-white border-zinc-200 text-zinc-900 focus:ring-emerald-500"
                data-testid="login-email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-zinc-700 font-medium">
                Contraseña
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="bg-white border-zinc-200 text-zinc-900 focus:ring-emerald-500 pr-10"
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                  data-testid="toggle-password-btn"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-600 text-white font-medium py-2.5 transition-all duration-200"
              data-testid="login-submit-btn"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : isLogin ? (
                "Iniciar Sesión"
              ) : (
                "Crear Cuenta"
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-sm text-zinc-500 hover:text-emerald-600 transition-colors"
              data-testid="toggle-auth-mode-btn"
            >
              {isLogin
                ? "¿No tienes cuenta? Regístrate"
                : "¿Ya tienes cuenta? Inicia sesión"}
            </button>
          </div>

          <p className="mt-4 text-center text-xs text-zinc-400">
            Acceso restringido a personal autorizado
          </p>
        </CardContent>
      </Card>

      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 text-zinc-500 text-xs">
        © 2026 Gimmicks Marketing Services. Todos los derechos reservados.
      </div>
    </div>
  );
}
