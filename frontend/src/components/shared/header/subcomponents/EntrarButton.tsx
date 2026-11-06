import Link from "next/link";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EntrarButton() {
  return (
    <Button
      className="bg-[#004080] text-white hover:bg-[#002A58] font-semibold px-5 gap-2 transition-colors"
      render={<Link href="/login" />}
      nativeButton={false}
    >
      Entrar
      <LogIn className="w-4 h-4" />
    </Button>
  );
}
