import { Lock } from "lucide-react";
import { AdminLoginForm } from "./AdminLoginForm";

export function AdminLoginCard() {
  return (
    <div className="w-full max-w-md bg-white border border-[#D1D1D1] rounded-2xl shadow-lg overflow-hidden flex flex-col">
      {/* Cabeçalho do Card - Estilo Administrativo (Azul Presidencial) */}
      <div className="bg-[#002A58] p-6 text-white flex flex-col items-center gap-2 text-center">
        <div className="bg-white/10 p-3 rounded-full border border-white/20">
          <Lock className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-xl font-bold rounded-none">
          Identificação do Profissional
        </h1>
        <p className="text-sm text-white/80 max-w-xs">
          Insira suas credenciais para acessar o sistema.
        </p>
      </div>

      {/* Corpo do Card - Contém o formulário */}
      <div className="p-8">
        <AdminLoginForm />
      </div>

      {/* Rodapé do Card - Aviso de segurança simplificado */}
      <div className="px-8 pb-6 text-center">
        <span className="text-xs text-[#002A58]/50">
          Este é um sistema restrito.
        </span>
      </div>
    </div>
  );
}