"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, ClipboardList, History } from "lucide-react";
import { Logo } from "@/components/shared/header/subcomponents/Logo";
import { apiRoutes } from "@/lib/api-routes";
import {
  ApiError,
  apiFetch,
  clearAuthSession,
  hasAuthSession,
  logout,
} from "@/lib/api";
import type { CidadaoUser, RegistroFila } from "@/lib/api-types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCpf(value: string) {
  return value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
}

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`));
  } catch {
    return value;
  }
}

function situacaoBadgeClass(situacao: string): string {
  const map: Record<string, string> = {
    AGENDADO: "bg-green-50 text-green-700",
    SOLICITADO: "bg-blue-50 text-blue-700",
    PENDENTE: "bg-yellow-50 text-yellow-700",
    CANCELADO: "bg-red-50 text-red-700",
    NEGADO: "bg-red-50 text-red-700",
    NEGADO_CRL: "bg-red-50 text-red-700",
    DEVOLVIDO: "bg-orange-50 text-orange-700",
    REENVIADO: "bg-purple-50 text-purple-700",
  };
  return map[situacao] ?? "bg-slate-100 text-slate-700";
}

// ---------------------------------------------------------------------------
// Aba Visão Geral
// ---------------------------------------------------------------------------

function AbaVisaoGeral({ registros }: { registros: RegistroFila[] }) {
  if (registros.length === 0) {
    return (
      <p className="p-6 text-sm text-slate-500">
        Nenhuma solicitação publicada foi encontrada para seu CPF.
      </p>
    );
  }
  return (
    <div className="grid gap-4 p-5 md:grid-cols-2">
      {registros.map((registro) => (
        <article key={registro.id} className="rounded-lg border border-slate-200 p-4 hover:shadow-sm transition-shadow">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold text-[#002A58]">{registro.especialidade_nome}</p>
              <p className="text-xs text-slate-500">{registro.especialidade_tipo_display}</p>
            </div>
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${situacaoBadgeClass(registro.situacao)}`}>
              {registro.situacao_display}
            </span>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-slate-500">Posição</dt>
              <dd className="font-semibold text-[#004080]">#{registro.posicao}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Prioridade</dt>
              <dd className="font-medium text-slate-800">{registro.prioridade_display}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Código</dt>
              <dd className="font-mono text-xs text-slate-800">{registro.codigo_solicitacao}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Data</dt>
              <dd className="text-slate-800">{formatDate(registro.data_solicitacao)}</dd>
            </div>
          </dl>
        </article>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Aba Histórico
// ---------------------------------------------------------------------------

function AbaHistorico({ registros }: { registros: RegistroFila[] }) {
  if (registros.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <History className="h-12 w-12 text-slate-200" />
        <p className="text-sm text-slate-500">
          Nenhum registro de histórico encontrado para seu CPF.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <div className="mb-3 px-5 pt-4 text-xs text-slate-500">
        {registros.length} registro{registros.length !== 1 ? "s" : ""} encontrado{registros.length !== 1 ? "s" : ""}
      </div>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
            <th className="px-5 py-3 font-medium">Especialidade</th>
            <th className="py-3 pr-4 font-medium">Tipo</th>
            <th className="py-3 pr-4 font-medium">Situação</th>
            <th className="py-3 pr-4 font-medium">Posição</th>
            <th className="py-3 pr-4 font-medium">Prioridade</th>
            <th className="py-3 pr-4 font-medium">Código</th>
            <th className="py-3 pr-5 font-medium">Data Solicitação</th>
          </tr>
        </thead>
        <tbody>
          {registros.map((reg) => (
            <tr
              key={reg.id}
              className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
            >
              <td className="px-5 py-3 font-medium text-[#002A58]">
                {reg.especialidade_nome}
              </td>
              <td className="py-3 pr-4 text-xs text-slate-600">
                {reg.especialidade_tipo_display}
              </td>
              <td className="py-3 pr-4">
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${situacaoBadgeClass(reg.situacao)}`}>
                  {reg.situacao_display}
                </span>
              </td>
              <td className="py-3 pr-4 font-semibold text-[#004080]">
                #{reg.posicao}
              </td>
              <td className="py-3 pr-4 text-slate-600 text-xs">
                {reg.prioridade_display}
              </td>
              <td className="py-3 pr-4 font-mono text-xs text-slate-600">
                {reg.codigo_solicitacao}
              </td>
              <td className="py-3 pr-5 text-slate-600">
                {formatDate(reg.data_solicitacao)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type Aba = "visao-geral" | "historico";

export default function AcessoCidadaoPage() {
  const router = useRouter();
  const [user, setUser] = useState<CidadaoUser | null>(null);
  const [registros, setRegistros] = useState<RegistroFila[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [aba, setAba] = useState<Aba>("visao-geral");

  useEffect(() => {
    let active = true;
    async function loadData() {
      if (!hasAuthSession("cidadao")) {
        clearAuthSession();
        router.replace("/login");
        return;
      }

      try {
        const [currentUser, queueRecords] = await Promise.all([
          apiFetch<CidadaoUser>(apiRoutes.cidadaoMe, { cache: "no-store" }),
          apiFetch<RegistroFila[]>(apiRoutes.cidadaoFilas, { cache: "no-store" }),
        ]);
        if (!active) return;
        setUser(currentUser);
        setRegistros(queueRecords);
      } catch (requestError) {
        if (!active) return;
        if (
          requestError instanceof ApiError &&
          (requestError.status === 401 || requestError.status === 403)
        ) {
          clearAuthSession();
          router.replace("/login");
          return;
        }
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Não foi possível carregar seus dados.",
        );
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadData();
    return () => {
      active = false;
    };
  }, [router]);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await logout(apiRoutes.cidadaoLogout);
    } catch {
      // The local session is cleared even when the API is unavailable.
    } finally {
      router.replace("/login");
    }
  }

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-600">
        Carregando seus dados...
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-[#004080] shadow-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo variant="dark" />
          <button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="inline-flex items-center gap-2 rounded-md border border-white/30 px-3 py-2 text-sm font-medium text-white hover:bg-white/10 disabled:opacity-60"
          >
            <LogOut className="h-4 w-4" />
            {isLoggingOut ? "Saindo..." : "Sair"}
          </button>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6">
        {error ? (
          <section
            className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800"
            role="alert"
          >
            {error}
          </section>
        ) : user ? (
          <>
            {/* Perfil do cidadão */}
            <section className="rounded-xl border bg-white p-6 shadow-sm">
              <p className="text-sm font-medium text-[#004080]">Área do cidadão</p>
              <h1 className="mt-1 text-2xl font-semibold text-[#002A58]">
                Olá, {user.nome_completo || "cidadão"}
              </h1>
              <p className="mt-2 text-sm text-slate-600">CPF: {formatCpf(user.cpf)}</p>
            </section>

            {/* Card com abas */}
            <section className="overflow-hidden rounded-xl border bg-white shadow-sm">
              {/* Cabeçalho com título e abas */}
              <div className="border-b px-5 pt-4">
                <h2 className="font-semibold text-[#002A58]">Minhas solicitações</h2>
                <p className="mt-1 mb-3 text-sm text-slate-500">
                  Somente registros vinculados ao seu CPF são exibidos.
                </p>

                {/* Tab bar */}
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => setAba("visao-geral")}
                    className={`relative inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors ${
                      aba === "visao-geral"
                        ? "text-[#004080]"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    <ClipboardList className="h-4 w-4" />
                    Visão Geral
                    {aba === "visao-geral" && (
                      <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#004080] rounded-t" />
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => setAba("historico")}
                    className={`relative inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors ${
                      aba === "historico"
                        ? "text-[#004080]"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    <History className="h-4 w-4" />
                    Histórico
                    {registros.length > 0 && (
                      <span className="ml-1 rounded-full bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                        {registros.length}
                      </span>
                    )}
                    {aba === "historico" && (
                      <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#004080] rounded-t" />
                    )}
                  </button>
                </div>
              </div>

              {/* Conteúdo da aba */}
              {aba === "visao-geral" ? (
                <AbaVisaoGeral registros={registros} />
              ) : (
                <AbaHistorico registros={registros} />
              )}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
