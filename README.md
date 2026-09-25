# Central de Editais

Radar aberto e gratuito de **editais, chamadas de patrocínio e credenciamentos** do campo
cultural brasileiro, atualizado todos os dias, com filtros por estado, mecanismo (Rouanet,
Lei do Esporte, ICMS, PNAB...), prazo, valor e tipo de proponente.

Mantido por **Flores Produções** e pelo **Ponto de Cultura Lab Garra** ([labgarra.art.br](https://labgarra.art.br)).

- Site: https://radardeeditais.isadoraflores.art.br
- Dados abertos: `/api/editais.json`, `/api/editais.csv`, `/api/editais.xlsx`, `/api/editais.db`
- Código: MIT ([LICENSE](LICENSE)). Dados: CC BY 4.0 ([LICENSE-DATA.md](LICENSE-DATA.md)).

> A Central organiza informações públicas e sempre aponta para a fonte oficial.
> Confira prazos e regras no edital oficial antes de se inscrever.

## Como funciona

```
fontes oficiais ──> coleta ──> normalização ──> dedupe ──> curadoria ──> status/prioridade
   (Fase 2)        (Fase 2)    (regras YAML)              (overrides)      (config YAML)
                                                                              │
             data/editais.json (versionado) <─────────────────────────────────┘
                     │
                     ├─> /api/editais.{json,csv,xlsx,db}
                     └─> site estático (Next.js) ──> GitHub Pages
```

Arquitetura e decisões: [docs/PLANO.md](docs/PLANO.md).

## Rodar localmente

Requisitos: [uv](https://docs.astral.sh/uv/) (instala o Python 3.12 sozinho) e Node 22.

```bash
make setup        # instala dependências
make import-seed  # (só na primeira vez) importa a planilha-semente
make dev          # reprocessa os dados e abre o site em http://localhost:3000
```

Outros comandos:

| Comando | O que faz |
|---|---|
| `make run` | recalcula status e prioridade e exporta para `site/public/api` |
| `make report` | resumo dos dados (por status, por fonte, top 10) |
| `make test` | testes Python (pytest) e do site (vitest) |
| `make lint` | ruff, mypy, eslint e tsc |
| `make site-build` | gera o site estático em `site/out` |
| `make collect` | coleta nas fontes (Fase 2) |

Para fixar a data de referência (testes, reprocessar um dia antigo): `CENTRAL_HOJE=2026-09-25 make run`.

## Curadoria manual

Edite [`data/overrides.yaml`](data/overrides.yaml). Tudo o que está lá vence a coleta automática:

```yaml
ambev-brasilidades-2026-5d25ba:   # id = final do endereço /edital/<id>
  destaque: true
  tags: [bahia]
  nota: "Conferido em 25/09"
  campos:
    data_limite: 2026-10-15
```

Apagar um override devolve o valor coletado na próxima atualização.

## Configuração

| Arquivo | Para quê |
|---|---|
| `config/priority.yaml` | pesos da nota de prioridade (0 a 100) |
| `config/presets.yaml` | botões de busca pronta do site |
| `config/mapeamentos.yaml` | regras que transformam texto livre em filtros (tipo, mecanismo, UF...) |

## Automação (GitHub Actions)

- `ci.yml`: lint, tipos, testes e build em todo push e pull request.
- `daily.yml`: todo dia às 06:00 de Salvador (e sob demanda) reprocessa os dados, faz commit
  de `data/` se algo mudou, gera o site e publica no GitHub Pages. Se a lista vier vazia,
  falha e **não publica**.

Segredos (Settings > Secrets and variables > Actions), usados a partir das fases 2–4:

| Segredo | Obrigatório | Uso |
|---|---|---|
| `ANTHROPIC_API_KEY` | Fase 3 | extração estruturada de editais longos |
| `NOTIFY_EMAIL_TO` | Fase 3 | destinatário do relatório diário |
| `RESEND_API_KEY` | opcional | envio do e-mail pelo Resend |
| `SHEETS_SERVICE_ACCOUNT_JSON` | opcional | sincronizar com Google Sheets |
| `SHEETS_ID` | opcional | planilha de destino |

## Rodar a sua própria instância

1. Faça um fork deste repositório.
2. Em Settings > Pages, escolha "GitHub Actions" como fonte.
3. Se não tiver domínio próprio, crie a variável de repositório `BASE_PATH` com o valor
   `/nome-do-repositorio` (Settings > Secrets and variables > Actions > Variables).
4. Troque os pesos em `config/priority.yaml` e os presets em `config/presets.yaml`
   para as prioridades do seu território.
