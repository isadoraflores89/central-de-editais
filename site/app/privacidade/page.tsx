import type { Metadata } from "next";

import { configSite } from "@/lib/dados";

export const metadata: Metadata = {
  title: "Política de Privacidade",
  description: "Como a Central de Editais trata os dados do cadastro, conforme a LGPD.",
};

const ATUALIZADA = "26/09/2026";

export default function Privacidade() {
  const email = configSite().consultoria?.email ?? "projetos@isadoraflores.art.br";
  const h2 = "mt-8 text-[1.4rem] font-bold";
  return (
    <article className="max-w-3xl">
      <h1 className="text-[2rem] font-bold leading-tight">Política de Privacidade</h1>
      <p className="mt-2 text-suave">Atualizada em {ATUALIZADA}.</p>

      <p className="mt-4 text-[1.1rem]">
        A lista de editais da Central é aberta a todas as pessoas. Para abrir links de inscrição,
        editais oficiais e baixar planilhas, pedimos um cadastro gratuito. Esta página explica,
        em linguagem simples, o que fazemos com esses dados, conforme a Lei Geral de Proteção de
        Dados (Lei 13.709/2018).
      </p>

      <h2 className={h2}>Quem cuida dos dados</h2>
      <p className="mt-2">
        Flores Educação e Cultura Ltda. (Flores Produções), CNPJ 18.376.163/0001-39, em parceria
        com o Ponto de Cultura Lab Garra. Contato para qualquer assunto sobre seus dados:{" "}
        <a className="font-bold text-acento underline" href={`mailto:${email}`}>{email}</a>.
      </p>

      <h2 className={h2}>Quais dados coletamos</h2>
      <ul className="mt-2 list-disc pl-6">
        <li>no cadastro: nome, e-mail, WhatsApp (opcional), estado, cidade (opcional), como você se inscreve em editais e sua área;</li>
        <li>suas escolhas: se quer receber a newsletter e se tem interesse em consultoria;</li>
        <li>a página e o edital que você estava abrindo quando se cadastrou.</li>
      </ul>
      <p className="mt-2">
        Não usamos cookies de rastreamento nem anúncios. O site guarda no seu próprio navegador
        apenas a informação de que você já se cadastrou, para não pedir de novo.
      </p>

      <h2 className={h2}>Para que usamos</h2>
      <ul className="mt-2 list-disc pl-6">
        <li>liberar o acesso aos links e downloads;</li>
        <li>entender quem usa a Central (estados, áreas, perfis) e melhorar o serviço;</li>
        <li>entrar em contato sobre editais e sobre a consultoria da Flores Produções;</li>
        <li>enviar a newsletter, somente se você marcou essa opção.</li>
      </ul>
      <p className="mt-2">
        A base legal é o seu consentimento, dado ao marcar o aceite no cadastro. Você pode
        retirá-lo quando quiser.
      </p>

      <h2 className={h2}>Onde os dados ficam e com quem compartilhamos</h2>
      <p className="mt-2">
        Em uma planilha privada do Google e no sistema interno de contatos da Flores Produções
        (Google Firebase). O Google atua apenas como fornecedor de armazenamento. Não vendemos
        nem cedemos seus dados a terceiros.
      </p>

      <h2 className={h2}>Por quanto tempo</h2>
      <p className="mt-2">
        Enquanto você mantiver o cadastro. Se não houver nenhum contato ou acesso por 2 anos,
        os dados são apagados.
      </p>

      <h2 className={h2}>Seus direitos</h2>
      <p className="mt-2">
        Você pode pedir a qualquer momento para ver, corrigir ou apagar seus dados, ou para
        deixar de receber mensagens. Basta escrever para{" "}
        <a className="font-bold text-acento underline" href={`mailto:${email}?subject=${encodeURIComponent("Meus dados na Central de Editais")}`}>{email}</a>{" "}
        com o assunto &quot;Meus dados na Central de Editais&quot;. Respondemos em até 15 dias.
      </p>
    </article>
  );
}
