import Link from "next/link";
import { MapPin } from "lucide-react";

interface LogoProps {
  variant?: "light" | "dark";
}

export function Logo({ variant = "light" }: LogoProps) {
  const isLight = variant === "light";

  return (
    <Link
      href="/"
      className="flex items-center gap-2 font-semibold text-lg no-underline select-none"
    >
      <MapPin
        className={`w-5 h-5 flex-shrink-0 ${
          isLight ? "text-[#004080]" : "text-white"
        }`}
        strokeWidth={2.5}
      />
      <span
        className={`whitespace-nowrap ${
          isLight ? "text-[#004080]" : "text-white"
        }`}
      >
        Fila Transparente Cidadã
      </span>
    </Link>
  );
}
