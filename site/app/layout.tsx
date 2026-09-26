import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible, Bricolage_Grotesque } from "next/font/google";
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

// Bricolage Grotesque: só em títulos e números grandes (personalidade editorial).
const display = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--fonte-display",
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
  { href: "/apoie/", rotulo: "Apoie" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${atkinson.variable} ${display.variable}`}>
      <body>
        <CadastroProvider endpoint={configSite().cadastro_endpoint ?? ""}>
        <a href="#conteudo" className="pular-link">Pular para o conteúdo</a>
        <header className="listras bg-cabecalho text-cabecalho-texto">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
            <Link href="/" className="inline-flex items-center gap-3 no-underline" aria-label="Central de Editais, página inicial">
              <Marca />
              <span className="titulo-display text-[1.7rem] font-extrabold">Central de Editais</span>
            </Link>
            <nav aria-label="Principal">
              <ul className="flex flex-wrap gap-x-6 gap-y-1">
                {NAV.filter((n) => n.href !== "/apoie/" || temApoio()).map((n) => (
                  <li key={n.href}>
                    <Link href={n.href} className="alvo inline-flex items-center font-bold underline decoration-amarelo decoration-[3px] underline-offset-[6px] hover:decoration-[5px]">
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
        <footer className="mt-16 border-t-[6px] border-amarelo">
          <div className="mx-auto max-w-6xl px-4 py-8 text-suave">
            <p className="titulo-display mb-3 text-[1.5rem] font-extrabold text-texto">Central de Editais</p>
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

/** Marca: folha de edital com o canto dobrado e uma faixa amarela (decorativa). */
function Marca() {
  return (
    <svg viewBox="0 0 40 40" width="40" height="40" aria-hidden="true" focusable="false">
      <path d="M8 4h17l7 7v25H8z" fill="#fbfaf6" />
      <path d="M25 4v7h7" fill="#d9dccf" />
      <rect x="12" y="15" width="16" height="5" fill="#f4c542" />
      <rect x="12" y="23" width="16" height="2.5" fill="#1f3a2e" />
      <rect x="12" y="28" width="11" height="2.5" fill="#1f3a2e" />
    </svg>
  );
}

function temApoio(): boolean {
  const a = configSite().apoio;
  return Boolean(a?.pix_chave || a?.apoiase_url);
}
