"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminSidebar } from "@/components/admin-sidebar";
import { PrivateHeader } from "@/components/shared/header/PrivateHeader";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { apiRoutes } from "@/lib/api-routes";
import {
  ApiError,
  apiFetch,
  clearAuthSession,
  hasAuthSession,
  logout,
} from "@/lib/api";
import type { AdminUser } from "@/lib/api-types";

export function PrivateShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [error, setError] = useState("");
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadUser() {
      if (!hasAuthSession("admin")) {
        clearAuthSession();
        router.replace("/admin/login");
        return;
      }

      try {
        const currentUser = await apiFetch<AdminUser>(apiRoutes.adminMe, {
          cache: "no-store",
        });
        if (active) setUser(currentUser);
      } catch (requestError) {
        if (!active) return;
        if (
          requestError instanceof ApiError &&
          requestError.status !== 401 &&
          requestError.status !== 403
        ) {
          setError(requestError.message);
          return;
        }
        clearAuthSession();
        router.replace("/admin/login");
      }
    }

    void loadUser();
    return () => {
      active = false;
    };
  }, [router]);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await logout(apiRoutes.adminLogout);
    } catch {
      // The local session is cleared even when the API is unavailable.
    } finally {
      router.replace("/admin/login");
    }
  }

  if (error) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 p-6">
        <div className="max-w-md rounded-xl border bg-white p-6 text-center shadow-sm">
          <h1 className="text-lg font-semibold text-[#002A58]">Backend indisponível</h1>
          <p className="mt-2 text-sm text-slate-600">{error}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-4 rounded-md bg-[#004080] px-4 py-2 text-sm font-medium text-white"
          >
            Tentar novamente
          </button>
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50">
        <p className="text-sm text-slate-600">Validando sessão...</p>
      </main>
    );
  }

  const displayName = user.full_name || user.username;
  const role = user.is_superuser ? "Superadministrador" : "Administrador";

  return (
    <SidebarProvider>
      <AdminSidebar />
      <SidebarInset>
        <PrivateHeader
          userName={displayName}
          userRole={role}
          onLogout={handleLogout}
          isLoggingOut={isLoggingOut}
        />
        <main className="flex-1 bg-slate-50 p-4 sm:p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
