"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { UserCog, KeyRound, LogIn, Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { apiRoutes } from "@/lib/api-routes";
import { apiFetch, saveAuthSession } from "@/lib/api";
import type { AdminUser, AuthResponse } from "@/lib/api-types";

function AdminInputWithIcon({
  id,
  label,
  type = "text",
  placeholder,
  icon: Icon,
  value,
  onChange,
  rightElement,
}: {
  id: string;
  label: string;
  type?: string;
  placeholder: string;
  icon: React.ElementType;
  value: string;
  onChange: (v: string) => void;
  rightElement?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id} className="text-sm font-medium text-[#002A58]">
        {label}
      </Label>
      <div className="relative">
        <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#004080]/60 pointer-events-none" />
        <Input
          id={id}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="pl-9 h-11 text-sm border-[#C0C0C0] focus-visible:border-[#002A58] focus-visible:ring-[#002A58]/10"
        />
        {rightElement && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {rightElement}
          </div>
        )}
      </div>
    </div>
  );
}

export function AdminLoginForm() {
  const router = useRouter();
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [hasError, setHasError] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback("");
    setHasError(false);

    if (!usuario || !senha) {
      setHasError(true);
      setFeedback("Informe usuário e senha para continuar.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await apiFetch<AuthResponse<AdminUser>>(
        apiRoutes.adminLogin,
        {
          method: "POST",
          cache: "no-store",
          body: JSON.stringify({
            username: usuario,
            password: senha,
          }),
        },
      );
      saveAuthSession(response, "admin");

      setFeedback("Login realizado com sucesso.");
      router.replace("/dashboard");
    } catch (error) {
      setHasError(true);
      setFeedback(
        error instanceof Error
          ? error.message
          : "Nao foi possivel autenticar.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <AdminInputWithIcon
        id="usuario"
        label="Usuário"
        placeholder="ex: servidora.saude"
        icon={UserCog}
        value={usuario}
        onChange={setUsuario}
      />

      <AdminInputWithIcon
        id="senha"
        label="Senha"
        type={showPassword ? "text" : "password"}
        placeholder="************"
        icon={KeyRound}
        value={senha}
        onChange={setSenha}
        rightElement={
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="text-[#004080]/60 hover:text-[#002A58] transition-colors"
            title={showPassword ? "Esconder senha" : "Mostrar senha"}
          >
            {showPassword ? (
              <EyeOff className="w-4 h-4" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
          </button>
        }
      />

      {feedback && (
        <p
          className={`text-sm ${hasError ? "text-red-600" : "text-green-700"}`}
          role="status"
        >
          {feedback}
        </p>
      )}

      <Button
        id="btn-autenticar"
        type="submit"
        size="lg"
        disabled={isSubmitting}
        className="w-full h-11 bg-[#004080] hover:bg-[#002A58] text-white font-semibold mt-2 gap-2 transition-all duration-200"
      >
        {isSubmitting ? "Autenticando..." : "Autenticar no Sistema"}
        <LogIn className="w-4 h-4" />
      </Button>
    </form>
  );
}

