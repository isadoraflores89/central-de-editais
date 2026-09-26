import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible } from "next/font/google";
import Link from "next/link";

import { CadastroProvider } from "@/components/Cadastro";
import { LinkApoio } from "@/components/Chamadas";
import { configSite } from "@/lib/dados";

import "./globals.css";

// Atkinson Hyperlegible: fonte desenhada para leitores com baixa visão.
const atkinson = Atkinson_Hyperlegible({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--fonte-atkinson",
  display: "swap",
});

const SITE = process.env.NEXT_PUBLIC_SITE_URL;

export const metadata: Metadata = {
  metadataBase: SITE ? new URL(SITE) : undefined,
  title: { default: "Central de Editais", template: "%s | Central de Editais" },
  description:
    "Radar gratuito de editais, patrocínios e credenciamentos culturais do Brasil, atualizado todos os dias, com filtros por estado, mecanismo, prazo e valor.",
  openGraph: { type: "website", locale: "pt_BR", siteName: "Central de Editais" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#1f3a2e" },
    { media: "(prefers-color-scheme: dark)", color: "#111413" },
  ],
};

const NAV = [
  { href: "/", rotulo: "Editais" },
  { href: "/parecerista/", rotulo: "Parecerista" },
  { href: "/lei-do-esporte/", rotulo: "Lei do Esporte" },
  { href: "/sobre/", rotulo: "Sobre" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={atkinson.variable}>
      <body>
        <CadastroProvider endpoint={configSite().cadastro_endpoint ?? ""}>
        <a href="#conteudo" className="pular-link">Pular para o conteúdo</a>
        <header className="bg-marca text-marca-texto">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
            <Link href="/" className="text-[1.5rem] font-bold no-underline">
              Central de Editais
            </Link>
            <nav aria-label="Principal">
              <ul className="flex flex-wrap gap-x-5 gap-y-1">
                {NAV.map((n) => (
                  <li key={n.href}>
                    <Link href={n.href} className="alvo inline-flex items-center font-bold underline decoration-2">
                      {n.rotulo}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </header>
        <main id="conteudo" className="mx-auto max-w-6xl px-4 py-6">
          {children}
        </main>
        <footer className="mt-12 border-t-2 border-borda-suave">
          <div className="mx-auto max-w-6xl px-4 py-8 text-suave">
            <p>
              Mantido por <strong className="text-texto">Flores Produções</strong> e pelo{" "}
              <a href="https://labgarra.art.br" className="font-bold text-acento underline">Ponto de Cultura Lab Garra</a>.
            </p>
            <p className="mt-2">
              Código aberto sob licença MIT. Dados sob CC BY 4.0, com atribuição às fontes.
              Confira sempre prazos e regras no edital oficial antes de se inscrever.{" "}
              <Link href="/privacidade/" className="font-bold text-acento underline">Política de Privacidade</Link>.
            </p>
            <div className="mt-2"><LinkApoio /></div>
          </div>
        </footer>
        </CadastroProvider>
      </body>
    </html>
  );
}
