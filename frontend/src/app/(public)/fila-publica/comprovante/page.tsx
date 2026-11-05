"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

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

function formatDatetime(iso: string) {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FilaItem = {
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
};

// ---------------------------------------------------------------------------
// Conteúdo do comprovante
// ---------------------------------------------------------------------------

function ComprovantePosicao() {
  const params = useSearchParams();
  const [filas, setFilas] = useState<FilaItem[]>([]);
  const [emitidoEm, setEmitidoEm] = useState("");
  const [protocolo, setProtocolo] = useState("");

  useEffect(() => {
    // localStorage é compartilhado entre abas da mesma origem
    const raw = localStorage.getItem("comprovante_fila");
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as {
          filas: FilaItem[];
          emitido_em: string;
          protocolo: string;
        };
        setFilas(parsed.filas);
        setEmitidoEm(parsed.emitido_em);
        setProtocolo(parsed.protocolo);
        // Remove após ler para não deixar dados pessoais armazenados
        localStorage.removeItem("comprovante_fila");
      } catch {
        // ignora
      }
    }
  }, [params]);

  if (filas.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500 text-sm">
        Nenhum dado de comprovante encontrado. Realize a consulta na{" "}
        <a href="/fila-publica" className="ml-1 text-blue-600 underline">
          Fila Pública
        </a>{" "}
        e clique em &quot;Gerar Comprovante&quot;.
      </div>
    );
  }

  return (
    <>
      {/* Estilos apenas para impressão */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
        @page {
          size: A4 portrait;
          margin: 20mm 15mm 20mm 15mm;
        }
      `}</style>

      <div className="min-h-screen bg-white py-8 px-4 max-w-3xl mx-auto">

        {/* Botões de ação — ocultos na impressão */}
        <div className="no-print flex gap-3 justify-end mb-6">
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 rounded bg-purple-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-purple-700 transition-colors"
          >
            🖨️ Imprimir / Salvar PDF
          </button>
          <button
            onClick={() => window.close()}
            className="inline-flex items-center gap-2 rounded border border-slate-300 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
          >
            Fechar
          </button>
        </div>

        {/* Cabeçalho do comprovante */}
        <div className="border-2 border-blue-800 rounded-lg overflow-hidden">

          {/* Faixa de cabeçalho */}
          <div
            className="px-6 py-5 text-white"
            style={{ background: "linear-gradient(135deg, #0d4f8c 0%, #1a7ab5 60%, #2fa8d4 100%)" }}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-blue-200 mb-1">
                  Sistema de Fila Transparente Cidadã
                </p>
                <h1 className="text-xl font-bold leading-tight">
                  Comprovante de Posição na Fila de Espera
                </h1>
                <p className="mt-1 text-sm text-blue-100">
                  Lista Pública de Espera — Rede de Saúde Municipal
                </p>
              </div>
              {/* Ícone decorativo */}
              <div className="shrink-0 opacity-80">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden>
                  <rect x="8" y="6" width="32" height="36" rx="3" stroke="white" strokeWidth="2" fill="none"/>
                  <line x1="14" y1="16" x2="34" y2="16" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                  <line x1="14" y1="22" x2="34" y2="22" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                  <line x1="14" y1="28" x2="26" y2="28" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                  <circle cx="36" cy="34" r="8" fill="white" fillOpacity="0.2" stroke="white" strokeWidth="1.5"/>
                  <path d="M32 34l3 3 5-5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            </div>
          </div>

          {/* Informações do comprovante */}
          <div className="bg-blue-50 px-6 py-3 border-b border-blue-200 flex flex-wrap gap-6 text-xs text-slate-600">
            <span>
              <span className="font-semibold text-slate-700">Emitido em: </span>
              {formatDatetime(emitidoEm)}
            </span>
            {protocolo && (
              <span>
                <span className="font-semibold text-slate-700">Protocolo: </span>
                <span className="font-mono">{protocolo}</span>
              </span>
            )}
            <span>
              <span className="font-semibold text-slate-700">Validade: </span>
              Consulta na data de emissão
            </span>
          </div>

          {/* Dados do paciente (mascarados) */}
          <div className="px-6 py-5 border-b border-slate-200">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Dados do Paciente
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <InfoField label="Nome" value={filas[0]?.nome_mascarado ?? "—"} />
              <InfoField
                label="Registros na fila"
                value={`${filas.length} ${filas.length === 1 ? "especialidade" : "especialidades"}`}
              />
            </div>
          </div>

          {/* Posições na fila */}
          <div className="px-6 py-5">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">
              Posição(ões) na Fila
            </h2>

            <div className="space-y-4">
              {filas.map((fila, i) => (
                <div
                  key={i}
                  className="border border-slate-200 rounded-lg overflow-hidden"
                >
                  {/* Cabeçalho do card */}
                  <div className="bg-slate-50 px-4 py-2.5 flex items-center justify-between border-b border-slate-200">
                    <span className="text-sm font-semibold text-slate-700">
                      {fila.especialidade}
                      <span className="ml-2 text-xs font-normal text-slate-500">
                        ({fila.tipo_especialidade})
                      </span>
                    </span>
                    {/* Destaque da posição */}
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-slate-500">Posição</span>
                      <span className="rounded bg-purple-600 px-3 py-0.5 text-sm font-bold text-white">
                        #{fila.posicao}
                      </span>
                    </div>
                  </div>

                  {/* Detalhes do card */}
                  <div className="px-4 py-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                    <InfoField label="Situação" value={fila.situacao_display} highlight />
                    <InfoField label="Prioridade" value={fila.prioridade_display} />
                    <InfoField label="Competência" value={formatDate(fila.competencia)} />
                    <InfoField label="Data da Solicitação" value={formatDate(fila.data_solicitacao)} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Rodapé com aviso */}
          <div className="bg-amber-50 border-t border-amber-200 px-6 py-4">
            <p className="text-xs text-amber-800 leading-relaxed">
              <span className="font-semibold">⚠️ Atenção:</span> Este comprovante reflete a posição na fila no
              momento da consulta ({formatDatetime(emitidoEm)}). A posição pode variar conforme
              novas atualizações da lista. Os dados pessoais exibidos são parcialmente mascarados
              para proteção da privacidade conforme a LGPD.
            </p>
          </div>
        </div>

        {/* Rodapé da página */}
        <p className="mt-6 text-center text-xs text-slate-400">
          Fila Transparente Cidadã — Sistema de Gestão de Filas de Saúde Municipal
        </p>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Componente auxiliar
// ---------------------------------------------------------------------------

function InfoField({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p
        className={`text-sm font-medium ${
          highlight ? "text-blue-700" : "text-slate-800"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Export com Suspense (necessário para useSearchParams no App Router)
// ---------------------------------------------------------------------------

export default function ComprovantePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-slate-400 text-sm">
          Carregando comprovante...
        </div>
      }
    >
      <ComprovantePosicao />
    </Suspense>
  );
}

