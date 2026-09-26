import type { Metadata } from "next";
import QRCode from "qrcode";

import { Consultoria } from "@/components/Chamadas";
import { CopiarPix } from "@/components/CopiarPix";
import { configSite } from "@/lib/dados";
import { brCode } from "@/lib/pix";

export const metadata: Metadata = {
  title: "Apoie",
  description: "A Central de Editais é gratuita e independente. Apoie com um PIX ou mensalmente pelo Apoia.se.",
};

export default async function Apoie() {
  const a = configSite().apoio ?? {};
  const pix = a.pix_chave ? brCode(a.pix_chave, a.pix_nome ?? "", a.pix_cidade ?? "") : null;
  const qr = pix ? await QRCode.toString(pix, { type: "svg", margin: 2, width: 260 }) : null;

  return (
    <article className="max-w-3xl">
      <h1 className="text-[2rem] font-bold leading-tight">Apoie a Central de Editais</h1>
      <p className="mt-4 text-[1.1rem]">
        A Central é gratuita, aberta e feita por uma produtora cultural e um Ponto de Cultura.
        Manter o robô, a curadoria e a newsletter dá trabalho todo dia. Se ela te ajudou a achar
        um edital, pague um café para a equipe.
      </p>

      {!pix && !a.apoiase_url && (
        <p className="mt-8 rounded-lg border-2 border-borda-suave p-4">
          As formas de apoio estarão disponíveis em breve.
        </p>
      )}

      {pix && qr && (
        <section aria-labelledby="t-pix" className="mt-8 rounded-xl border-2 border-borda-suave bg-superficie p-5">
          <h2 id="t-pix" className="text-[1.4rem] font-bold">Cafezinho por PIX</h2>
          <p className="mt-2">Qualquer valor. Aponte a câmera do app do banco para o QR code ou use o copia e cola.</p>
          <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-start">
            <div
              role="img"
              aria-label="QR code do PIX para apoiar a Central de Editais"
              className="w-[260px] shrink-0 rounded-lg bg-white p-2"
              dangerouslySetInnerHTML={{ __html: qr }}
            />
            <div className="flex flex-col gap-3">
              <CopiarPix codigo={pix} rotulo="Copiar código PIX (copia e cola)" />
              <p>Chave PIX: <strong className="break-all">{a.pix_chave}</strong></p>
              {a.pix_nome && <p>Recebedor: {a.pix_nome}</p>}
            </div>
          </div>
        </section>
      )}

      {a.apoiase_url && (
        <section aria-labelledby="t-apoiase" className="mt-6 rounded-xl border-2 border-borda-suave bg-superficie p-5">
          <h2 id="t-apoiase" className="text-[1.4rem] font-bold">Apoio mensal</h2>
          <p className="mt-2">
            Quem apoia todo mês pelo Apoia.se recebe alertas de editais novos por e-mail e
            WhatsApp, com a frequência que escolher (conforme o valor do apoio).
          </p>
          <a
            href={a.apoiase_url}
            target="_blank"
            rel="noopener noreferrer"
            className="alvo mt-3 inline-flex items-center rounded-lg border-2 border-marca px-4 py-2 font-bold text-acento"
          >
            Apoiar pelo Apoia.se <span className="sr-only">(abre em nova aba)</span>
          </a>
        </section>
      )}

      <div className="mt-8"><Consultoria /></div>
    </article>
  );
}
