import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import type { RegistroFila } from "./api-types";

export interface ExportFilaItem {
  posicao: number;
  especialidade: string;
  categoria: string;
  paciente: string;
  codigoSolicitacao: string;
  tipo: string;
  prioridade: string;
  situacao: string;
  dataSolicitacao: string;
}

export interface ExportFilaMetadata {
  filtrosAtivos?: string[];
}

function formatDateBR(value: string): string {
  if (!value) return "";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`));
}

function escapeCSV(value: string | number): string {
  const text = String(value ?? "");
  if (/[;"\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function mapRegistrosParaExportacao(
  registros: RegistroFila[],
  tiposMap?: Record<string, string>,
): ExportFilaItem[] {
  return registros.map((registro) => ({
    posicao: registro.posicao,
    especialidade: registro.especialidade_nome,
    categoria: registro.especialidade_tipo_display,
    paciente: registro.nome_mascarado,
    codigoSolicitacao: registro.codigo_solicitacao,
    tipo: tiposMap?.[registro.tipo] ?? registro.tipo,
    prioridade: registro.prioridade_display,
    situacao: registro.situacao_display,
    dataSolicitacao: formatDateBR(registro.data_solicitacao),
  }));
}

export function exportarRegistrosCSV(
  registros: RegistroFila[],
  tiposMap?: Record<string, string>,
) {
  const itens = mapRegistrosParaExportacao(registros, tiposMap);

  const cabecalho = [
    "Posição",
    "Especialidade",
    "Categoria",
    "Paciente",
    "Código da Solicitação",
    "Tipo",
    "Prioridade",
    "Situação",
    "Data da Solicitação",
  ];

  const linhas = itens.map((item) =>
    [
      item.posicao,
      item.especialidade,
      item.categoria,
      item.paciente,
      item.codigoSolicitacao,
      item.tipo,
      item.prioridade,
      item.situacao,
      item.dataSolicitacao,
    ]
      .map(escapeCSV)
      .join(";"),
  );

  const conteudo = `\uFEFF${[cabecalho.join(";"), ...linhas].join("\r\n")}`;
  const blob = new Blob([conteudo], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const dataAtual = new Date().toISOString().slice(0, 10);
  const link = document.createElement("a");
  link.href = url;
  link.download = `fila-de-espera-${dataAtual}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportarRegistrosPDF(
  registros: RegistroFila[],
  tiposMap?: Record<string, string>,
  metadata?: ExportFilaMetadata,
) {
  const itens = mapRegistrosParaExportacao(registros, tiposMap);
  const doc = new jsPDF({
    orientation: "landscape",
    unit: "mm",
    format: "a4",
  });

  const emitidoEm = new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date());

  const resumoFiltros =
    metadata?.filtrosAtivos && metadata.filtrosAtivos.length > 0
      ? metadata.filtrosAtivos.join(" | ")
      : "Nenhum filtro aplicado (todos os registros ativos)";

  // Cabeçalho do documento
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.setTextColor(0, 42, 88); // #002A58
  doc.text("Fila Transparente Cidadã", 14, 15);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  doc.setTextColor(71, 85, 105);
  doc.text(
    "Relatório da Lista de Espera Pública — Secretaria Municipal de Saúde",
    14,
    20.5,
  );

  doc.setFontSize(8.5);
  doc.setTextColor(51, 65, 85);
  doc.text(`Emitido em: ${emitidoEm}`, 283, 15, { align: "right" });
  doc.text(`Total de registros: ${itens.length}`, 283, 20.5, {
    align: "right",
  });

  // Linha divisória e resumo dos filtros
  doc.setDrawColor(0, 42, 88);
  doc.setLineWidth(0.5);
  doc.line(14, 23.5, 283, 23.5);

  const textoFiltros = doc.splitTextToSize(
    `Filtros aplicados: ${resumoFiltros}`,
    269,
  );
  doc.setFontSize(8.5);
  doc.text(textoFiltros, 14, 29);

  const startY = 29 + textoFiltros.length * 4 + 2;

  autoTable(doc, {
    startY,
    head: [
      [
        "Posição",
        "Especialidade",
        "Categoria",
        "Paciente",
        "Solicitação",
        "Tipo",
        "Prioridade",
        "Situação",
        "Data",
      ],
    ],
    body: itens.map((item) => [
      `#${item.posicao}`,
      item.especialidade,
      item.categoria,
      item.paciente,
      item.codigoSolicitacao,
      item.tipo,
      item.prioridade,
      item.situacao,
      item.dataSolicitacao,
    ]),
    styles: {
      fontSize: 8,
      cellPadding: 2.5,
      textColor: [15, 23, 42],
    },
    headStyles: {
      fillColor: [0, 42, 88], // #002A58
      textColor: [255, 255, 255],
      fontStyle: "bold",
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252],
    },
    margin: { left: 14, right: 14, bottom: 16 },
    didDrawPage: (data) => {
      const pageHeight = doc.internal.pageSize.getHeight();
      doc.setFontSize(7.5);
      doc.setTextColor(100, 116, 139);
      doc.text(
        "Dados exibidos conforme a Lei Geral de Proteção de Dados (LGPD - Lei nº 13.709/2018).",
        14,
        pageHeight - 8,
      );
      doc.text(
        `Página ${data.pageNumber}`,
        283,
        pageHeight - 8,
        { align: "right" },
      );
    },
  });

  const dataAtual = new Date().toISOString().slice(0, 10);
  doc.save(`fila-de-espera-${dataAtual}.pdf`);
}