"use client";

import { useEffect, useState, useCallback } from "react";
import { Search, Printer, SlidersHorizontal } from "lucide-react";
import { apiFetch, onlyDigits } from "@/lib/api";
import { apiRoutes } from "@/lib/api-routes";
import type { FilaOpcoes, RegistroFila } from "@/lib/api-types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type AbaAtiva = "individual" | "lista-geral";

type PosicaoResult = {
  encontrado: boolean;
  filas: {
    posicao: number;
    prioridade: number;
    prioridade_display: string;
    situacao: string;
    situacao_display: string;
    especialidade: string;
    tipo_especialidade: string;
    competencia: string;
    nome_mascarado: string;
    data_solicitacao: string;
  }[];
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat("pt-BR").format(
      new Date(`${value}T00:00:00`),
    );
  } catch {
    return value;
  }
}

function formatCpf(value: string) {
  const d = onlyDigits(value).slice(0, 11);
  return d
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}

// ---------------------------------------------------------------------------
// Empty state illustration
// ---------------------------------------------------------------------------

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      {/* Simple SVG placeholder matching the design */}
      <svg
        width="120"
        height="100"
        viewBox="0 0 120 100"
        fill="none"
        aria-hidden="true"
      >
        <rect x="30" y="8" width="60" height="10" rx="5" fill="#E2E8F0" />
        <rect x="30" y="24" width="44" height="10" rx="5" fill="#E2E8F0" />
        <rect x="8" y="44" width="60" height="10" rx="5" fill="#E2E8F0" />
        <rect x="8" y="60" width="44" height="10" rx="5" fill="#E2E8F0" />
        <rect x="20" y="8" width="14" height="14" rx="3" fill="#7C3AED" />
        <circle cx="78" cy="72" r="18" fill="#3B82F6" opacity="0.15" />
        <circle cx="78" cy="72" r="12" stroke="#3B82F6" strokeWidth="3" fill="none" />
        <line x1="87" y1="81" x2="96" y2="90" stroke="#3B82F6" strokeWidth="3" strokeLinecap="round" />
        <text x="50" y="100" fontSize="10" fill="#3B82F6" fontWeight="bold">+</text>
      </svg>
      <p className="text-sm text-slate-500 max-w-xs">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Select component
// ---------------------------------------------------------------------------

function FilterSelect({
  label,
  value,
  onChange,
  options,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string | number; label: string }[];
  placeholder?: string;
}) {
  return (
    <div className="flex flex-col gap-1 min-w-[160px]">
      <label className="text-xs text-slate-500">{label}*</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none rounded border border-slate-300 bg-white px-3 py-2.5 pr-8 text-sm text-slate-800 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
        >
          {placeholder && (
            <option value="">{placeholder}</option>
          )}
          {options.map((o) => (
            <option key={String(o.value)} value={String(o.value)}>
              {o.label}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-slate-400">
          ▾
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hero banner
// ---------------------------------------------------------------------------

function HeroBanner() {
  return (
    <div
      className="relative w-full overflow-hidden"
      style={{ background: "linear-gradient(135deg, #0d4f8c 0%, #1a7ab5 60%, #2fa8d4 100%)" }}
    >
      {/* subtle background pattern */}
      <div className="absolute inset-0 opacity-10 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMiIgZmlsbD0id2hpdGUiLz48L3N2Zz4=')]" />
      <div className="relative mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-white sm:text-3xl">
          Lista Pública de Espera de Pacientes
        </h1>
        <p className="mt-2 text-sm text-blue-100">
          Obtenha online a lista de espera dos cidadãos que aguardam atendimento
          na rede de saúde municipal
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Individual tab
// ---------------------------------------------------------------------------

function AbaIndividual({ opcoes }: { opcoes: FilaOpcoes | null }) {
  const [tipo, setTipo] = useState("pendentes");
  const [situacao, setSituacao] = useState("");
  const [busca, setBusca] = useState("");
  const [resultado, setResultado] = useState<PosicaoResult | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState("");

  // Set default situacao when opcoes load
  useEffect(() => {
    if (opcoes?.situacoes?.length && !situacao) {
      setSituacao(String(opcoes.situacoes[0].value));
    }
  }, [opcoes, situacao]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const trimmed = busca.trim();
    if (!trimmed) {
      setError("Informe o CPF, CNS ou número do protocolo.");
      return;
    }

    const cpfDigits = onlyDigits(trimmed);

    setIsSearching(true);
    setHasSearched(false);

    try {
      const params = new URLSearchParams();
      if (tipo) params.set("tipo", tipo);
      if (situacao) params.set("situacao", situacao);

      const data = await apiFetch<PosicaoResult>(
        `${apiRoutes.filaPosicao}`,
        {
          method: "POST",
          cache: "no-store",
          body: JSON.stringify({ cpf: cpfDigits }),
        },
      );
      setResultado(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Não foi possível realizar a consulta.",
      );
      setResultado(null);
    } finally {
      setIsSearching(false);
      setHasSearched(true);
    }
  }

  const tiposOpcoes = opcoes?.tipos ?? [];
  const situacoesOpcoes = opcoes?.situacoes ?? [];

  return (
    <div>
      {/* Filters */}
      <form
        onSubmit={handleSearch}
        className="flex flex-wrap items-end gap-3 px-6 py-5 border-b border-slate-100"
      >
        <FilterSelect
          label="Tipo"
          value={tipo}
          onChange={setTipo}
          options={tiposOpcoes}
          placeholder="Todos"
        />
        <FilterSelect
          label="Situação"
          value={situacao}
          onChange={setSituacao}
          options={situacoesOpcoes}
          placeholder="Todas"
        />
        {/* CPF / CNS / protocolo input */}
        <div className="flex flex-col gap-1 flex-1 min-w-[220px]">
          <label className="text-xs text-slate-500 invisible">Busca</label>
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="CPF, CNS ou o número do protocolo*"
            className="rounded border border-slate-300 px-3 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
        </div>
        {/* Action buttons */}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isSearching}
            className="inline-flex items-center gap-2 rounded bg-purple-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-purple-700 disabled:opacity-60 transition-colors"
          >
            <Search className="h-4 w-4" />
            {isSearching ? "Pesquisando..." : "Pesquisar"}
          </button>
          <button
            type="button"
            title="Imprimir"
            onClick={() => window.print()}
            className="inline-flex items-center justify-center rounded border border-slate-300 p-2.5 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <Printer className="h-4 w-4" />
          </button>
          <button
            type="button"
            title="Limpar filtros"
            onClick={() => { setBusca(""); setResultado(null); setHasSearched(false); setError(""); }}
            className="inline-flex items-center justify-center rounded border border-slate-300 p-2.5 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <SlidersHorizontal className="h-4 w-4" />
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-4 rounded bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      <div className="px-6 py-4">
        {!hasSearched && !error && (
          <EmptyState message='Preencha as informações solicitadas e clique em "Pesquisar" para visualizá-las.' />
        )}

        {hasSearched && resultado && (
          resultado.encontrado && resultado.filas.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                      <th className="py-3 pr-4 font-medium">Paciente</th>
                    <th className="py-3 pr-4 font-medium">Especialidade</th>
                    <th className="py-3 pr-4 font-medium">Tipo</th>
                    <th className="py-3 pr-4 font-medium">Situação</th>
                    <th className="py-3 pr-4 font-medium">Posição</th>
                    <th className="py-3 pr-4 font-medium">Competência</th>
                    <th className="py-3 font-medium">Solicitação</th>
                  </tr>
                </thead>
                <tbody>
                  {resultado.filas.map((fila, i) => (
                    <tr
                      key={i}
                      className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                    >
                      <td className="py-3 pr-4 font-medium text-slate-800">
                        {fila.nome_mascarado}
                      </td>
                      <td className="py-3 pr-4 text-slate-700">
                        {fila.especialidade}
                      </td>
                      <td className="py-3 pr-4 text-slate-600">
                        {fila.tipo_especialidade}
                      </td>
                      <td className="py-3 pr-4">
                        <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                          {fila.situacao_display}
                        </span>
                      </td>
                      <td className="py-3 pr-4 font-semibold text-purple-700">
                        #{fila.posicao}
                      </td>
                      <td className="py-3 pr-4 text-slate-600">
                        {fila.competencia}
                      </td>
                      <td className="py-3 text-slate-600">
                        {formatDate(fila.data_solicitacao)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState message="Nenhum registro encontrado para as informações informadas." />
          )
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lista Geral tab
// ---------------------------------------------------------------------------

function AbaListaGeral({ opcoes }: { opcoes: FilaOpcoes | null }) {
  const [especialidade, setEspecialidade] = useState("");
  const [tipo, setTipo] = useState("");
  const [situacao, setSituacao] = useState("");
  const [prioridade, setPrioridade] = useState("");
  const [registros, setRegistros] = useState<RegistroFila[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState("");

  // Set default situacao when opcoes load
  useEffect(() => {
    if (opcoes?.situacoes?.length && !situacao) {
      setSituacao(String(opcoes.situacoes[0].value));
    }
    if (opcoes?.tipos?.length && !tipo) {
      setTipo(String(opcoes.tipos[0].value));
    }
  }, [opcoes, situacao, tipo]);

  const handleSearch = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError("");
    setIsSearching(true);
    setHasSearched(false);

    try {
      const params = new URLSearchParams();
      if (especialidade) params.set("especialidade", especialidade);
      if (tipo) params.set("tipo", tipo);
      if (situacao) params.set("situacao", situacao);
      if (prioridade) params.set("prioridade", prioridade);

      const query = params.toString();
      const data = await apiFetch<RegistroFila[]>(
        `${apiRoutes.filaRegistros}${query ? `?${query}` : ""}`,
        { cache: "no-store" },
      );
      setRegistros(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Não foi possível carregar a lista.",
      );
      setRegistros([]);
    } finally {
      setIsSearching(false);
      setHasSearched(true);
    }
  }, [especialidade, tipo, situacao, prioridade]);

  const tiposOpcoes = opcoes?.tipos ?? [];
  const situacoesOpcoes = opcoes?.situacoes ?? [];
  const prioridadesOpcoes = opcoes?.prioridades ?? [];

  return (
    <div>
      {/* Filters */}
      <form
        onSubmit={handleSearch}
        className="flex flex-wrap items-end gap-3 px-6 py-5 border-b border-slate-100"
      >
        {/* Especialidade text search */}
        <div className="flex flex-col gap-1 w-full">
          <label className="text-xs text-slate-500 sr-only">Consulta ou exame</label>
          <div className="relative">
            <input
              type="text"
              value={especialidade}
              onChange={(e) => setEspecialidade(e.target.value)}
              placeholder="Consulta ou exame*"
              className="w-full rounded border border-slate-300 px-3 py-2.5 pr-10 text-sm text-slate-800 placeholder-slate-400 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
          </div>
        </div>

        <FilterSelect
          label="Tipo"
          value={tipo}
          onChange={setTipo}
          options={tiposOpcoes}
          placeholder="Todos"
        />
        <FilterSelect
          label="Situação"
          value={situacao}
          onChange={setSituacao}
          options={situacoesOpcoes}
          placeholder="Todas"
        />
        <FilterSelect
          label="Prioridade"
          value={prioridade}
          onChange={setPrioridade}
          options={prioridadesOpcoes}
          placeholder="Todas as prioridades"
        />

        {/* Action buttons */}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isSearching}
            className="inline-flex items-center gap-2 rounded bg-purple-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-purple-700 disabled:opacity-60 transition-colors"
          >
            <Search className="h-4 w-4" />
            {isSearching ? "Pesquisando..." : "Pesquisar"}
          </button>
          <button
            type="button"
            title="Imprimir"
            onClick={() => window.print()}
            className="inline-flex items-center justify-center rounded border border-slate-300 p-2.5 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <Printer className="h-4 w-4" />
          </button>
          <button
            type="button"
            title="Limpar filtros"
            onClick={() => {
              setEspecialidade("");
              setPrioridade("");
              setRegistros([]);
              setHasSearched(false);
              setError("");
            }}
            className="inline-flex items-center justify-center rounded border border-slate-300 p-2.5 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <SlidersHorizontal className="h-4 w-4" />
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-4 rounded bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      <div className="px-6 py-4">
        {!hasSearched && !error && (
          <EmptyState message='Preencha as informações solicitadas e clique em "Pesquisar" para visualizá-las.' />
        )}

        {hasSearched && registros.length === 0 && !error && (
          <EmptyState message="Nenhum registro encontrado para os filtros selecionados." />
        )}

        {hasSearched && registros.length > 0 && (
          <div className="overflow-x-auto">
            <div className="mb-3 text-xs text-slate-500">
              {registros.length} registro{registros.length !== 1 ? "s" : ""} encontrado{registros.length !== 1 ? "s" : ""}
            </div>
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                  <th className="py-3 pr-4 font-medium">Posição</th>
                  <th className="py-3 pr-4 font-medium">Nome</th>
                  <th className="py-3 pr-4 font-medium">Especialidade</th>
                  <th className="py-3 pr-4 font-medium">Tipo</th>
                  <th className="py-3 pr-4 font-medium">Situação</th>
                  <th className="py-3 pr-4 font-medium">Prioridade</th>
                  <th className="py-3 pr-4 font-medium">Código</th>
                  <th className="py-3 font-medium">Solicitação</th>
                </tr>
              </thead>
              <tbody>
                {registros.map((reg) => (
                  <tr
                    key={reg.id}
                    className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                  >
                    <td className="py-3 pr-4 font-semibold text-purple-700">
                      #{reg.posicao}
                    </td>
                    <td className="py-3 pr-4 font-medium text-slate-800">
                      {reg.nome_mascarado}
                    </td>
                    <td className="py-3 pr-4 text-slate-700">
                      {reg.especialidade_nome}
                    </td>
                    <td className="py-3 pr-4 text-slate-600 text-xs">
                      {reg.especialidade_tipo_display}
                    </td>
                    <td className="py-3 pr-4">
                      <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                        {reg.situacao_display}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-slate-600 text-xs">
                      {reg.prioridade_display}
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-slate-600">
                      {reg.codigo_solicitacao}
                    </td>
                    <td className="py-3 text-slate-600">
                      {formatDate(reg.data_solicitacao)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function FilaPublicaPage() {
  const [aba, setAba] = useState<AbaAtiva>("individual");
  const [opcoes, setOpcoes] = useState<FilaOpcoes | null>(null);

  useEffect(() => {
    apiFetch<FilaOpcoes>(apiRoutes.filaOpcoes, { cache: "no-store" })
      .then(setOpcoes)
      .catch(() => {/* silently ignore; selects stay empty */});
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <HeroBanner />

      <div className="mx-auto max-w-7xl px-0 sm:px-0">
        {/* Tab bar */}
        <div className="flex border-b border-slate-200 px-6">
          <button
            type="button"
            onClick={() => setAba("individual")}
            className={`relative px-4 py-3 text-sm font-medium transition-colors ${
              aba === "individual"
                ? "text-green-600"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Individual
            {aba === "individual" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-green-500 rounded-t" />
            )}
          </button>
          <button
            type="button"
            onClick={() => setAba("lista-geral")}
            className={`relative px-4 py-3 text-sm font-medium transition-colors ${
              aba === "lista-geral"
                ? "text-green-600"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Lista Geral
            {aba === "lista-geral" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-green-500 rounded-t" />
            )}
          </button>
        </div>

        {/* Tab content */}
        {aba === "individual" ? (
          <AbaIndividual opcoes={opcoes} />
        ) : (
          <AbaListaGeral opcoes={opcoes} />
        )}
      </div>
    </div>
  );
}

