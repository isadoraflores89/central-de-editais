import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sobre",
  description: "Como a Central de Editais funciona: fontes, metodologia, prioridade e licenças.",
};

const repo = process.env.NEXT_PUBLIC_REPO;

export default function Sobre() {
  return (
    <article className="max-w-3xl">
      <h1 className="text-[2rem] font-bold leading-tight">Sobre a Central de Editais</h1>
      <p className="mt-4 text-[1.1rem]">
        A Central de Editais reúne, num só lugar, editais, chamadas de patrocínio e
        credenciamentos do campo cultural brasileiro. É gratuita, de código aberto e mantida
        pela Flores Produções e pelo Ponto de Cultura Lab Garra.
      </p>

      <h2 className="mt-8 text-[1.4rem] font-bold">De onde vêm os dados</h2>
      <p className="mt-2">
        A primeira carga veio de uma curadoria manual feita em 24/09/2026. A partir dela, um robô
        consulta todos os dias as fontes oficiais: Ministério da Cultura, Mapa da Cultura, Funarte,
        Prosas, secretarias estaduais, PNCP e páginas de patrocínio de empresas. Todo registro guarda
        o link da fonte e a data em que foi capturado. Nada é inventado: se um prazo ou valor não
        aparece na fonte, o campo fica em branco.
      </p>

      <h2 className="mt-8 text-[1.4rem] font-bold">Como a lista é ordenada</h2>
      <p className="mt-2">Por padrão, cada edital recebe uma nota de prioridade de 0 a 100:</p>
      <ul className="mt-2 list-disc pl-6">
        <li>abrangência nacional: 25 pontos;</li>
        <li>Lei Rouanet, Lei do Esporte ou ICMS da Bahia ou do Paraná: 20;</li>
        <li>valor por projeto a partir de R$ 100 mil: 15;</li>
        <li>prazo entre 7 e 60 dias: 20 (entre 0 e 6 dias: 10; fluxo contínuo: 5);</li>
        <li>não exige projeto já aprovado em lei: 10;</li>
        <li>projeto na Bahia ou no Paraná: 10;</li>
        <li>destaque da curadoria: 30.</li>
      </ul>
      <p className="mt-2">Editais encerrados ficam com nota zero e saem da lista padrão, mas continuam no histórico.</p>

      <h2 className="mt-8 text-[1.4rem] font-bold">Dados abertos</h2>
      <p className="mt-2">Qualquer pessoa pode baixar e reutilizar os dados:</p>
      <ul className="mt-2 list-disc pl-6">
        <li><a className="text-acento underline" href={`${process.env.NEXT_PUBLIC_BASE_PATH}/api/editais.json`}>editais.json</a> (para programadores)</li>
        <li><a className="text-acento underline" href={`${process.env.NEXT_PUBLIC_BASE_PATH}/api/editais.csv`}>editais.csv</a></li>
        <li><a className="text-acento underline" href={`${process.env.NEXT_PUBLIC_BASE_PATH}/api/editais.xlsx`}>editais.xlsx</a> (Excel)</li>
      </ul>
      <p className="mt-2">
        Os dados estão sob a licença Creative Commons Atribuição 4.0 (CC BY 4.0): cite a Central de
        Editais e a fonte original de cada edital. O código é aberto sob licença MIT.
      </p>

      <h2 className="mt-8 text-[1.4rem] font-bold">Sugerir um edital ou corrigir um erro</h2>
      <p className="mt-2">
        Viu um edital que falta ou uma informação errada? Abra um aviso no{" "}
        <a className="font-bold text-acento underline" href={`https://github.com/${repo}/issues/new`}>
          GitHub do projeto
        </a>
        . Em cada página de edital há um link que já preenche o aviso para você.
      </p>

      <p className="mt-8 rounded-lg border-2 border-borda-suave p-4">
        Atenção: a Central organiza informações públicas, mas não substitui o edital oficial.
        Confira sempre prazos, valores e regras na página do órgão antes de se inscrever.
      </p>
    </article>
  );
}
