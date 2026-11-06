import { ShieldCheck } from "lucide-react";
import { CidadaoLoginForm } from "./CidadaoLoginForm";

export function CidadaoLoginCard() {
  return (
    <div className="w-full max-w-md bg-white border border-[#D1D1D1] rounded-2xl shadow-md p-6 sm:p-8 flex flex-col gap-6">
      
      {/* Cabeçalho Leve e Convidativo */}
      <div className="text-center flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-[#002A58]">Acesse sua Conta</h1>
        <p className="text-sm text-[#002A58]/70">
          Insira seus dados para acessar sua conta.
        </p>
      </div>

      {/* Formulário de Autenticação */}
      <CidadaoLoginForm />

      {/* Box de Segurança / LGPD */}
      <div className="mt-2 bg-[#f8fafd] rounded-lg p-4 flex items-start gap-3 border-l-4 border-[#004080]">
        <ShieldCheck className="w-5 h-5 text-[#004080] shrink-0 mt-0.5" />
        <p className="text-xs text-[#002A58]/70 leading-relaxed">
          <strong className="text-[#002A58]">Ambiente Seguro:</strong> Seus dados estão protegidos em conformidade com a LGPD.
        </p>
      </div>
      
    </div>
  );
}