"use client";

import { useEffect, useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { apiRoutes } from "@/lib/api-routes";
import type {
  Especialidade,
  FilaOpcoes,
  RegistroFila,
} from "@/lib/api-types";

type Filters = {
  especialidade: string;
  especialidade_tipo: string;
  tipo: string;
  situacao: string;
  prioridade: string;
};

const initialFilters: Filters = {
  especialidade: "",
  especialidade_tipo: "",
  tipo: "",
  situacao: "",
  prioridade: "",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`));
}

export default function DashboardPage() {
  const [especialidades, setEspecialidades] = useState<Especialidade[]>([]);
  const [opcoes, setOpcoes] = useState<FilaOpcoes | null>(null);
  const [registros, setRegistros] = useState<RegistroFila[]>([]);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [loadingMetadata, setLoadingMetadata] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    async function loadMetadata() {
      setLoadingMetadata(true);
      try {
        const [specialties, filterOptions] = await Promise.all([
          apiFetch<Especialidade[]>(apiRoutes.filaEspecialidades, {
            cache: "no-store",
          }),
          apiFetch<FilaOpcoes>(apiRoutes.filaOpcoes, { cache: "no-store" }),
        ]);
        if (!active) return;
        setEspecialidades(specialties);
        setOpcoes(filterOptions);
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Não foi possível carregar os filtros.",
          );
        }
      } finally {
        if (active) setLoadingMetadata(false);
      }
    }
    void loadMetadata();
    return () => {
      active = false;
    };
  }, [reloadKey]);

  useEffect(() => {
    let active = true;
    async function loadRecords() {
      setLoadingRecords(true);
      setError("");
      const params = new URLSearchParams();
      for (const [key, value] of Object.entries(filters)) {
        if (value) params.set(key, value);
      }
      const path = `${apiRoutes.filaRegistros}${params.size ? `?${params}` : ""}`;

      try {
        const data = await apiFetch<RegistroFila[]>(path, { cache: "no-store" });
        if (active) setRegistros(data);
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Não foi possível carregar os registros.",
          );
        }
      } finally {
        if (active) setLoadingRecords(false);
      }
    }
    void loadRecords();
    return () => {
      active = false;
    };
  }, [filters, reloadKey]);

  const summary = useMemo(() => ({
    total: registros.length,
    solicitadas: registros.filter((item) => item.tipo === "SOLICITADAS").length,
    pendentes: registros.filter((item) => item.tipo === "PENDENTES").length,
    baixadas: registros.filter((item) => item.tipo === "BAIXADAS").length,
  }), [registros]);

  function updateFilter(name: keyof Filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  const isLoading = loadingMetadata || loadingRecords;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-[#004080]">Painel administrativo</p>
          <h1 className="text-2xl font-semibold tracking-tight text-[#002A58]">
            Acompanhamento das filas
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Dados das publicações ativas disponibilizadas pela API.
          </p>
        </div>
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

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Registros encontrados", summary.total],
          ["Solicitadas", summary.solicitadas],
          ["Pendentes", summary.pendentes],
          ["Baixadas", summary.baixadas],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-600">{label}</p>
            <p className="mt-2 text-3xl font-semibold text-[#002A58]">{value}</p>
          </div>
        ))}
      </section>

      <section className="rounded-xl border bg-white p-5 shadow-sm">
        <div className="mb-4">
          <h2 className="font-semibold text-[#002A58]">Filtros</h2>
          <p className="text-sm text-slate-500">Combine os critérios para consultar a API.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <FilterSelect
            label="Especialidade"
            value={filters.especialidade}
            onChange={(value) => updateFilter("especialidade", value)}
            options={especialidades.map((item) => ({
              value: String(item.id),
              label: `${item.tipo_display} — ${item.nome}`,
            }))}
          />
          <FilterSelect
            label="Categoria"
            value={filters.especialidade_tipo}
            onChange={(value) => updateFilter("especialidade_tipo", value)}
            options={opcoes?.especialidade_tipos ?? []}
          />
          <FilterSelect
            label="Tipo"
            value={filters.tipo}
            onChange={(value) => updateFilter("tipo", value)}
            options={opcoes?.tipos ?? []}
          />
          <FilterSelect
            label="Situação"
            value={filters.situacao}
            onChange={(value) => updateFilter("situacao", value)}
            options={opcoes?.situacoes ?? []}
          />
          <FilterSelect
            label="Prioridade"
            value={filters.prioridade}
            onChange={(value) => updateFilter("prioridade", value)}
            options={opcoes?.prioridades ?? []}
          />
        </div>
        {Object.values(filters).some(Boolean) && (
          <button
            type="button"
            onClick={() => setFilters(initialFilters)}
            className="mt-4 text-sm font-medium text-[#004080] hover:underline"
          >
            Limpar filtros
          </button>
        )}
      </section>

      <section id="registros" className="overflow-hidden rounded-xl border bg-white shadow-sm">
        <div className="border-b px-5 py-4">
          <h2 className="font-semibold text-[#002A58]">Registros da fila</h2>
        </div>
        {error ? (
          <p className="p-6 text-sm text-red-700" role="alert">{error}</p>
        ) : loadingRecords ? (
          <p className="p-6 text-sm text-slate-500">Carregando registros...</p>
        ) : registros.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">Nenhum registro corresponde aos filtros.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Posição</th>
                  <th className="px-4 py-3">Especialidade</th>
                  <th className="px-4 py-3">Paciente</th>
                  <th className="px-4 py-3">Solicitação</th>
                  <th className="px-4 py-3">Prioridade</th>
                  <th className="px-4 py-3">Situação</th>
                  <th className="px-4 py-3">Data</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {registros.map((registro) => (
                  <tr key={registro.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3 font-semibold text-[#002A58]">#{registro.posicao}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800">{registro.especialidade_nome}</p>
                      <p className="text-xs text-slate-500">{registro.especialidade_tipo_display}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{registro.nome_mascarado}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700">{registro.codigo_solicitacao}</td>
                    <td className="px-4 py-3 text-slate-700">{registro.prioridade_display}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-[#004080]">
                        {registro.situacao_display}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{formatDate(registro.data_solicitacao)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string | number; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-medium text-[#002A58]">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm font-normal text-slate-700 outline-none focus:border-[#004080] focus:ring-2 focus:ring-[#004080]/15"
      >
        <option value="">Todos</option>
        {options.map((option) => (
          <option key={String(option.value)} value={String(option.value)}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
