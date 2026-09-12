"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
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

function formatCpf(value: string) {
  return value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`));
}

export default function AcessoCidadaoPage() {
  const router = useRouter();
  const [user, setUser] = useState<CidadaoUser | null>(null);
  const [registros, setRegistros] = useState<RegistroFila[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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
    return <main className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-600">Carregando seus dados...</main>;
  }

  return (
    <div className="min-h-screen bg-slate-50">
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
          <section className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800" role="alert">
            {error}
          </section>
        ) : user ? (
          <>
            <section className="rounded-xl border bg-white p-6 shadow-sm">
              <p className="text-sm font-medium text-[#004080]">Área do cidadão</p>
              <h1 className="mt-1 text-2xl font-semibold text-[#002A58]">
                Olá, {user.nome_completo || "cidadão"}
              </h1>
              <p className="mt-2 text-sm text-slate-600">CPF: {formatCpf(user.cpf)}</p>
            </section>

            <section className="overflow-hidden rounded-xl border bg-white shadow-sm">
              <div className="border-b px-5 py-4">
                <h2 className="font-semibold text-[#002A58]">Minhas solicitações</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Somente registros vinculados ao seu CPF são exibidos.
                </p>
              </div>
              {registros.length === 0 ? (
                <p className="p-6 text-sm text-slate-500">
                  Nenhuma solicitação publicada foi encontrada para seu CPF.
                </p>
              ) : (
                <div className="grid gap-4 p-5 md:grid-cols-2">
                  {registros.map((registro) => (
                    <article key={registro.id} className="rounded-lg border border-slate-200 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-[#002A58]">{registro.especialidade_nome}</p>
                          <p className="text-xs text-slate-500">{registro.especialidade_tipo_display}</p>
                        </div>
                        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-[#004080]">
                          {registro.situacao_display}
                        </span>
                      </div>
                      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <dt className="text-slate-500">Posição</dt>
                          <dd className="font-semibold text-slate-800">#{registro.posicao}</dd>
                        </div>
                        <div>
                          <dt className="text-slate-500">Prioridade</dt>
                          <dd className="font-medium text-slate-800">{registro.prioridade_display}</dd>
                        </div>
                        <div>
                          <dt className="text-slate-500">Solicitação</dt>
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
              )}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
