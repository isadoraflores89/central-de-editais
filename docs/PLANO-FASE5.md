# Fase 5 — Open calls, chamadas acadêmicas e conteúdo para LinkedIn

Plano de execução do adendo recebido em 31/10/2026. Ele amplia o escopo sem
reescrever o que já roda (Fase 1: planilha-semente, curadoria, status,
prioridade, site estático, API; radares diários de vagas, licitações e
resultados).

## 0. Situação de partida (o que o adendo assume e não existe)

O adendo diz "depois que as Fases 1–2 estiverem rodando". A Fase 2 (coletores
automáticos de fontes brasileiras) **não foi construída**: hoje a lista de
fomento vem da planilha-semente e da curadoria. Por isso a Fase 5 começa
criando a base de coletores que a Fase 2 previa (`pipeline/collectors/base.py`:
cache em `data/cache/`, rate limit, robots.txt, fixtures para teste) e os
coletores do adendo são os primeiros a usá-la. Os coletores brasileiros de
fomento (Prosas, MinC, Mapa Cultural…) continuam em aberto, agora mais fáceis.

Nada é bloqueante para começar. Duas decisões ficam com a Isadora, mas têm
padrão provisório:

1. **Marca**: `config/brand.yaml` nasce com o nome atual ("Central de Editais")
   e pode ser trocado sem mexer em código.
2. **Voz dos posts** (`voz: institucional | pessoal`): começa em `pessoal`
   (primeira pessoa, como ela publica hoje).

## 1. O que muda no esquema (`pipeline/models.py`)

A classe continua `Edital` (todo o código e o site a usam) e ganha o alias
`Oportunidade`. `SCHEMA_VERSION` passa de 1 para 2. **Todos os campos novos têm
valor padrão**, então o `data/editais.json` atual carrega sem conversão e os
registros antigos viram `vertical = fomento` automaticamente.

Comuns às três verticais:

| campo | tipo | padrão |
|---|---|---|
| `vertical` | `fomento` / `open_call` / `academico` | `fomento` |
| `idiomas` | lista (`pt`, `es`, `en`, `fr`…) | `[]` |
| `pais_organizador` | ISO-3166 alfa-2 | `null` |
| `elegivel_brasileiros` | `true` / `false` / `null` (só quando o texto diz) | `null` |

Open call: `formato` (residencia, exposicao, festival, premio, bolsa_mobilidade,
comissionamento, publicacao_artistica, outro), `taxa_inscricao` + `taxa_moeda`
(0 = gratuita; `null` = não informado), `cobre[]` (honorario, passagem,
hospedagem, ajuda_custo, producao, visto, alimentacao), `moeda`,
`valor_original`, `valor_brl_estimado`, `cotacao_data`, `modalidade`
(presencial, online, hibrida).

Acadêmico: `formato_academico` (dossie_revista, fluxo_continuo_revista,
congresso, livro_coletanea, premio_pesquisa, bolsa_pesquisa, pos_doc),
`periodico`, `evento`, `issn`, `qualis`, `indexadores[]`, `apc` + `apc_moeda`,
`data_resumo`, `data_texto_completo`, `data_evento`, `tema_dossie`,
`organizadores[]`, `link_normas`.

Regras que o código impõe:

- Nunca inferir Qualis, taxa ou elegibilidade: sem evidência no texto, `null`.
- `taxa_inscricao > 0` ou `apc > 0` ganha o marcador `com_taxa` (selo no site).
- Open call com taxa e sem nenhuma contrapartida em `cobre[]` ganha
  `alerta_taxa` + `revisao_pendente = true`: fica fora da publicação automática
  até a curadoria liberar em `data/overrides.yaml`.
- Para o acadêmico, `data_limite` recebe a data mais próxima entre
  `data_resumo` e `data_texto_completo`; o site mostra as duas.
- Áreas continuam vocabulário aberto; entram `politicas_culturais`,
  `gestao_cultural`, `estudos_culturais`, `comunicacao`, `antropologia`,
  `artes`, `educacao`.

Conversão de moeda: cotação PTAX do dia da coleta pela API aberta do Banco
Central (sem chave), guardada com a data em `cotacao_data`. Se a API falhar, o
valor fica só na moeda original.

## 2. O que muda nas pastas

```
config/
  brand.yaml            nome, slogan, domínio, cores, assinatura, voz, hashtags
  periodicos.yaml       revistas em OJS: url_base, área, issn, qualis (editável)
  fontes_opencall.yaml  agregadores e programas de open call: url, método, ativo
  priority.yaml         ganha o bloco `verticais:` (open_call e academico)
pipeline/
  collectors/
    base.py             RawItem, cache, rate limit, robots.txt, fixtures
    ojs.py              coletor genérico de avisos de revistas OJS
    onthemove.py        On the Move (RSS)
    (próximos) transartists.py, resartis.py, ibero.py, congressos.py, wikicfp.py
  content/
    weekly.py           post semanal + carrossel JSON + newsletter + alertas
  publishers/
    linkedin.py         interface pronta e DESLIGADA (LINKEDIN_PUBLISH=0)
content/
  weekly/AAAA-WW.md, AAAA-WW.carrossel.json
  newsletter/AAAA-WW.md
  alertas/AAAA-MM-DD.md
docs/
  PLANO-FASE5.md (este), FONTES.md (método usado em cada fonte)
tests/fixtures/{ojs,onthemove,...}   HTML/XML salvos: testes nunca acessam a rede
.github/workflows/
  radar-conteudo.yml    segunda 07:00 Bahia: gera conteúdo e commita em content/
  daily.yml             ganha o passo `python -m pipeline collect`
```

Comandos novos: `python -m pipeline collect [--fonte ojs|onthemove] [--simular]`
e `python -m pipeline conteudo [--semana AAAA-WW]`.

## 3. Ordem de entrega

| # | Entrega | Estado |
|---|---|---|
| 1 | Migração do modelo + `brand.yaml` + prioridade por vertical + CSV/XLSX com colunas novas | feito nesta rodada |
| 2 | Base de coletores + OJS genérico (10 revistas semente) + On the Move | feito nesta rodada (OJS e OTM); TransArtists, Res Artis, Ibero e congressos nas próximas |
| 3 | Gerador semanal: post LinkedIn, carrossel JSON, newsletter, alertas + workflow | feito nesta rodada |
| 4 | Site com 3 abas (Fomento, Open calls, Acadêmico), facetas e presets novos, datas duplas, valor em moeda + R$ estimado, rótulos pt/es/en | próxima rodada |
| 5 | Coletores restantes (Res Artis, TransArtists, Ibero, institutos estrangeiros, congressos nacionais, editoras internacionais, WikiCFP) com fixtures | rodadas seguintes, uma fonte por vez |
| 6 | Relatório de cobertura por vertical em `reports/` | junto com a 5 |

## 4. Fontes: o que já foi verificado

- **On the Move**: tem RSS público (`https://on-the-move.org/feed`), 10 itens por
  vez. Os títulos vêm vazios no feed; o coletor usa a primeira frase da
  descrição. O link é a página do On the Move; o link oficial da instituição
  entra na curadoria (marcador `link_agregador`).
- **Revistas OJS**: o feed RSS de avisos não está ligado na maioria; a página
  `/announcement` é pública e tem marcação estável (`obj_announcement_summary`).
  O coletor lê essa página.
- **Res Artis**: protegido por desafio anti-robô; precisa de outra estratégia
  (newsletter ou página de membros). **TransArtists**: sem RSS; HTML na próxima
  rodada.

## 5. Conteúdo para LinkedIn (sem publicação automática)

Toda segunda às 07:00 (Bahia) o pipeline gera, a partir dos dados da semana:
post (máx. 2.800 caracteres, 5–7 destaques, até 3 hashtags, links para a página
do item no site), carrossel (JSON com 6–8 slides) e newsletter. Alertas
imediatos entram em `content/alertas/` quando chega item com prioridade ≥ 80 ou
prazo ≤ 7 dias. Tudo fica no repositório para revisão humana; a publicação no
LinkedIn fica desligada (`publishers/linkedin.py`, env `LINKEDIN_PUBLISH`).

## 6. Riscos

- Fontes internacionais mudam de HTML sem aviso: cada coletor tem fixture e o
  teste quebra antes do site.
- Pay-to-play: o marcador `alerta_taxa` segura a publicação, mas a decisão
  final é humana (overrides).
- Volume: open calls + acadêmico podem triplicar a lista. A prioridade por
  vertical e as abas separadas evitam misturar públicos.
