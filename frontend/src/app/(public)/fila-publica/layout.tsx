import { PublicHeader } from "@/components/shared/header/PublicHeader";

export default function FilaPublicaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <PublicHeader />
      <main className="flex-1">{children}</main>
    </>
  );
}

