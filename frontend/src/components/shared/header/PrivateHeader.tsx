"use client";

import { LogOut } from "lucide-react";
import { Logo } from "./subcomponents/Logo";
import { UserMenu } from "./subcomponents/UserMenu";

interface PrivateHeaderProps {
  userName: string;
  userRole?: string;
  onLogout?: () => void;
  isLoggingOut?: boolean;
}

export function PrivateHeader({
  userName,
  userRole,
  onLogout,
  isLoggingOut = false,
}: PrivateHeaderProps) {
  return (
    <header className="w-full bg-[#004080] shadow-md">
      <div className="px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-4">
        {/* Logo (variante clara para fundo azul) */}
        <Logo variant="dark" />

        <div className="flex items-center gap-3">
          <UserMenu name={userName} role={userRole} />
          {onLogout && (
            <button
              type="button"
              onClick={onLogout}
              disabled={isLoggingOut}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-white/30 px-3 text-sm font-medium text-white transition-colors hover:bg-white/10 disabled:opacity-60"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">
                {isLoggingOut ? "Saindo..." : "Sair"}
              </span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
