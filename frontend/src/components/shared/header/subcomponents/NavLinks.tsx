"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navLinks = [
  { label: "Início", href: "/" },
  { label: "Acesso cidadão", href: "/login" },
  { label: "Acesso administrativo", href: "/admin/login" },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="hidden md:flex items-center gap-1">
      {navLinks.map((link) => {
        const isActive = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`
              relative px-4 py-2 text-sm font-medium transition-colors
              ${
                isActive
                  ? "text-[#004080]"
                  : "text-[#002A58]/70 hover:text-[#004080]"
              }
            `}
          >
            {link.label}
            {isActive && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#004080] rounded-full" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}
