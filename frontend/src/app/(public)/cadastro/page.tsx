"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiRoutes } from "@/lib/api-routes";
import { apiFetch, onlyDigits, saveAuthSession } from "@/lib/api";
import type { AuthResponse, CidadaoUser } from "@/lib/api-types";

function formatCpf(value: string) {
  return onlyDigits(value)
    .slice(0, 11)
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}

export default function CadastroCidadaoPage() {
  const router = useRouter();
  const [cpf, setCpf] = useState("");
  const [cns, setCns] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [feedback, setFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFeedback("");

    const cpfDigits = onlyDigits(cpf);
    const cnsDigits = onlyDigits(cns);
    if (cpfDigits.length !== 11) {
      setFeedback("Informe um CPF válido com 11 dígitos.");
      return;
    }
    if (cnsDigits.length !== 15) {
      setFeedback("Informe um CNS válido com 15 dígitos.");
      return;
    }
    if (!password || password !== passwordConfirmation) {
      setFeedback("Informe senhas iguais nos dois campos.");
      return;
    }

    setIsSubmitting(true);
    let accountCreated = false;
    try {
      await apiFetch<CidadaoUser>(apiRoutes.cidadaoRegister, {
        method: "POST",
        cache: "no-store",
        body: JSON.stringify({
          cpf: cpfDigits,
          cns: cnsDigits,
          password,
          password_confirmation: passwordConfirmation,
        }),
      });
      accountCreated = true;

      const session = await apiFetch<AuthResponse<CidadaoUser>>(
        apiRoutes.cidadaoLogin,
        {
          method: "POST",
          cache: "no-store",
          body: JSON.stringify({ username: cpfDigits, password }),
        },
      );
      saveAuthSession(session, "cidadao");
      router.replace("/acesso");
    } catch (error) {
      if (accountCreated) {
        setFeedback("Conta criada, mas o login automático falhou. Entre com sua nova senha.");
        window.setTimeout(() => router.replace("/login"), 1800);
      } else {
        setFeedback(
          error instanceof Error
            ? error.message
            : "Não foi possível concluir o cadastro.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-[#f4f6f9] px-4 py-12">
      <section className="w-full max-w-lg rounded-2xl border border-[#D1D1D1] bg-white p-6 shadow-md sm:p-8">
        <div className="mb-6">
          <p className="text-sm font-medium text-[#004080]">Área do cidadão</p>
          <h1 className="mt-1 text-2xl font-bold text-[#002A58]">Criar conta</h1>
          <p className="mt-2 text-sm leading-6 text-[#002A58]/70">
            Use o CPF e o CNS de um paciente já cadastrado na rede de saúde.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="grid gap-4">
          <FormField label="CPF" htmlFor="cpf">
            <Input
              id="cpf"
              value={cpf}
              onChange={(event) => setCpf(formatCpf(event.target.value))}
              placeholder="000.000.000-00"
              inputMode="numeric"
              maxLength={14}
              autoComplete="username"
            />
          </FormField>

          <FormField label="CNS" htmlFor="cns">
            <Input
              id="cns"
              value={cns}
              onChange={(event) => setCns(onlyDigits(event.target.value).slice(0, 15))}
              placeholder="000000000000000"
              inputMode="numeric"
              maxLength={15}
              autoComplete="off"
            />
          </FormField>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Senha" htmlFor="password">
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="new-password"
              />
            </FormField>
            <FormField label="Confirmar senha" htmlFor="password-confirmation">
              <Input
                id="password-confirmation"
                type="password"
                value={passwordConfirmation}
                onChange={(event) => setPasswordConfirmation(event.target.value)}
                autoComplete="new-password"
              />
            </FormField>
          </div>

          {feedback && (
            <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">
              {feedback}
            </p>
          )}

          <Button
            type="submit"
            size="lg"
            disabled={isSubmitting}
            className="mt-2 w-full gap-2 bg-[#004080] text-white hover:bg-[#002A58]"
          >
            <UserPlus className="h-4 w-4" />
            {isSubmitting ? "Criando conta..." : "Criar conta e entrar"}
          </Button>
        </form>

        <Link
          href="/login"
          className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-[#004080] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar para o login
        </Link>
      </section>
    </div>
  );
}

function FormField({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={htmlFor} className="text-sm font-medium text-[#002A58]">
        {label}
      </Label>
      {children}
    </div>
  );
}
