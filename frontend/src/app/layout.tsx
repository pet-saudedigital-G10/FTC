import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const lexend = localFont({
  src: "../../public/fonts/Lexend/Lexend-VariableFont_wght.ttf",
  variable: "--font-lexend",
  weight: "100 900",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FTC",
  description: "FTC - Frontend",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className={`${lexend.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
