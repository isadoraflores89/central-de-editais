// Blocos de consultoria e newsletter. Cada um só aparece se estiver configurado
// em config/site.yaml.
import Link from "next/link";

import { configSite } from "@/lib/dados";

export function Consultoria() {
  const c = configSite().consultoria;
  if (!c?.email) return null;
  const assunto = encodeURIComponent("Consultoria para projeto cultural");
  return (
    <aside aria-labelledby="t-consultoria" className="rounded-xl border-2 border-marca bg-chip p-5">
      <h2 id="t-consultoria" className="text-[1.25rem] font-bold">{c.titulo}</h2>
      <p className="mt-2">{c.texto}</p>
      <a
        href={`mailto:${c.email}?subject=${assunto}`}
        className="alvo mt-3 inline-flex items-center rounded-lg bg-marca px-4 py-2 font-bold text-marca-texto"
      >
        Fale com a gente: {c.email}
      </a>
    </aside>
  );
}

export function Newsletter() {
  const url = configSite().substack_url?.replace(/\/+$/, "");
  if (!url) return null;
  return (
    <aside aria-labelledby="t-newsletter" className="rounded-xl border-2 border-borda-suave bg-superficie p-5">
      <h2 id="t-newsletter" className="text-[1.25rem] font-bold">Receba as novidades por e-mail</h2>
      <p className="mt-2">
        A cada 15 dias, os editais novos, os prorrogados e os que estão para fechar. Grátis.
      </p>
      <iframe
        src={`${url}/embed`}
        title="Formulário de inscrição na newsletter da Central de Editais (Substack)"
        className="mt-3 h-[150px] w-full max-w-md rounded-lg border border-borda-suave bg-white"
        loading="lazy"
      />
      <p className="mt-2">
        <a href={`${url}/subscribe`} className="font-bold text-acento underline" target="_blank" rel="noopener noreferrer">
          Assinar direto no Substack
        </a>
      </p>
    </aside>
  );
}

export function LinkApoio() {
  const a = configSite().apoio;
  if (!a?.pix_chave && !a?.apoiase_url) return null;
  return (
    <p>
      A Central é gratuita e independente.{" "}
      <Link href="/apoie/" className="font-bold text-acento underline">Apoie com um cafezinho</Link>.
    </p>
  );
}
