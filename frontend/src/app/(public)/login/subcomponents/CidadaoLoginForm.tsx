"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { User, KeyRound, ArrowRight, Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { apiRoutes } from "@/lib/api-routes";
import { apiFetch, onlyDigits, saveAuthSession } from "@/lib/api";
import type { AuthResponse, CidadaoUser } from "@/lib/api-types";

function InputWithIcon({
  id,
  label,
  type = "text",
  placeholder,
  icon: Icon,
  value,
  onChange,
  maxLength,
  rightElement,
}: {
  id: string;
  label: string;
  type?: string;
  placeholder: string;
  icon: React.ElementType;
  value: string;
  onChange: (v: string) => void;
  maxLength?: number;
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
          maxLength={maxLength}
          className="pl-9 h-11 text-sm border-[#D1D1D1] focus-visible:border-[#004080] focus-visible:ring-[#004080]/20"
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

export function CidadaoLoginForm() {
  const router = useRouter();
  const [cpf, setCpf] = useState("");
  const [senha, setSenha] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [hasError, setHasError] = useState(false);

  function formatCpf(value: string) {
    const digits = onlyDigits(value).slice(0, 11);
    return digits
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback("");
    setHasError(false);

    if (onlyDigits(cpf).length !== 11 || !senha) {
      setHasError(true);
      setFeedback("Informe CPF e senha para continuar.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await apiFetch<AuthResponse<CidadaoUser>>(
        apiRoutes.cidadaoLogin,
        {
          method: "POST",
          cache: "no-store",
          body: JSON.stringify({
            username: onlyDigits(cpf),
            password: senha,
          }),
        },
      );
      saveAuthSession(response, "cidadao");

      setFeedback("Login realizado com sucesso.");
      router.replace("/acesso");
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
      <InputWithIcon
        id="cpf"
        label="CPF do Paciente"
        placeholder="000.000.000-00"
        icon={User}
        value={cpf}
        onChange={(v) => setCpf(formatCpf(v))}
      />

      <div className="flex flex-col gap-1">
        <InputWithIcon
          id="senha"
          label="Senha de Acesso"
          type={showPassword ? "text" : "password"}
          placeholder="********"
          icon={KeyRound}
          value={senha}
          onChange={setSenha}
          rightElement={
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="text-[#004080]/60 hover:text-[#002A58] transition-colors"
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          }
        />

      </div>

      {feedback && (
        <p
          className={`text-sm ${hasError ? "text-red-600" : "text-green-700"}`}
          role="status"
        >
          {feedback}
        </p>
      )}

      <Button
        id="btn-entrar"
        type="submit"
        size="lg"
        disabled={isSubmitting}
        className="w-full h-11 bg-[#004080] hover:bg-[#002A58] text-white font-semibold mt-1 gap-2 transition-all duration-200"
      >
        {isSubmitting ? "Entrando..." : "Entrar na Conta"}
        <ArrowRight className="w-4 h-4" />
      </Button>
    </form>
  );
}

