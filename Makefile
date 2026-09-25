# Central de Editais — atalhos. Requer uv (Python) e npm (Node 22).
UV ?= uv
NPM ?= npm

.PHONY: setup import-seed run collect report test lint site-build dev

setup:            ## instala dependências Python e do site
	$(UV) sync
	cd site && $(NPM) ci

import-seed:      ## importa a planilha-semente para data/editais.json
	$(UV) run python -m pipeline import-seed

run:              ## reprocessa status/prioridade e exporta para o site
	$(UV) run python -m pipeline run --destino site/public/api

collect:          ## coleta nas fontes (Fase 2)
	$(UV) run python -m pipeline collect

report:           ## resumo dos dados e cobertura por fonte
	$(UV) run python -m pipeline report

test:             ## testes Python e site
	$(UV) run pytest
	cd site && $(NPM) test

lint:             ## ruff + mypy + eslint + tsc
	$(UV) run ruff check pipeline tests
	$(UV) run mypy
	cd site && $(NPM) run lint && $(NPM) run typecheck

site-build: run   ## gera o site estático em site/out
	cd site && $(NPM) run build

dev: run          ## site em modo desenvolvimento (http://localhost:3000)
	cd site && $(NPM) run dev
