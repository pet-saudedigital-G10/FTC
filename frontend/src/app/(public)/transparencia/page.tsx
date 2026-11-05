"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { apiRoutes } from "@/lib/api-routes";
import type {
  TransparenciaContagem,
  TransparenciaIndicadores,
  TransparenciaPosicao,
} from "@/lib/api-types";

const prefeitura =
  process.env.NEXT_PUBLIC_PREFEITURA_NOME ?? "Prefeitura Municipal";

const numero = new Intl.NumberFormat("pt-BR");

function formatDays(value: number | null) {
  if (value === null) return "—";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value)} ${
    value === 1 ? "dia" : "dias"
  }`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`));
}

function formatDatetime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function TransparenciaPage() {
  const [dados, setDados] = useState<TransparenciaIndicadores | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadIndicadores() {
      try {
        const data = await apiFetch<TransparenciaIndicadores>(
          apiRoutes.transparenciaIndicadores,
          { cache: "no-store" },
        );
        if (active) setDados(data);
      } catch {
        if (active) setError("Não foi possível carregar os indicadores.");
      }
    }
    void loadIndicadores();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-[#002A58] px-4 py-8 text-white sm:px-6">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-medium text-blue-200">{prefeitura}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
            Fila da saúde em números
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-blue-100">
            Quantidades, tempos médios de espera e consulta de posição nas filas de
            regulação de consultas e exames.
          </p>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6">
        {error ? (
          <p className="rounded-xl border bg-white p-6 text-sm text-red-700" role="alert">
            {error}
          </p>
        ) : !dados ? (
          <p className="text-sm text-slate-500">Carregando indicadores...</p>
        ) : (
          <>
            <section
              aria-label="Resumo das filas"
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              <StatTile label="Pessoas aguardando" value={numero.format(dados.total_aguardando)} />
              <StatTile
                label="Especialidades com fila"
                value={numero.format(dados.especialidades_com_fila)}
              />
              <StatTile label="Espera média" value={formatDays(dados.espera_media_dias)} />
              <StatTile label="Maior espera" value={formatDays(dados.maior_espera_dias)} />
            </section>

            <ConsultaPosicao />

            <section className="grid items-start gap-4 lg:grid-cols-3">
              <BarList titulo="Por tipo" itens={dados.por_tipo} />
              <BarList titulo="Por prioridade" itens={dados.por_prioridade} />
              <BarList titulo="Por situação" itens={dados.por_situacao} />
            </section>

            <section className="overflow-hidden rounded-xl border bg-white shadow-sm">
              <div className="border-b px-5 py-4">
                <h2 className="font-semibold text-[#002A58]">Filas por especialidade</h2>
              </div>
              {dados.especialidades.length === 0 ? (
                <p className="p-6 text-sm text-slate-500">Nenhuma fila publicada.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[620px] text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-4 py-3">Especialidade</th>
                        <th className="px-4 py-3">Tipo</th>
                        <th className="px-4 py-3 text-right">Aguardando</th>
                        <th className="px-4 py-3 text-right">Espera média</th>
                        <th className="px-4 py-3 text-right">Maior espera</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {dados.especialidades.map((item) => (
                        <tr key={`${item.tipo}-${item.nome}`}>
                          <td className="px-4 py-3 font-medium text-slate-800">{item.nome}</td>
                          <td className="px-4 py-3 text-slate-600">{item.tipo}</td>
                          <td className="px-4 py-3 text-right text-slate-800">
                            {numero.format(item.total)}
                          </td>
                          <td className="px-4 py-3 text-right text-slate-700">
                            {formatDays(item.espera_media_dias)}
                          </td>
                          <td className="px-4 py-3 text-right text-slate-700">
                            {formatDays(item.maior_espera_dias)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <p className="text-xs leading-5 text-slate-500">
              {dados.atualizado_em && (
                <>Última publicação: {formatDatetime(dados.atualizado_em)}. </>
              )}
              A espera é contada em dias corridos, da data da solicitação até hoje. Os
              indicadores não identificam pacientes, e a posição pode mudar conforme a
              regulação e novas solicitações.
            </p>
          </>
        )}
      </main>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-600">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-[#002A58]">{value}</p>
    </div>
  );
}

function BarList({
  titulo,
  itens,
}: {
  titulo: string;
  itens: TransparenciaContagem[];
}) {
  const maior = Math.max(...itens.map((item) => item.total), 1);

  return (
    <div className="rounded-xl border bg-white p-5 shadow-sm">
      <h2 className="font-semibold text-[#002A58]">{titulo}</h2>
      <ul className="mt-4 flex flex-col gap-3">
        {itens.map((item) => (
          <li key={String(item.valor)} title={`${item.rotulo}: ${numero.format(item.total)}`}>
            <div className="flex justify-between gap-3 text-sm">
              <span className="text-slate-700">{item.rotulo}</span>
              <span className="font-medium text-slate-800">{numero.format(item.total)}</span>
            </div>
            <div className="mt-1 h-2 rounded bg-slate-100">
              <div
                className="h-2 rounded bg-[#004080]"
                style={{ width: `${(item.total / maior) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ConsultaPosicao() {
  const [codigo, setCodigo] = useState("");
  const [ano, setAno] = useState("");
  const [resultado, setResultado] = useState<TransparenciaPosicao | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setResultado(null);

    if (!codigo.trim() || ano.length !== 4) {
      setError("Informe o código da solicitação e o ano de nascimento com 4 dígitos.");
      return;
    }

    setSearching(true);
    try {
      const data = await apiFetch<TransparenciaPosicao>(apiRoutes.transparenciaPosicao, {
        method: "POST",
        cache: "no-store",
        body: JSON.stringify({
          codigo_solicitacao: codigo.trim(),
          ano_nascimento: Number(ano),
        }),
      });
      setResultado(data);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível realizar a consulta.",
      );
    } finally {
      setSearching(false);
    }
  }

  const inputClass =
    "h-10 rounded-md border border-slate-300 bg-white px-3 text-sm font-normal text-slate-700 outline-none focus:border-[#004080] focus:ring-2 focus:ring-[#004080]/15";

  return (
    <section className="rounded-xl border bg-white p-5 shadow-sm">
      <h2 className="font-semibold text-[#002A58]">Consultar minha posição</h2>
      <p className="mt-1 text-sm text-slate-500">
        Use o código da solicitação informado pela unidade de saúde.
      </p>
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex flex-1 flex-col gap-1.5 text-sm font-medium text-[#002A58]">
          Código da solicitação
          <input
            type="text"
            value={codigo}
            onChange={(event) => setCodigo(event.target.value)}
            maxLength={50}
            autoComplete="off"
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-[#002A58] sm:w-48">
          Ano de nascimento
          <input
            type="text"
            inputMode="numeric"
            value={ano}
            onChange={(event) => setAno(event.target.value.replace(/\D/g, "").slice(0, 4))}
            placeholder="AAAA"
            autoComplete="off"
            className={inputClass}
          />
        </label>
        <Button type="submit" disabled={searching} className="h-10 gap-2">
          <Search className="h-4 w-4" />
          {searching ? "Consultando..." : "Consultar"}
        </Button>
      </form>

      {error && (
        <p className="mt-3 text-sm text-red-700" role="alert">{error}</p>
      )}

      {resultado && !resultado.encontrado && (
        <p className="mt-4 text-sm text-slate-600" role="status">
          Nenhuma solicitação ativa encontrada. Confira os dados ou procure sua unidade de
          saúde.
        </p>
      )}

      {resultado?.filas.map((fila) => (
        <article
          key={`${fila.tipo}-${fila.especialidade}`}
          className="mt-4 rounded-lg border border-slate-200 p-4"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-semibold text-[#002A58]">{fila.especialidade}</p>
              <p className="text-xs text-slate-500">{fila.tipo}</p>
            </div>
            <p className="text-sm text-slate-600">
              Posição{" "}
              <span className="text-2xl font-semibold text-[#002A58]">
                {numero.format(fila.posicao)}
              </span>
            </p>
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <Detalhe rotulo="Situação" valor={fila.situacao} />
            <Detalhe rotulo="Prioridade" valor={fila.prioridade} />
            <Detalhe rotulo="Solicitada em" valor={formatDate(fila.data_solicitacao)} />
            <Detalhe rotulo="Tempo de espera" valor={formatDays(fila.dias_espera)} />
          </dl>
          <p className="mt-3 text-xs text-slate-500">
            {numero.format(fila.total_aguardando)} pessoas aguardam nesta especialidade.
          </p>
        </article>
      ))}
    </section>
  );
}

function Detalhe({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <dt className="text-slate-500">{rotulo}</dt>
      <dd className="font-medium text-slate-800">{valor}</dd>
    </div>
  );
}
