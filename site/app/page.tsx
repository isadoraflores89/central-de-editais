import type { Metadata } from "next";

// A porta de entrada única é editais.isadoraflores.art.br (decisão de 01/11/2026).
// Esta página só encaminha quem chega aqui. As páginas de cada edital (/edital/<id>),
// a API (/api/*) e a pasta content/ continuam no ar neste domínio, porque o painel
// de assinantes e a newsletter dependem delas.
const DESTINO = "https://editais.isadoraflores.art.br/";

export const metadata: Metadata = {
  title: "Editais da Isa",
  robots: { index: false, follow: true },
  alternates: { canonical: DESTINO },
};

export default function Inicio() {
  return (
    <>
      <meta httpEquiv="refresh" content={`0; url=${DESTINO}`} />
      <script dangerouslySetInnerHTML={{ __html: `location.replace(${JSON.stringify(DESTINO)});` }} />
      <section className="mx-auto max-w-2xl py-16 text-center">
        <h1 className="font-display text-3xl">A Central de Editais mudou de endereço.</h1>
        <p className="mt-4 text-lg">
          Agora tudo fica em <a className="underline" href={DESTINO}>editais.isadoraflores.art.br</a>. Você será levada
          para lá em um instante.
        </p>
      </section>
    </>
  );
}
