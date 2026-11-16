import { LoginHeader } from "@/components/shared/header/LoginHeader";

export default function CadastroLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <LoginHeader />
      <main className="flex-1">{children}</main>
    </>
  );
}
