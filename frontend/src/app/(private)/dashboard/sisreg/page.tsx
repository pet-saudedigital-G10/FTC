"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { apiRoutes } from "@/lib/api-routes";
import type {
  Especialidade,
  PublicacaoImportada,
  SisregFila,
  SisregGrupos,
  SisregStatus,
} from "@/lib/api-types";
import { SisregConfigForm } from "./subcomponents/SisregConfigForm";

const ambientes: Record<string, string> = {
  homologacao: "Homologação",
  producao: "Produção",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`));
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export default function SisregPage() {
  const [status, setStatus] = useState<SisregStatus | null>(null);
  const [statusError, setStatusError] = useState("");
  const [showConfig, setShowConfig] = useState(false);
  const [configVersion, setConfigVersion] = useState(0);

  useEffect(() => {
    let active = true;
    async function loadStatus() {
      try {
        const data = await apiFetch<SisregStatus>(apiRoutes.sisregStatus, {
          cache: "no-store",
        });
        if (active) setStatus(data);
      } catch (requestError) {
        if (active) {
          setStatusError(
            errorMessage(requestError, "Não foi possível verificar a integração."),
          );
        }
      }
    }
    void loadStatus();
    return () => {
      active = false;
    };
  }, [configVersion]);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-[#004080]">Integração opcional</p>
          <h1 className="text-2xl font-semibold tracking-tight text-[#002A58]">
            Fila de regulação do SISREG
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Consulte a fila ambulatorial na API do DATASUS e publique-a na Fila Transparente.
          </p>
        </div>
        {status?.pode_configurar && status.habilitado && (
          <Button
            variant="outline"
            onClick={() => setShowConfig((value) => !value)}
            className="gap-2"
          >
            <Settings className="h-4 w-4" />
            {showConfig ? "Ocultar configuração" : "Configurar integração"}
          </Button>
        )}
      </div>

      {statusError ? (
        <p className="rounded-xl border bg-white p-6 text-sm text-red-700 shadow-sm" role="alert">
          {statusError}
        </p>
      ) : !status ? (
        <p className="text-sm text-slate-500">Verificando a integração...</p>
      ) : (
        <>
          {status.pode_configurar && (showConfig || !status.habilitado) && (
            <section className="rounded-xl border bg-white p-5 shadow-sm">
              <h2 className="mb-3 font-semibold text-[#002A58]">
                Configuração da integração
              </h2>
              <SisregConfigForm
                onSaved={() => {
                  setShowConfig(true);
                  setConfigVersion((value) => value + 1);
                }}
              />
            </section>
          )}
          {status.habilitado ? (
            <SisregPanel key={configVersion} status={status} />
          ) : (
            !status.pode_configurar && (
              <section className="rounded-xl border bg-white p-6 shadow-sm">
                <h2 className="font-semibold text-[#002A58]">
                  Integração não habilitada
                </h2>
                <p className="mt-2 max-w-3xl text-sm text-slate-600">
                  O uso do SISREG é opcional e a publicação por PDF continua funcionando
                  sem ele. Para habilitar, peça a um superadministrador que informe a
                  credencial nesta tela.
                </p>
              </section>
            )
          )}
        </>
      )}
    </div>
  );
}

function SisregPanel({ status }: { status: SisregStatus }) {
  const [grupos, setGrupos] = useState<SisregGrupos | null>(null);
  const [especialidades, setEspecialidades] = useState<Especialidade[]>([]);
  const [fila, setFila] = useState<SisregFila | null>(null);
  const [grupo, setGrupo] = useState("");
  const [pagina, setPagina] = useState(1);
  const [especialidade, setEspecialidade] = useState("");
  const [loadingGrupos, setLoadingGrupos] = useState(true);
  const [loadingFila, setLoadingFila] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");
  const [importError, setImportError] = useState("");
  const [importResult, setImportResult] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    async function loadGrupos() {
      setLoadingGrupos(true);
      try {
        const [groups, specialties] = await Promise.all([
          apiFetch<SisregGrupos>(apiRoutes.sisregGrupos, { cache: "no-store" }),
          apiFetch<Especialidade[]>(apiRoutes.filaEspecialidades, {
            cache: "no-store",
          }),
        ]);
        if (!active) return;
        setGrupos(groups);
        setEspecialidades(specialties);
      } catch (requestError) {
        if (active) {
          setError(errorMessage(requestError, "Não foi possível consultar o SISREG."));
        }
      } finally {
        if (active) setLoadingGrupos(false);
      }
    }
    void loadGrupos();
    return () => {
      active = false;
    };
  }, [reloadKey]);

  useEffect(() => {
    let active = true;
    async function loadFila() {
      setLoadingFila(true);
      setError("");
      const params = new URLSearchParams({ pagina: String(pagina) });
      if (grupo) params.set("grupo", grupo);

      try {
        const data = await apiFetch<SisregFila>(`${apiRoutes.sisregFila}?${params}`, {
          cache: "no-store",
        });
        if (active) setFila(data);
      } catch (requestError) {
        if (active) {
          setError(errorMessage(requestError, "Não foi possível consultar o SISREG."));
        }
      } finally {
        if (active) setLoadingFila(false);
      }
    }
    void loadFila();
    return () => {
      active = false;
    };
  }, [grupo, pagina, reloadKey]);

  function selectGrupo(value: string) {
    setGrupo(value);
    setPagina(1);
    setImportError("");
    setImportResult("");
  }

  async function handleImport() {
    const confirmed = window.confirm(
      "A fila publicada desta especialidade será substituída pelos dados do SISREG. Deseja continuar?",
    );
    if (!confirmed) return;

    setImporting(true);
    setImportError("");
    setImportResult("");
    try {
      const result = await apiFetch<PublicacaoImportada>(apiRoutes.sisregImportar, {
        method: "POST",
        body: JSON.stringify({
          especialidade: Number(especialidade),
          codigo_grupo_procedimento: grupo,
        }),
      });
      setImportResult(
        `${result.registros_importados} registros publicados (versão ${result.versao}).`,
      );
    } catch (requestError) {
      setImportError(errorMessage(requestError, "Não foi possível publicar a fila."));
    } finally {
      setImporting(false);
    }
  }

  const isLoading = loadingGrupos || loadingFila;
  const totalPaginas = fila ? Math.ceil(fila.total / fila.tamanho_pagina) : 0;

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-3">
        {[
          ["Ambiente", ambientes[status.ambiente ?? ""] ?? status.ambiente],
          ["Índice", status.indice],
          ["Solicitações na fila", grupos?.total ?? "—"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-600">{label}</p>
            <p className="mt-2 break-words text-lg font-semibold text-[#002A58]">{value}</p>
          </div>
        ))}
      </section>

      <section className="rounded-xl border bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <label className="flex flex-1 flex-col gap-1.5 text-sm font-medium text-[#002A58]">
            Grupo de procedimento
            <select
              value={grupo}
              onChange={(event) => selectGrupo(event.target.value)}
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm font-normal text-slate-700 outline-none focus:border-[#004080] focus:ring-2 focus:ring-[#004080]/15"
            >
              <option value="">Todos os grupos</option>
              {grupos?.grupos.map((item) => (
                <option key={item.codigo} value={item.codigo}>
                  {item.nome} ({item.total})
                </option>
              ))}
            </select>
          </label>
          <Button
            variant="outline"
            onClick={() => setReloadKey((value) => value + 1)}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border bg-white shadow-sm">
        <div className="border-b px-5 py-4">
          <h2 className="font-semibold text-[#002A58]">Fila no SISREG</h2>
          <p className="text-sm text-slate-500">
            Ordenada por classificação de risco e data da solicitação. A consulta não
            altera a fila publicada.
          </p>
        </div>
        {error ? (
          <p className="p-6 text-sm text-red-700" role="alert">{error}</p>
        ) : loadingFila ? (
          <p className="p-6 text-sm text-slate-500">Consultando o SISREG...</p>
        ) : !fila || fila.registros.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">Nenhuma solicitação na fila.</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Solicitação</th>
                    <th className="px-4 py-3">Paciente</th>
                    <th className="px-4 py-3">Grupo</th>
                    <th className="px-4 py-3">Classificação de risco</th>
                    <th className="px-4 py-3">Situação</th>
                    <th className="px-4 py-3">Data</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {fila.registros.map((registro) => (
                    <tr key={registro.codigo_solicitacao} className="hover:bg-slate-50/70">
                      <td className="px-4 py-3 font-mono text-xs text-slate-700">
                        {registro.codigo_solicitacao}
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-slate-700">{registro.nome_mascarado}</p>
                        <p className="text-xs text-slate-500">{registro.cns_mascarado}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-700">
                        {registro.nome_grupo_procedimento}
                      </td>
                      <td className="px-4 py-3 text-slate-700">
                        {registro.classificacao_risco}
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-[#004080]">
                          {registro.situacao_display}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {formatDate(registro.data_solicitacao)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between gap-3 border-t px-5 py-3 text-sm text-slate-600">
              <span>
                Página {fila.pagina} de {totalPaginas} · {fila.total} solicitações
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setPagina((value) => value - 1)}
                  disabled={pagina <= 1 || loadingFila}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setPagina((value) => value + 1)}
                  disabled={pagina >= totalPaginas || loadingFila}
                >
                  Próxima
                </Button>
              </div>
            </div>
          </>
        )}
      </section>

      <section className="rounded-xl border bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-[#002A58]">Publicar na Fila Transparente</h2>
        <p className="mt-1 max-w-3xl text-sm text-slate-500">
          Substitui a fila publicada da especialidade pelo grupo selecionado acima. O SISREG
          não informa a posição: ela é calculada pela classificação de risco e pela data da
          solicitação. Confirme esse critério com a Central de Regulação.
        </p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex flex-1 flex-col gap-1.5 text-sm font-medium text-[#002A58]">
            Especialidade de destino
            <select
              value={especialidade}
              onChange={(event) => setEspecialidade(event.target.value)}
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm font-normal text-slate-700 outline-none focus:border-[#004080] focus:ring-2 focus:ring-[#004080]/15"
            >
              <option value="">Selecione</option>
              {especialidades.map((item) => (
                <option key={item.id} value={String(item.id)}>
                  {item.tipo_display} — {item.nome}
                </option>
              ))}
            </select>
          </label>
          <Button
            onClick={() => void handleImport()}
            disabled={!grupo || !especialidade || importing}
          >
            {importing ? "Publicando..." : "Publicar fila"}
          </Button>
        </div>
        {!grupo && (
          <p className="mt-3 text-sm text-slate-500">
            Selecione um grupo de procedimento para publicar.
          </p>
        )}
        {importError && (
          <p className="mt-3 text-sm text-red-700" role="alert">{importError}</p>
        )}
        {importResult && (
          <p className="mt-3 text-sm font-medium text-green-700" role="status">
            {importResult}
          </p>
        )}
      </section>
    </>
  );
}
