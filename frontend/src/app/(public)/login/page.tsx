import { CidadaoLoginCard } from "./subcomponents/CidadaoLoginCard";

export default function LoginCidadaoPage() {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#f4f6f9] flex items-center justify-center">
      <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 flex justify-center">
        <CidadaoLoginCard />
      </div>
    </div>
  );
}