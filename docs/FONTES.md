# Fontes da Fase 5 — o que foi verificado e como cada uma é lida

Regra geral: cada coletor respeita robots.txt, espera 1,5 s entre pedidos,
guarda cache em `data/cache/` (fora do git) e tem uma fixture em
`tests/fixtures/` para os testes rodarem sem rede. Inventário em
`config/fontes_opencall.yaml` e `config/periodicos.yaml`.

## Open calls

| Fonte | Método | Estado | Observações |
|---|---|---|---|
| On the Move | RSS `https://on-the-move.org/feed` | ativo | Títulos vêm vazios ("[News] "); usamos a primeira frase da descrição. Link é a página do agregador (marcador `link_agregador`); o link oficial entra na curadoria. 10 itens por leitura. |
| TransArtists | HTML | próxima rodada | Sem RSS. Lista em `/en/open-calls`. |
| Res Artis | manual | bloqueado | Desafio anti-robô na página de open calls. Avaliar newsletter ou página de membros. |
| Ibermúsicas / Iberescena / IberCultura Viva | HTML | próxima rodada | Convocatórias anuais; textos em espanhol. |
| Pro Helvetia, Goethe-Institut | HTML | próxima rodada | Páginas regionais em português/inglês. |

## Chamadas acadêmicas (revistas em OJS 3)

A página pública `<url_base>/announcement` tem blocos
`<article class="obj_announcement_summary">` com `h2 > a` (título e link),
`div.date` (AAAA-MM-DD) e `div.summary`. O feed RSS de avisos existe no OJS,
mas quase nenhuma revista o liga (404 na Políticas Culturais em Revista), por
isso o coletor lê o HTML. Só entram avisos cujo título ou resumo fala em
chamada, dossiê, call for papers, número temático ou submissões.

Qualis e ISSN nunca são inferidos do texto: vêm de `config/periodicos.yaml`,
preenchido à mão com a Plataforma Sucupira. APC só quando o aviso diz
explicitamente (gratuito ou valor).

Revistas semente (10): Políticas Culturais em Revista (UFBA), Contemporânea
(UFBA), Pragmatizes (UFF), Extraprensa (USP), Revista CPC (USP), Horizontes
Antropológicos (UFRGS), Estudos da Presença (UFRGS), ouvirOUver (UFU),
Educação, Cultura e Sociedade (UNEMAT), FAMECOS (PUCRS).

## Congressos e outros (próximas rodadas)

- ENECULT (UFBA), Compós, Intercom, ABA, ABRACE: páginas próprias, uma por
  coletor, com fixture.
- WikiCFP: RSS por categoria (`cultural studies`, `communication`).
- Editoras internacionais (Routledge, Palgrave): calls for chapters em HTML.

## Câmbio

Valores em moeda estrangeira ganham `valor_brl_estimado` pela cotação PTAX de
venda do dia da coleta (API aberta do Banco Central, sem chave), com a data em
`cotacao_data`. Se a API falhar, fica só o valor original.
