# Central de Editais — Plano de arquitetura

Mantido por Flores Produções e Ponto de Cultura Lab Garra (labgarra.art.br).
Documento vivo: toda decisão que mudar entra aqui com data.

Versão 1 — 25/09/2026.

---

## 1. O que o produto é, em uma frase

Um radar público e gratuito de editais, patrocínios e credenciamentos culturais,
atualizado todo dia por robô, com filtros de verdade e dados abertos (JSON, CSV,
XLSX, Google Sheets).

Ele substitui a planilha manual `Editais_Culturais_Nacionais_set2026_v2` e também
o "Radar de Editais" anterior (`PROGRAMAS/Radar de Editais` e a página privada
`isadoraflores.art.br/radar-3fx8qm/`). Esses dois podem ser desligados quando a
Central estiver no ar.

---

## 1b. Respostas da Isadora (25/09/2026)

- **Deploy:** GitHub Pages, no endereço `radardeeditais.isadoraflores.art.br`
  (conserta o link que hoje está quebrado no site principal). É preciso criar um
  CNAME no DNS de isadoraflores.art.br apontando para `isadoraflores89.github.io`.
- **Repositório:** `isadoraflores89/central-de-editais`, público.
- **Google Sheets:** ainda não há service account. Fica para a Fase 4, com guia.
- **Ambiente local:** uv + Python 3.12.14 e Node 22.23.3 instalados em `~/.local`.


## 1c. Mudanças de rumo (26/09/2026)

- **Sem IA por enquanto.** O enriquecimento com IA (D11, Fase 3) e o chat com o projeto
  ficam de fora. A coleta e a normalização seguem só com regras (config/mapeamentos.yaml),
  e o que as regras não entenderem vai para a fila de revisão. Custo de IA: zero.
- **No lugar do chat**, o site tem uma chamada para a consultoria da Flores:
  "Quer fazer seu projeto de forma profissional e rápida?" → projetos@isadoraflores.art.br.
- **Novidades por Substack (grátis, a cada 15 dias).** O site ganha um bloco de inscrição na
  newsletter que já existe. O Substack não tem API para publicar, então o robô gera a cada
  15 dias um rascunho da edição (reports/newsletter-AAAA-MM-DD.md) para ser colado no Substack.
- **Alertas pagos para apoiadores do Apoia.se**, por e-mail e WhatsApp, com frequência
  conforme o valor (ex.: diário ou 2x por semana). O robô gera os resumos de cada
  frequência (reports/alerta-diario-*.md, reports/alerta-2x-*.md). A forma de entrega
  (lista de e-mail e WhatsApp) está em aberto; ver o plano de monetização.
- **Apoio ("pague um café")**: PIX (chave + QR code + copia e cola) e Apoia.se (mensal).
- Tudo isso fica configurável em `config/site.yaml`. Um bloco só aparece quando o dado
  correspondente está preenchido.
- O plano de monetização fica fora do repositório público, em
  `FLORES CULTURA/GUIAS/Central_de_Editais_Monetizacao.md`.

## 2. Estrutura de pastas

```
central-de-editais/
├── pipeline/                  # pacote Python (python -m pipeline ...)
│   ├── __main__.py            # CLI: run, collect, import-seed, export, add-manual, report, check-links
│   ├── config.py              # lê env + config/*.yaml
│   ├── models.py              # Edital, RawItem, Curadoria, Historico (pydantic + sqlmodel)
│   ├── enums.py               # TipoApoio, Mecanismo, Abrangencia, Area, Proponente, Status...
│   ├── db.py                  # sqlite (sqlmodel): criar, carregar do JSON, salvar
│   ├── ids.py                 # id estável + normalização de título
│   ├── status.py              # regras de status (encerrado, prorrogado, em_breve)
│   ├── priority.py            # regra de prioridade lida de config/priority.yaml
│   ├── overrides.py           # aplica data/overrides.yaml (sempre vence a coleta)
│   ├── importers/
│   │   └── seed_xlsx.py       # importa as 3 abas da planilha-semente
│   ├── collectors/            # um arquivo por fonte, todos com fetch() -> list[RawItem]
│   │   ├── base.py            # BaseCollector: rate limit, retries, cache em data/cache/, robots.txt
│   │   ├── prosas.py          # (Fase 2)
│   │   ├── minc.py, mapa_cultura.py, culteditais.py, funarte.py, pncp.py, secult_ba.py
│   │   ├── agregadores.py     # BRB Law, Capta etc. — só descoberta de links
│   │   ├── seec_pr.py, fcc_curitiba.py, corporativos.py, internacionais.py   # (Fase 3)
│   ├── normalize/             # RawItem -> Edital (datas, valores, UF, enums)
│   ├── enrich/                # IA (Fase 3): extração estruturada com cache por hash do texto
│   ├── dedupe/                # funde duplicatas, mantém fonte oficial como principal
│   ├── export/                # json.py, csv.py, xlsx.py, sheets.py (Fase 4)
│   ├── notify/                # email (Resend/SMTP) + interface de webhook (WhatsApp)
│   └── report.py              # reports/AAAA-MM-DD.md + cobertura por fonte
├── config/
│   ├── priority.yaml          # pesos da prioridade (editável sem mexer em código)
│   ├── presets.yaml           # buscas prontas (Bahia, Paraná, Parecerista...)
│   ├── sources.yaml           # fontes ativas, rate limit, User-Agent por fonte
│   └── mapeamentos.yaml       # texto livre -> enum ("Patrocínio via leis ESTADUAIS" -> patrocinio_incentivado + icms_estadual)
├── data/
│   ├── editais.json           # FONTE DA VERDADE versionada (ordenada, estável, diffável)
│   ├── historico.jsonl        # uma linha por mudança (prazo, status, campo)
│   ├── overrides.yaml         # curadoria manual por id
│   ├── seed/                  # planilha-semente original (.xlsx) — congelada
│   ├── editais.db             # sqlite gerado (fora do git — ver decisão D1)
│   └── cache/                 # HTML/PDF baixados (fora do git)
├── site/                      # Next.js 15 + TypeScript + Tailwind, output: 'export'
│   ├── app/
│   │   ├── page.tsx           # lista + filtros
│   │   ├── edital/[id]/page.tsx
│   │   ├── parecerista/, lei-do-esporte/, sobre/, embed/
│   ├── lib/                   # filtros, busca sem acento, facetas, exportação no cliente
│   ├── components/            # Card, Filtros, Facetas, Contagem regressiva, ícones SVG próprios
│   └── scripts/copy-data.mjs  # copia data/ para public/api/ no build
├── tests/
│   ├── fixtures/              # HTML/JSON salvos de cada fonte (testes nunca acessam a internet)
│   └── test_*.py
├── reports/                   # relatórios diários (markdown)
├── .github/
│   ├── workflows/ci.yml       # lint + testes + build em todo push/PR
│   ├── workflows/daily.yml    # cron 09:00 UTC (06:00 Bahia) + workflow_dispatch
│   ├── workflows/weekly-links.yml  # checa se os links respondem (semanal)
│   └── ISSUE_TEMPLATE/        # reportar erro, sugerir edital
├── docs/PLANO.md, docs/METODOLOGIA.md
├── Makefile                   # make dev, make collect, make test, make report
├── pyproject.toml, .pre-commit-config.yaml
├── LICENSE (MIT, código)  e  LICENSE-DATA (CC-BY 4.0, dados)
└── README.md
```

---

## 3. Decisões de arquitetura

**D1. O `editais.json` é a fonte da verdade no git. O `editais.db` não é commitado.**
Aqui me afastei do que foi pedido. Motivo: o sqlite é um arquivo binário. Cada
atualização diária guardaria no histórico do git uma cópia inteira do banco, sem
diff legível, e em um ano o repositório passaria de centenas de MB. O JSON (ordenado
por id, com indentação estável) mostra no GitHub, linha a linha, o que mudou no dia.
O banco continua existindo: o pipeline recria o `editais.db` a partir do JSON ao
começar e trabalha nele. As mudanças ficam em `historico.jsonl`. Nada se perde, e
quem quiser o `.db` baixa pelo site em `/api/editais.db`.

**D2. O id é gerado uma vez e depois fica congelado.**
Na primeira captura: `slug-do-titulo-` + 6 caracteres do hash (fonte canônica +
título normalizado). Exemplo: `ambev-brasilidades-2026-3f9a1c`. A partir daí o id
não muda mesmo que o título mude na fonte ("2026" vira "2026 — prorrogado"). Assim
os links `/edital/[id]` e as regras de `overrides.yaml` não quebram. A comparação
entre coletas usa as chaves do dedupe, não o id. Quando dois registros se fundem, o
id perdido vira um alias que redireciona.

**D3. Carga-semente: 63 linhas viram menos de 63 registros únicos, e isso é esperado.**
A planilha tem o mesmo edital em mais de uma aba (Ambev, Sicredi, Mapfre e Shell
aparecem em "Editais" e em "Lei do Esporte"). O dedupe junta cada par em um registro
só e soma os mecanismos (ex.: `[rouanet, lei_esporte]`). O relatório de importação
mostra "63 linhas lidas → N registros, M fusões", com a lista das fusões.
- `fonte = "curadoria inicial (planilha 24/09/2026)"`, `captured_at = 2026-09-24`.
- `source_url` = link oficial da linha (inscrição, ou o PDF citado em Observações).
  As linhas de Parecerista com link genérico da Prosas (`/editais?status=abertos`,
  "localizar pelo nome") entram com `curadoria.tags = ["link_generico"]` e aparecem
  na fila de revisão. O link exato fica para o coletor da Prosas (Fase 2).
- "Tipo de apoio" e "Abrangência" são texto livre. A conversão para enums é feita por
  regras em `config/mapeamentos.yaml`, sem IA. O que nenhuma regra reconhecer vira
  `null` e recebe a tag `revisar`, sem chute.
- "Dias restantes" e "Novo (24/09)" não são importados: o sistema calcula os dois.
- Em 25/09 vários prazos vencem em 30/09. O import já calcula o status de cada um.

**D4. O status é calculado duas vezes: no pipeline e no navegador.**
O site é estático e reconstruído uma vez por dia. Se o robô falhar num dia, o
navegador ainda compara `data_limite` com a data de hoje e esconde o que venceu, e a
contagem regressiva fica sempre certa. A prioridade é calculada só no Python. No
navegador vale apenas a regra "encerrado = 0".

**D5. O site filtra tudo no navegador, a partir de um único JSON.**
Mesmo com 5.000 editais o arquivo fica em torno de 1 MB comprimido, e a filtragem é
instantânea. Assim não existe backend, nem custo, nem servidor para cair. Os filtros
ficam na URL (`?uf=BA,PR&mecanismo=rouanet&prazo=30`) para dar para compartilhar.
A busca ignora acentos (normalização NFD) em título, órgão, resumo e cidades.
Para a primeira tela carregar rápido, a página inicial recebe só os campos dos cards,
e o JSON completo vem depois.

**D6. As páginas `/edital/[id]` são geradas no build (`generateStaticParams`).**
Isso inclui os encerrados, para manter o histórico e o SEO. Parecerista, Lei do
Esporte e Embed são presets de `config/presets.yaml` com layout próprio.

**D7. CSV e XLSX "do filtro atual" são gerados no navegador.**
CSV é escrito à mão (com BOM UTF-8 para abrir certo no Excel). XLSX usa `exceljs`,
carregado só quando alguém clica em baixar. Não uso o pacote `xlsx` do npm porque a
versão publicada lá está desatualizada e tem vulnerabilidade conhecida.

**D8. Acessibilidade: o mínimo aqui é mais alto que o AA.**
Fonte base de 18px e nenhum texto menor que 15px. Contraste de 4,5:1 ou mais,
verificado nos testes. Foco visível forte, todos os alvos com 44px ou mais, e
`aria-live` na contagem de resultados. Cores de prazo sempre acompanhadas de texto
("fecha em 3 dias"), nunca só a cor. Sem emojis: ícones SVG próprios. Os textos da
interface ficam em pt-BR.

**D9. Robô: nunca publicar lista vazia nem lista quebrada.**
O `daily.yml` falha e não publica quando: (a) todas as fontes falharam; (b) o total
de editais abertos caiu mais de 40% em relação ao dia anterior (sinal de coletor
quebrado, não de editais sumindo). Fonte que falha sozinha entra como
"indisponível" no relatório, e os itens dela não são encerrados nesse dia. Um item
só é marcado como "sumiu da fonte" depois de 3 coletas bem-sucedidas seguidas sem
ele.

**D10. Coleta responsável.**
Cada fonte consulta o `robots.txt` antes, respeita um rate limit (padrão de 1
requisição a cada 2 segundos por domínio), usa cache em disco e tenta de novo com
backoff exponencial. O User-Agent padrão se identifica (`CentralDeEditaisBot/1.0
(+url-do-site/sobre)`). As fontes que só respondem a navegador (SEEC-PR, Prosas)
usam Playwright com User-Agent de navegador, e só onde o `robots.txt` permite.
Da Prosas guardamos só os metadados públicos do card e sempre mandamos a pessoa
para a página da Prosas. Não copiamos regulamentos.

**D11. IA (Fase 3) só extrai informação, nunca inventa.**
A saída tem schema rígido (tool use / JSON). Todo campo vem acompanhado do trecho do
texto que o justifica. Se o trecho não aparece literalmente no texto-fonte, o campo
vira `null`. O cache é por SHA-256 do texto, e os tokens gastos vão para o relatório.
O modelo é configurável por `ANTHROPIC_MODEL`. A especificação pede
`claude-sonnet-4-5` como padrão; minha proposta é usar a geração atual
(`claude-sonnet-5`), que custa o mesmo e é mais precisa. Decido de vez na Fase 3,
testando os dois com fixtures reais.

**D12. Python 3.12 com `uv`, Node 22 LTS com `npm`.** (Node 20 saiu de suporte em abril/2026.)
O `uv` instala o Python certo sozinho e trava as versões (`uv.lock`). No GitHub
Actions, tudo roda na versão fixada. Qualidade: ruff, mypy (strict no `pipeline/`),
pytest, eslint, tsc e pre-commit.

**D13. Licenças.** O código é MIT. Os dados são CC-BY 4.0, com o campo `fonte` e
`source_url` em todo registro como atribuição. A página `/sobre` explica como citar.

---

## 4. Modelo de dados

Segue a especificação combinada. Os acréscimos, que ela já pressupõe, são:
`fontes_secundarias[]`, `historico[]`, `aliases[]` (ids fundidos) e
`revisao_pendente: bool`.
Datas em ISO (`AAAA-MM-DD`), valores em BRL como número (centavos não importam).
Valores em outra moeda (ex.: € 175 mil do protocolo luso-brasileiro) ficam em
`valor_texto` e **não** são convertidos. O filtro de valor mostra esses casos como
"não informado em R$".

## 5. Regra de prioridade (config/priority.yaml)

| Critério | Pontos |
|---|---|
| Abrangência nacional | +25 |
| Mecanismo Rouanet, Lei do Esporte ou ICMS BA/PR | +20 |
| Valor por projeto a partir de R$ 100 mil | +15 |
| Prazo entre 7 e 60 dias | +20 |
| Prazo entre 1 e 6 dias | +10 |
| Fluxo contínuo | +5 |
| Não exige projeto já aprovado | +10 |
| UF inclui BA ou PR | +10 |
| Destaque manual | +30 |
| Encerrado | = 0 e sai da lista padrão |

O teto é 100 (o que passar disso é cortado). Critério sem dado (`null`) não soma
pontos: um edital sem valor informado não é premiado nem punido.

---

## 6. Fase 1 — o que entra

1. Estrutura do repositório, pyproject, Makefile, pre-commit, CI.
2. Modelo `Edital` + enums + banco sqlite + id estável.
3. Importação da planilha-semente (3 abas) com relatório de fusões e pendências.
4. Status e prioridade calculados (com testes).
5. `data/overrides.yaml` aplicado.
6. Exportação para `editais.json`, `editais.csv` e `editais.xlsx`.
7. Site: lista, painel de filtros completo (facetas, prazo, toggles, valor, busca,
   ordenação), card, `/edital/[id]`, exportação do filtro atual, presets básicos,
   acessibilidade.
8. Deploy funcionando com os dados-semente.

Fica para as próximas fases: coletores, IA, e-mail, Sheets, embed, `add-manual`.

---

## 7. Riscos já conhecidos

- **Termos de uso da Prosas**: a raspagem é tolerada, mas não é autorizada. Guardamos
  só metadados públicos e mandamos o tráfego para lá. Se a Prosas pedir, o coletor é
  desligado em `sources.yaml` sem mexer no código.
- **gov.br "Conteúdo Restrito"**: tratado como falha leve, com URL alternativa.
- **Mudança de layout das fontes**: cada coletor tem teste com fixture. Quando o
  layout muda, o teste do dia falha e o relatório mostra, mas o site continua com a
  última lista boa.
- **Link quebrado hoje em isadoraflores.art.br** (`radardeeditais.isadoraflores.art.br`
  não existe). Se a Central usar esse subdomínio, o link volta a funcionar sozinho.
