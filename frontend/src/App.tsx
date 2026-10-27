import { useEffect, ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { supabase } from "./lib/supabase";
import { useAuthStore } from "./store/authStore";
import { useUIStore } from "./store/uiStore";

import { DashboardLayout } from "./components/DashboardLayout";
import { ToastContainer } from "./components/ToastContainer";
import { ServerWarmupBanner } from "./components/ServerWarmupBanner";
import { ErrorBoundary } from "./components/ErrorBoundary";

import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { DashboardPage } from "./pages/DashboardPage";
import { NewTripPage } from "./pages/NewTripPage";
import { TripDetailPage } from "./pages/TripDetailPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      refetchOnWindowFocus: false,
    },
  },
});

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <DashboardLayout>{children}</DashboardLayout>;
}

export function App() {
  const { setSession } = useAuthStore();
  const isDarkMode = useUIStore((s) => s.isDarkMode);
  const setIsServerWakingUp = useUIStore((s) => s.setIsServerWakingUp);

  useEffect(() => {
    // Ping /health on mount; if it takes longer than 2.5s, show friendly wake-up banner
    const apiBase =
      import.meta.env.VITE_API_URL ||
      import.meta.env.VITE_API_BASE_URL ||
      "http://localhost:8000";

    let resolved = false;
    const slowTimer = setTimeout(() => {
      if (!resolved) {
        setIsServerWakingUp(true);
      }
    }, 2500);

    fetch(`${apiBase}/health`, { method: "GET" })
      .then(() => {
        resolved = true;
        clearTimeout(slowTimer);
        setIsServerWakingUp(false);
      })
      .catch(() => {
        // Ignored; UI shows banner or fails gracefully on user actions
      });

    return () => clearTimeout(slowTimer);
  }, [setIsServerWakingUp]);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDarkMode]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      useAuthStore.setState({ isLoading: false });
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      useAuthStore.setState({ isLoading: false });
    });

    return () => subscription.unsubscribe();
  }, [setSession]);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ServerWarmupBanner />
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Authenticated Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/trips/new"
              element={
                <ProtectedRoute>
                  <NewTripPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/trips/:id"
              element={
                <ProtectedRoute>
                  <TripDetailPage />
                </ProtectedRoute>
              }
            />

            {/* Default Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          <ToastContainer />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
