import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Transparência da fila da saúde",
  description: "Indicadores das filas de regulação e consulta de posição.",
};

export default function TransparenciaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
