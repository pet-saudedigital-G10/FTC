"use client";

import { useState, type FormEvent } from "react";
import { FileText, Loader2, Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { apiRoutes } from "@/lib/api-routes";
import type {
  AtualizacaoFilaResposta,
  Especialidade,
} from "@/lib/api-types";

interface AtualizarFilaModalProps {
  open: boolean;
  especialidades: Especialidade[];
  onClose: () => void;
  onSuccess: (resultado: AtualizacaoFilaResposta) => void;
}

function getCurrentMonthISO() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

export function AtualizarFilaModal({
  open,
  especialidades,
  onClose,
  onSuccess,
}: AtualizarFilaModalProps) {
  const [especialidadeId, setEspecialidadeId] = useState("");
  const [competencia, setCompetencia] = useState(getCurrentMonthISO);
  const [observacao, setObservacao] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  function resetAndClose() {
    if (submitting) return;
    setEspecialidadeId("");
    setCompetencia(getCurrentMonthISO());
    setObservacao("");
    setArquivo(null);
    setError("");
    onClose();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!especialidadeId) {
      setError("Selecione a especialidade da fila.");
      return;
    }
    if (!competencia) {
      setError("Informe o mês de competência.");
      return;
    }
    if (!arquivo) {
      setError("Selecione o arquivo PDF da lista de regulação.");
      return;
    }
    if (!arquivo.name.toLowerCase().endsWith(".pdf")) {
      setError("O arquivo selecionado deve estar no formato .pdf.");
      return;
    }

    const formData = new FormData();
    formData.append("especialidade", especialidadeId);
    formData.append("competencia", competencia);
    formData.append("arquivo", arquivo);
    if (observacao.trim()) {
      formData.append("observacao", observacao.trim());
    }

    setSubmitting(true);
    try {
      const resultado = await apiFetch<AtualizacaoFilaResposta>(
        apiRoutes.filaPublicacoes,
        {
          method: "POST",
          body: formData,
        },
      );
      setEspecialidadeId("");
      setCompetencia(getCurrentMonthISO());
      setObservacao("");
      setArquivo(null);
      onSuccess(resultado);
      onClose();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível atualizar a fila de espera.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="atualizar-fila-titulo"
    >
      <div className="w-full max-w-lg overflow-hidden rounded-2xl border bg-white shadow-xl">
        <div className="flex items-center justify-between bg-[#002A58] px-6 py-4 text-white">
          <div>
            <h2 id="atualizar-fila-titulo" className="text-lg font-semibold">
              Atualizar Fila de Espera
            </h2>
            <p className="text-xs text-blue-100">
              Importe o novo relatório PDF para atualizar os registros da especialidade.
            </p>
          </div>
          <button
            type="button"
            onClick={resetAndClose}
            disabled={submitting}
            className="rounded-lg p-1.5 text-blue-100 transition hover:bg-white/10 hover:text-white disabled:opacity-50"
            aria-label="Fechar modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-6">
          {error && (
            <div
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
              role="alert"
            >
              {error}
            </div>
          )}

          <label className="flex flex-col gap-1.5 text-sm font-medium text-[#002A58]">
            Especialidade *
            <select
              value={especialidadeId}
              onChange={(event) => setEspecialidadeId(event.target.value)}
              disabled={submitting}
              required
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm font-normal text-slate-700 outline-none focus:border-[#004080] focus:ring-2 focus:ring-[#004080]/15"
            >
              <option value="">Selecione uma especialidade...</option>
              {especialidades
                .filter((item) => item.ativo)
                .map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.tipo_display} — {item.nome}
                  </option>
                ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5 text-sm font-medium text-[#002A58]">
            Competência (Mês/Ano) *
            <input
              type="month"
              value={competencia}
              onChange={(event) => setCompetencia(event.target.value)}
              disabled={submitting}
              required
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm font-normal text-slate-700 outline-none focus:border-[#004080] focus:ring-2 focus:ring-[#004080]/15"
            />
          </label>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-[#002A58]">
              Relatório PDF da Regulação *
            </span>
            <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50/70 px-4 py-5 text-center transition hover:border-[#004080] hover:bg-blue-50/30">
              {arquivo ? (
                <div className="flex items-center gap-2 text-sm font-medium text-[#002A58]">
                  <FileText className="h-5 w-5 text-[#004080]" />
                  <span className="max-w-[280px] truncate">{arquivo.name}</span>
                  <span className="text-xs font-normal text-slate-500">
                    ({(arquivo.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              ) : (
                <>
                  <Upload className="h-6 w-6 text-[#004080]" />
                  <span className="text-sm font-medium text-slate-700">
                    Clique para selecionar o arquivo PDF
                  </span>
                  <span className="text-xs text-slate-500">
                    Apenas arquivos .pdf gerados pelo sistema de regulação
                  </span>
                </>
              )}
              <input
                type="file"
                accept=".pdf,application/pdf"
                disabled={submitting}
                onChange={(event) => {
                  const selected = event.target.files?.[0] ?? null;
                  setArquivo(selected);
                  setError("");
                }}
                className="sr-only"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1.5 text-sm font-medium text-[#002A58]">
            Observação (opcional)
            <textarea
              rows={3}
              maxLength={2000}
              value={observacao}
              onChange={(event) => setObservacao(event.target.value)}
              disabled={submitting}
              placeholder="Ex: Atualização quinzenal enviada pela Central de Regulação..."
              className="rounded-md border border-slate-300 bg-white p-3 text-sm font-normal text-slate-700 outline-none focus:border-[#004080] focus:ring-2 focus:ring-[#004080]/15"
            />
          </label>

          <div className="mt-2 flex items-center justify-end gap-2 border-t pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={resetAndClose}
              disabled={submitting}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              className="gap-2 bg-[#004080] text-white hover:bg-[#002A58]"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processando PDF...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Atualizar Fila
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}