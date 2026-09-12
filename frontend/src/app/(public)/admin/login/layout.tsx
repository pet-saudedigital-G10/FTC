import { LoginHeader } from "@/components/shared/header/LoginHeader";

export default function PublicLayout({
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
