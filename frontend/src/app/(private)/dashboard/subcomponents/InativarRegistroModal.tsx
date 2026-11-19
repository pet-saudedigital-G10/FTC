"use client";

import { useState, type FormEvent } from "react";
import { AlertTriangle, Ban, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { apiRoutes } from "@/lib/api-routes";
import type {
  OperacaoRegistroResposta,
  RegistroFila,
} from "@/lib/api-types";

interface InativarRegistroModalProps {
  registro: RegistroFila | null;
  onClose: () => void;
  onSuccess: (registro: RegistroFila) => void;
}

export function InativarRegistroModal({
  registro,
  onClose,
  onSuccess,
}: InativarRegistroModalProps) {
  const [motivo, setMotivo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!registro) return null;

  function resetAndClose() {
    if (submitting) return;
    setMotivo("");
    setError("");
    onClose();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!registro) return;
    setError("");

    const motivoLimpo = motivo.trim();
    if (!motivoLimpo) {
      setError("O motivo da inativação é obrigatório.");
      return;
    }

    setSubmitting(true);
    try {
      await apiFetch<OperacaoRegistroResposta>(
        apiRoutes.filaRegistroInativar(registro.id),
        {
          method: "PATCH",
          body: JSON.stringify({ motivo: motivoLimpo }),
        },
      );
      setMotivo("");
      onSuccess(registro);
      onClose();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível inativar o registro.",
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
      aria-labelledby="inativar-registro-titulo"
    >
      <div className="w-full max-w-lg overflow-hidden rounded-2xl border bg-white shadow-xl">
        <div className="flex items-center justify-between bg-[#002A58] px-6 py-4 text-white">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="h-5 w-5 text-amber-300" />
            <div>
              <h2 id="inativar-registro-titulo" className="text-lg font-semibold">
                Inativar Registro da Fila
              </h2>
              <p className="text-xs text-blue-100">
                Esta operação é registrada na auditoria e oculta o paciente da fila pública.
              </p>
            </div>
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

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Registro selecionado
            </p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-slate-700">
              <div>
                <dt className="text-xs text-slate-500">Posição</dt>
                <dd className="font-semibold text-[#002A58]">#{registro.posicao}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Solicitação</dt>
                <dd className="font-mono text-xs font-medium text-slate-800">
                  {registro.codigo_solicitacao}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Paciente</dt>
                <dd className="font-medium text-slate-800">{registro.nome_mascarado}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Especialidade</dt>
                <dd className="font-medium text-slate-800">{registro.especialidade_nome}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-lg border border-amber-200 bg-amber-50/80 px-3.5 py-2.5 text-xs text-amber-900">
            Solicitações inativadas também são suprimidas automaticamente em futuras
            importações de PDF, até que sejam reativadas.
          </div>

          <label className="flex flex-col gap-1.5 text-sm font-medium text-[#002A58]">
            Motivo / Justificativa *
            <textarea
              rows={3}
              value={motivo}
              onChange={(event) => setMotivo(event.target.value)}
              disabled={submitting}
              required
              placeholder="Ex: Paciente desistiu do procedimento, solicitação duplicada ou atendimento já realizado..."
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
              disabled={submitting || !motivo.trim()}
              className="gap-2 bg-red-600 text-white hover:bg-red-700"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Inativando...
                </>
              ) : (
                <>
                  <Ban className="h-4 w-4" />
                  Confirmar Inativação
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}