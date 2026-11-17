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

## Buscador (17/11/2026): vigia de páginas, busca na web e Instagram ampliado

Inventário: `config/fontes.yaml`, gerado das planilhas em `config/fontes/` (Base_Fontes_Editais_da_Isa
e Base_Internacional) por `uv run python -m pipeline.importar_fontes`. 189 fontes: governo federal,
agregadores, empresas e institutos, 27 secretarias estaduais, fundações e mecanismos estaduais,
capitais, cooperação internacional, universidades; Europa (47) e América Latina (53).
Para incluir ou corrigir uma fonte: edite a planilha, rode o comando, confira o YAML.

| Coletor | O que faz | Limites por rodada (config/buscador.yaml) |
|---|---|---|
| `paginas` | abre a página de editais de cada fonte (`metodo: pagina`), acha links novos com palavra de oportunidade em PT/ES/EN/FR, lê a página e extrai os campos com o Gemini | diárias todo dia, semanais em rodízio por dia da semana; 6 links novos por fonte; 60 páginas lidas pela IA |
| `busca_web` | pergunta ao Google (Programmable Search, se `GOOGLE_CSE_KEY`/`GOOGLE_CSE_ID`; senão Gemini com Google Search) as consultas de `config/buscador.yaml` em rodízio + 2 estados por dia | 6 consultas + 2 estados; 30 páginas lidas |
| `instagram` | contas e hashtags de `config/instagram.yaml` (ampliado para ~70 contas; os `# confirmar` precisam de checagem do @) | 40 posts lidos pela IA |

Regras de segurança, iguais nos três: nada entra como "aberto" sem prazo **escrito na página**
(`datas_no_texto`); data sugerida pela IA que não está no texto vira `prazo_texto` e o item fica
`revisao_pendente` com marcador `aguardando_aprovacao` (status indefinido, invisível para assinantes)
até a curadoria confirmar em `data/overrides.yaml` (`campos.data_limite`). Links vistos ficam em
`data/fontes_vistos.json` e `data/busca_vistos.json` (180 dias) para não gastar IA duas vezes.
Sem `GEMINI_API_KEY`, vale a leitura por regras (título do link, prazo perto de "até/prazo"), mais
restritiva. Resultado da rodada aparece em `uv run python -m pipeline report` ("Aguardando revisão").

Verificado em 17/11/2026 (sem IA): MinC e Funarte dão 4 candidatos reais cada depois de ignorar
menus e caminhos administrativos; LabEC lista dezenas de links para Mapas Culturais e Prosas;
Prosas e Iberescena carregam a lista por JavaScript (0 links; ficam para a busca na web);
DGARTES `/pt/apoios` responde 404 (corrigir a URL na planilha).
