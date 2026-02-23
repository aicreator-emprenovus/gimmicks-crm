import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { useEffect, useState } from "react";

// Pages
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Inbox from "@/pages/Inbox";
import Leads from "@/pages/Leads";
import Inventory from "@/pages/Inventory";
import Settings from "@/pages/Settings";
import Users from "@/pages/Users";
import QuoteHistory from "@/pages/QuoteHistory";
import QuoteBuilder from "@/pages/QuoteBuilder";
import Clients from "@/pages/Clients";
import Interesados from "@/pages/Interesados";
import PublicCatalog from "@/pages/PublicCatalog";
import Layout from "@/components/Layout";

// Auth Context
import { AuthProvider, useAuth } from "@/context/AuthContext";

function ProtectedRoute({ children, adminOnly = false, allowedRoles = null }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f6f8] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#7BA899]"></div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    const fallback = user.role === "desarrollador" ? "/settings" : user.role === "admin" ? "/dashboard" : "/inbox";
    return <Navigate to={fallback} replace />;
  }

  if (adminOnly && user.role !== "admin") {
    const fallback = user.role === "desarrollador" ? "/settings" : "/inbox";
    return <Navigate to={fallback} replace />;
  }
  
  return children;
}

function AppRoutes() {
  const { user } = useAuth();
  
  const defaultRoute = user?.role === "desarrollador" ? "/settings" : user?.role === "admin" ? "/dashboard" : "/inbox";
  
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/catalog" element={<PublicCatalog />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to={defaultRoute} replace />} />
        <Route path="dashboard" element={
          <ProtectedRoute adminOnly>
            <Dashboard />
          </ProtectedRoute>
        } />
        <Route path="inbox" element={
          <ProtectedRoute allowedRoles={["admin", "asesor"]}>
            <Inbox />
          </ProtectedRoute>
        } />
        <Route path="leads" element={
          <ProtectedRoute adminOnly>
            <Leads />
          </ProtectedRoute>
        } />
        <Route path="inventory" element={
          <ProtectedRoute allowedRoles={["admin", "asesor"]}>
            <Inventory />
          </ProtectedRoute>
        } />
        <Route path="clients" element={
          <ProtectedRoute allowedRoles={["admin", "asesor"]}>
            <Clients />
          </ProtectedRoute>
        } />
        <Route path="interesados" element={
          <ProtectedRoute allowedRoles={["admin", "asesor"]}>
            <Interesados />
          </ProtectedRoute>
        } />
        <Route path="quotes" element={
          <ProtectedRoute allowedRoles={["admin", "asesor"]}>
            <QuoteHistory />
          </ProtectedRoute>
        } />
        <Route path="quotes/new" element={
          <ProtectedRoute allowedRoles={["admin", "asesor"]}>
            <QuoteBuilder />
          </ProtectedRoute>
        } />
        <Route path="purchase-orders" element={
          <ProtectedRoute allowedRoles={["admin", "asesor"]}>
            <QuoteHistory />
          </ProtectedRoute>
        } />
        <Route path="purchase-orders/new" element={
          <ProtectedRoute allowedRoles={["admin", "asesor"]}>
            <QuoteBuilder />
          </ProtectedRoute>
        } />
        <Route path="users" element={
          <ProtectedRoute adminOnly>
            <Users />
          </ProtectedRoute>
        } />
        <Route path="settings" element={
          <ProtectedRoute allowedRoles={["desarrollador"]}>
            <Settings />
          </ProtectedRoute>
        } />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
