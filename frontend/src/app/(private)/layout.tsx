import { PrivateShell } from "@/components/private-shell";

export default function PrivateLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <PrivateShell>{children}</PrivateShell>;
}
