"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

const TRANSPARENCIA_PATH = "/transparencia";

export function TransparenciaLinkCard() {
  const [copied, setCopied] = useState("");
  const link = `${window.location.origin}${TRANSPARENCIA_PATH}`;
  const iframe = `<iframe src="${link}" title="Fila da saúde" width="100%" height="900" style="border:0"></iframe>`;

  async function copy(label: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
    } catch {
      setCopied("");
    }
  }

  return (
    <section className="rounded-xl border bg-white p-5 shadow-sm">
      <h2 className="font-semibold text-[#002A58]">Link para o Portal da Transparência</h2>
      <p className="mt-1 text-sm text-slate-500">
        Página pública, sem login, com indicadores agregados e consulta de posição. Use o
        link direto ou incorpore a página no portal da prefeitura.
      </p>
      <div className="mt-4 flex flex-col gap-3">
        <CopyRow
          label="Link público"
          value={link}
          copied={copied === "link"}
          onCopy={() => void copy("link", link)}
        />
        <CopyRow
          label="Código para incorporar"
          value={iframe}
          copied={copied === "iframe"}
          onCopy={() => void copy("iframe", iframe)}
        />
      </div>
    </section>
  );
}

function CopyRow({
  label,
  value,
  copied,
  onCopy,
}: {
  label: string;
  value: string;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="flex flex-col gap-1.5 text-sm font-medium text-[#002A58]">
      {label}
      <div className="flex gap-2">
        <input
          readOnly
          value={value}
          aria-label={label}
          className="h-10 min-w-0 flex-1 rounded-md border border-slate-300 bg-slate-50 px-3 font-mono text-xs font-normal text-slate-700"
        />
        <Button type="button" variant="outline" onClick={onCopy} className="h-10">
          {copied ? "Copiado" : "Copiar"}
        </Button>
      </div>
    </div>
  );
}
