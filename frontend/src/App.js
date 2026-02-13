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
import Quotes from "@/pages/Quotes";
import Layout from "@/components/Layout";

// Auth Context
import { AuthProvider, useAuth } from "@/context/AuthContext";

function ProtectedRoute({ children, adminOnly = false }) {
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

  // Check admin-only routes
  if (adminOnly && user.role !== "admin") {
    return <Navigate to="/inbox" replace />;
  }
  
  return children;
}

function AppRoutes() {
  const { user } = useAuth();
  
  // Determine default route based on role
  const defaultRoute = user?.role === "admin" ? "/dashboard" : "/inbox";
  
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
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
        <Route path="inbox" element={<Inbox />} />
        <Route path="leads" element={
          <ProtectedRoute adminOnly>
            <Leads />
          </ProtectedRoute>
        } />
        <Route path="inventory" element={<Inventory />} />
        <Route path="quotes" element={<Quotes />} />
        <Route path="users" element={
          <ProtectedRoute adminOnly>
            <Users />
          </ProtectedRoute>
        } />
        <Route path="settings" element={
          <ProtectedRoute adminOnly>
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
