"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, apiFetch, onlyDigits } from "@/lib/api";
import { apiRoutes } from "@/lib/api-routes";
import type { SisregConfiguracao, SisregTesteConexao } from "@/lib/api-types";

const PORTAL_URL =
  "https://portalservicos-datasus.saude.gov.br/portfolio/NSsGTvxYk0";

const fieldClass =
  "h-10 rounded-md border border-slate-300 bg-white px-3 text-sm font-normal text-slate-700 outline-none focus:border-[#004080] focus:ring-2 focus:ring-[#004080]/15";

type FieldErrors = Record<string, string>;

function errorsFrom(error: unknown): FieldErrors {
  if (!(error instanceof ApiError) || typeof error.body !== "object" || !error.body) {
    return {};
  }
  const errors: FieldErrors = {};
  for (const [field, value] of Object.entries(error.body)) {
    errors[field] = Array.isArray(value)
      ? value.join(" ")
      : typeof value === "string"
        ? value
        : "Verifique o valor informado.";
  }
  return errors;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function SisregConfigForm({ onSaved }: { onSaved: () => void }) {
  const [loading, setLoading] = useState(true);
  const [habilitado, setHabilitado] = useState(false);
  const [ambiente, setAmbiente] = useState("homologacao");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [secretConfigurado, setSecretConfigurado] = useState(false);
  const [indice, setIndice] = useState("");
  const [centrais, setCentrais] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState("");
  const [message, setMessage] = useState("");

  function fill(config: SisregConfiguracao) {
    setHabilitado(config.habilitado);
    setAmbiente(config.ambiente);
    setClientId(config.client_id);
    setClientSecret("");
    setSecretConfigurado(config.client_secret_configurado);
    setIndice(config.indice);
    setCentrais(config.centrais_reguladoras.join(", "));
  }

  useEffect(() => {
    let active = true;
    async function loadConfig() {
      try {
        const config = await apiFetch<SisregConfiguracao>(
          apiRoutes.sisregConfiguracao,
          { cache: "no-store" },
        );
        if (active) fill(config);
      } catch (requestError) {
        if (active) {
          setFormError(
            errorMessage(requestError, "Não foi possível carregar a configuração."),
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadConfig();
    return () => {
      active = false;
    };
  }, []);

  function requestBody() {
    return JSON.stringify({
      habilitado,
      ambiente,
      client_id: clientId,
      client_secret: clientSecret,
      indice: indice.trim(),
      centrais_reguladoras: centrais
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    });
  }

  function clearFeedback() {
    setErrors({});
    setFormError("");
    setMessage("");
  }

  function showError(error: unknown, fallback: string) {
    const fields = errorsFrom(error);
    setErrors(fields);
    if (!Object.keys(fields).some((field) => field !== "detail")) {
      setFormError(errorMessage(error, fallback));
    }
  }

  async function handleTest() {
    clearFeedback();
    setTesting(true);
    try {
      const result = await apiFetch<SisregTesteConexao>(apiRoutes.sisregTestar, {
        method: "POST",
        body: requestBody(),
      });
      setMessage(
        `Conexão bem-sucedida: ${result.total} registros no índice. Os dados ainda não foram salvos.`,
      );
    } catch (requestError) {
      showError(requestError, "Não foi possível testar a conexão.");
    } finally {
      setTesting(false);
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    clearFeedback();
    setSaving(true);
    try {
      const config = await apiFetch<SisregConfiguracao>(
        apiRoutes.sisregConfiguracao,
        { method: "PUT", body: requestBody() },
      );
      fill(config);
      setMessage(
        config.habilitado
          ? "Configuração salva. A integração está ativa."
          : "Configuração salva. A integração está desligada.",
      );
      onSaved();
    } catch (requestError) {
      showError(requestError, "Não foi possível salvar a configuração.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Carregando a configuração...</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <p className="max-w-3xl text-sm text-slate-600">
        Informe os dados da credencial aprovada no{" "}
        <a
          href={PORTAL_URL}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-[#004080] hover:underline"
        >
          Portal de Serviços do DATASUS
        </a>
        . Use homologação até validar a integração.
      </p>

      <label className="flex items-center gap-2 text-sm font-medium text-[#002A58]">
        <input
          type="checkbox"
          checked={habilitado}
          onChange={(event) => setHabilitado(event.target.checked)}
          className="h-4 w-4 accent-[#004080]"
        />
        Integração ativa
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Ambiente" error={errors.ambiente}>
          <select
            value={ambiente}
            onChange={(event) => setAmbiente(event.target.value)}
            className={fieldClass}
          >
            <option value="homologacao">Homologação</option>
            <option value="producao">Produção</option>
          </select>
        </Field>

        <Field label="Client ID (CNES)" error={errors.client_id}>
          <input
            type="text"
            inputMode="numeric"
            value={clientId}
            onChange={(event) => setClientId(onlyDigits(event.target.value).slice(0, 7))}
            placeholder="0000000"
            autoComplete="off"
            className={fieldClass}
          />
        </Field>

        <Field
          label="Client Secret"
          error={errors.client_secret}
          hint="Gravado de forma criptografada e nunca exibido novamente."
        >
          <input
            type="password"
            value={clientSecret}
            onChange={(event) => setClientSecret(event.target.value)}
            placeholder={
              secretConfigurado ? "Em branco mantém o valor salvo" : "Secret gerado no Portal"
            }
            autoComplete="new-password"
            className={fieldClass}
          />
        </Field>

        <Field
          label="Índice"
          error={errors.indice}
          hint="Solicitações ambulatoriais, conforme liberado na credencial."
        >
          <input
            type="text"
            value={indice}
            onChange={(event) => setIndice(event.target.value)}
            placeholder="solicitacao-ambulatorial-es-vitoria"
            autoComplete="off"
            className={fieldClass}
          />
        </Field>

        <Field
          label="Centrais reguladoras (opcional)"
          error={errors.centrais_reguladoras}
          hint="Códigos separados por vírgula. Em branco, consulta todo o índice."
        >
          <input
            type="text"
            value={centrais}
            onChange={(event) => setCentrais(event.target.value)}
            placeholder="32C164, 32C206"
            autoComplete="off"
            className={fieldClass}
          />
        </Field>
      </div>

      {formError && (
        <p className="text-sm text-red-700" role="alert">{formError}</p>
      )}
      {message && (
        <p className="text-sm font-medium text-green-700" role="status">{message}</p>
      )}

      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={saving || testing}>
          {saving ? "Salvando..." : "Salvar configuração"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => void handleTest()}
          disabled={saving || testing}
        >
          {testing ? "Testando..." : "Testar conexão"}
        </Button>
      </div>
    </form>
  );
}

function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-medium text-[#002A58]">
      {label}
      {children}
      {error ? (
        <span className="text-xs font-normal text-red-700">{error}</span>
      ) : hint ? (
        <span className="text-xs font-normal text-slate-500">{hint}</span>
      ) : null}
    </label>
  );
}
