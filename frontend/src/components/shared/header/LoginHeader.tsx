import { Logo } from "./subcomponents/Logo";
import { NavLinks } from "./subcomponents/NavLinks";

export function LoginHeader() {
  return (
    <header className="w-full bg-white border-b border-[#D1D1D1] shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-6">
        {/* Logo */}
        <Logo variant="light" />

        {/* Navegação central */}
        <NavLinks />
      </div>
    </header>
  );
}
