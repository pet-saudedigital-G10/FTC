import Link from "next/link";
import { ArrowRight, ShieldCheck, UserRound } from "lucide-react";
import { PublicHeader } from "@/components/shared/header/PublicHeader";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <PublicHeader />
      <main className="flex-1">
        <section className="bg-[#002A58] px-4 py-20 text-white sm:px-6">
          <div className="mx-auto max-w-6xl">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-200">
              Fila Transparente Cidadã
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
              Acompanhe solicitações de saúde com clareza e segurança.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-blue-100 sm:text-lg">
              Consulte sua posição, situação e prioridade usando uma conta vinculada ao seu CPF.
            </p>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-5 px-4 py-10 sm:px-6 md:grid-cols-2">
          <AccessCard
            href="/login"
            title="Sou cidadão"
            description="Acesse somente as solicitações vinculadas ao seu cadastro de paciente."
            icon={<UserRound className="h-6 w-6" />}
          />
          <AccessCard
            href="/admin/login"
            title="Acesso administrativo"
            description="Consulte publicações, filtros e registros das filas da secretaria."
            icon={<ShieldCheck className="h-6 w-6" />}
          />
        </section>
      </main>
    </div>
  );
}

function AccessCard({
  href,
  title,
  description,
  icon,
}: {
  href: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group rounded-xl border bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-[#004080]/40 hover:shadow-md"
    >
      <span className="grid h-11 w-11 place-items-center rounded-lg bg-blue-50 text-[#004080]">
        {icon}
      </span>
      <h2 className="mt-5 text-xl font-semibold text-[#002A58]">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
      <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-[#004080]">
        Entrar <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
      </span>
    </Link>
  );
}
