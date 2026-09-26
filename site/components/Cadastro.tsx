"use client";

// Cadastro pedido na hora de abrir o link de inscrição, o edital oficial ou baixar
// a planilha. A lista continua aberta a todos. Os dados vão para o Apps Script
// (integracoes/apps-script/Cadastros.gs), que só recebe e alimenta o CRM.

import Link from "next/link";
import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from "react";

import { AREAS, UFS } from "@/lib/rotulos";

const CHAVE = "central-cadastro-v1";
const PENDENTE = "central-cadastro-pendente-v1";

interface Pessoa { nome: string; email: string }
interface Pedido { rotulo: string; aoLiberar?: () => void; href?: string; edital?: string }

interface Ctx {
  ativo: boolean;
  pessoa: Pessoa | null;
  pedir: (p: Pedido) => void;
}

const Contexto = createContext<Ctx>({ ativo: false, pessoa: null, pedir: () => {} });

export const useCadastro = () => useContext(Contexto);

function ler<T>(chave: string): T | null {
  try {
    const v = localStorage.getItem(chave);
    return v ? (JSON.parse(v) as T) : null;
  } catch {
    return null;
  }
}
function gravar(chave: string, valor: unknown): void {
  try {
    if (valor === null) localStorage.removeItem(chave);
    else localStorage.setItem(chave, JSON.stringify(valor));
  } catch {
    /* navegador sem armazenamento: vale só nesta visita */
  }
}

async function enviar(endpoint: string, dados: Record<string, unknown>): Promise<{ ok: boolean; erro?: string }> {
  // text/plain evita a checagem prévia de CORS, que o Apps Script não responde.
  const r = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(dados) });
  return (await r.json()) as { ok: boolean; erro?: string };
}

const PERFIS: Record<string, string> = {
  pf: "Pessoa física (artista, produtor(a)...)",
  mei: "MEI",
  pj: "Empresa / produtora",
  osc: "Associação, ONG ou OSC",
  coletivo: "Coletivo ou grupo",
  poder_publico: "Poder público",
  outro: "Outro",
};

export function CadastroProvider({ endpoint, children }: { endpoint: string; children: React.ReactNode }) {
  const ativo = Boolean(endpoint);
  const [pessoa, setPessoa] = useState<Pessoa | null>(null);
  const [pedido, setPedido] = useState<Pedido | null>(null);

  useEffect(() => {
    setPessoa(ler<Pessoa>(CHAVE));
    // Reenvia um cadastro que não chegou da última vez (sem internet, por exemplo).
    const pend = ler<Record<string, unknown>>(PENDENTE);
    if (endpoint && pend) {
      enviar(endpoint, pend).then((r) => r.ok && gravar(PENDENTE, null)).catch(() => {});
    }
  }, [endpoint]);

  const pedir = useCallback((p: Pedido) => {
    if (!ativo || ler<Pessoa>(CHAVE) || pessoa) {
      p.aoLiberar?.();
      if (p.href) window.open(p.href, "_blank", "noopener");
      return;
    }
    setPedido(p);
  }, [ativo, pessoa]);

  return (
    <Contexto.Provider value={{ ativo, pessoa, pedir }}>
      {children}
      {pedido && (
        <Formulario
          endpoint={endpoint}
          pedido={pedido}
          aoFechar={() => setPedido(null)}
          aoCadastrar={(p) => { gravar(CHAVE, p); setPessoa(p); }}
        />
      )}
    </Contexto.Provider>
  );
}

function Formulario({
  endpoint, pedido, aoFechar, aoCadastrar,
}: { endpoint: string; pedido: Pedido; aoFechar: () => void; aoCadastrar: (p: Pessoa) => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [pronto, setPronto] = useState(false);

  useEffect(() => {
    const d = ref.current;
    if (d && !d.open) d.showModal();
  }, []);

  const aoEnviar = async (ev: React.FormEvent<HTMLFormElement>) => {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const dados = {
      nome: String(f.get("nome") ?? ""),
      email: String(f.get("email") ?? ""),
      whatsapp: String(f.get("whatsapp") ?? ""),
      uf: String(f.get("uf") ?? ""),
      cidade: String(f.get("cidade") ?? ""),
      perfil: String(f.get("perfil") ?? ""),
      area: String(f.get("area") ?? ""),
      consultoria: f.get("consultoria") === "on",
      newsletter: f.get("newsletter") === "on",
      aceite: f.get("aceite") === "on",
      site: String(f.get("site") ?? ""), // armadilha para robôs
      pagina: window.location.pathname,
      edital: pedido.edital ?? "",
    };
    setEnviando(true);
    setErro(null);
    try {
      const r = await enviar(endpoint, dados);
      if (!r.ok) {
        setErro(r.erro ? `Não deu certo: ${r.erro}.` : "Não deu certo. Confira os campos.");
        return;
      }
    } catch {
      // Sem conexão com o servidor: libera o acesso e tenta enviar de novo na próxima visita.
      gravar(PENDENTE, dados);
    } finally {
      setEnviando(false);
    }
    aoCadastrar({ nome: dados.nome, email: dados.email });
    pedido.aoLiberar?.();
    setPronto(true);
  };

  const fechar = () => { ref.current?.close(); aoFechar(); };
  const campo = "alvo w-full rounded-lg border-2 border-borda bg-superficie px-3 py-2 text-[1.05rem]";

  return (
    <dialog
      ref={ref}
      aria-labelledby={`${id}-t`}
      onClose={aoFechar}
      className="m-auto w-[min(40rem,calc(100vw-2rem))] max-h-[calc(100vh-2rem)] overflow-y-auto rounded-xl border-2 border-marca bg-superficie p-0 text-texto backdrop:bg-black/60"
    >
      <div className="p-6">
        {pronto ? (
          <>
            <h2 id={`${id}-t`} className="text-[1.5rem] font-bold">Cadastro feito. Obrigada!</h2>
            <p className="mt-3">Você não vai precisar se cadastrar de novo neste aparelho.</p>
            <div className="mt-5 flex flex-wrap gap-3">
              {pedido.href && (
                <a href={pedido.href} target="_blank" rel="noopener noreferrer" onClick={fechar}
                   className="alvo inline-flex items-center rounded-lg bg-marca px-5 py-2.5 font-bold text-marca-texto">
                  {pedido.rotulo} <span className="sr-only">(abre em nova aba)</span>
                </a>
              )}
              <button type="button" onClick={fechar} className="alvo rounded-lg border-2 border-borda px-5 py-2.5 font-bold">
                Fechar
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={aoEnviar} noValidate={false}>
            <h2 id={`${id}-t`} className="text-[1.5rem] font-bold">Cadastre-se para abrir o edital</h2>
            <p className="mt-2">
              É grátis e leva 1 minuto. Você faz uma vez só e libera links de inscrição, editais
              oficiais e downloads.
            </p>

            <div className="mt-5 grid gap-4">
              <div>
                <label htmlFor={`${id}-nome`} className="mb-1 block font-bold">Nome <span aria-hidden="true">*</span></label>
                <input id={`${id}-nome`} name="nome" required minLength={2} autoComplete="name" className={campo} autoFocus />
              </div>
              <div>
                <label htmlFor={`${id}-email`} className="mb-1 block font-bold">E-mail <span aria-hidden="true">*</span></label>
                <input id={`${id}-email`} name="email" type="email" required autoComplete="email" className={campo} />
              </div>
              <div>
                <label htmlFor={`${id}-wa`} className="mb-1 block font-bold">WhatsApp (opcional)</label>
                <input id={`${id}-wa`} name="whatsapp" type="tel" autoComplete="tel" inputMode="tel" placeholder="(71) 99999-9999" className={campo} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor={`${id}-uf`} className="mb-1 block font-bold">Estado <span aria-hidden="true">*</span></label>
                  <select id={`${id}-uf`} name="uf" required defaultValue="" className={campo}>
                    <option value="" disabled>Escolha</option>
                    {Object.entries(UFS).map(([s, n]) => <option key={s} value={s}>{n}</option>)}
                  </select>
                </div>
                <div>
                  <label htmlFor={`${id}-cidade`} className="mb-1 block font-bold">Cidade (opcional)</label>
                  <input id={`${id}-cidade`} name="cidade" autoComplete="address-level2" className={campo} />
                </div>
              </div>
              <div>
                <label htmlFor={`${id}-perfil`} className="mb-1 block font-bold">Você se inscreve como <span aria-hidden="true">*</span></label>
                <select id={`${id}-perfil`} name="perfil" required defaultValue="" className={campo}>
                  <option value="" disabled>Escolha</option>
                  {Object.entries(PERFIS).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor={`${id}-area`} className="mb-1 block font-bold">Sua área principal <span aria-hidden="true">*</span></label>
                <select id={`${id}-area`} name="area" required defaultValue="" className={campo}>
                  <option value="" disabled>Escolha</option>
                  {Object.entries(AREAS).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                </select>
              </div>

              {/* Armadilha para robôs: invisível para pessoas e leitores de tela. */}
              <div aria-hidden="true" className="absolute -left-[9999px]">
                <label>Site <input name="site" tabIndex={-1} autoComplete="off" /></label>
              </div>

              <label className="flex items-start gap-3">
                <input type="checkbox" name="consultoria" className="mt-1" />
                <span>Quero ajuda profissional para escrever ou inscrever meu projeto (consultoria da Flores).</span>
              </label>
              <label className="flex items-start gap-3">
                <input type="checkbox" name="newsletter" className="mt-1" />
                <span>Quero receber a newsletter da Central a cada 15 dias.</span>
              </label>
              <label className="flex items-start gap-3">
                <input type="checkbox" name="aceite" required className="mt-1" />
                <span>
                  Li e aceito a{" "}
                  <Link href="/privacidade/" target="_blank" className="font-bold text-acento underline">
                    Política de Privacidade
                  </Link>{" "}
                  <span aria-hidden="true">*</span>
                </span>
              </label>
            </div>

            {erro && <p role="alert" className="mt-4 rounded-lg border-2 border-critica bg-critica-fundo p-3 font-bold text-critica">{erro}</p>}

            <div className="mt-6 flex flex-wrap gap-3">
              <button type="submit" disabled={enviando}
                      className="alvo rounded-lg bg-marca px-5 py-2.5 font-bold text-marca-texto disabled:opacity-60">
                {enviando ? "Enviando..." : "Cadastrar e continuar"}
              </button>
              <button type="button" onClick={fechar} className="alvo rounded-lg border-2 border-borda px-5 py-2.5 font-bold">
                Agora não
              </button>
            </div>
            <p className="mt-3 text-suave">Campos com * são obrigatórios.</p>
          </form>
        )}
      </div>
    </dialog>
  );
}

/** Link que pede cadastro antes de abrir (se o cadastro estiver ativo). */
export function LinkProtegido({
  href, edital, rotulo, className, children,
}: { href: string; edital?: string; rotulo: string; className: string; children: React.ReactNode }) {
  const { ativo, pessoa, pedir } = useCadastro();
  if (!ativo || pessoa) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
        {children}<span className="sr-only">(abre em nova aba)</span>
      </a>
    );
  }
  return (
    <button type="button" className={className} onClick={() => pedir({ rotulo, href, edital })}>
      {children}<span className="sr-only">(pede cadastro gratuito)</span>
    </button>
  );
}
