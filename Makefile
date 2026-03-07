.PHONY: up down down-v up-dev down-dev down-dev-v build test test-dev test-local lint lint-local help
.DEFAULT_GOAL := help

COMPOSE_DEV = -f docker-compose.yml -f docker-compose.dev.yml

# --- Build ---
# Imagen de producción (stage runtime, código dentro de la imagen)
build:
	docker compose build

# --- Producción ---
# Levantar servicios en segundo plano
up:
	docker compose up -d

# Parar servicios
down:
	docker compose down

# Parar servicios y eliminar volúmenes
down-v:
	docker compose down -v

# --- Desarrollo (hot reload) ---
# Levantar con compose de dev (montaje de código, watchmedo)
up-dev:
	docker compose $(COMPOSE_DEV) up -d

# Parar servicios de dev
down-dev:
	docker compose $(COMPOSE_DEV) down

# Parar servicios de dev y eliminar volúmenes
down-dev-v:
	docker compose $(COMPOSE_DEV) down -v

# --- Tests ---
# Ejecutar tests dentro del contenedor (montando tests/)
test:
	docker compose run --rm -v "$(PWD)/tests:/app/tests:ro" bot python -m pytest tests/ -v

# Ejecutar tests dentro del contenedor usando el stack de dev
test-dev:
	docker compose $(COMPOSE_DEV) run --rm -v "$(PWD)/tests:/app/tests:ro" bot python -m pytest tests/ -v

# Ejecutar tests en el host usando .venv (crear venv si no existe)
test-local:
	@if [ -d .venv ]; then \
		.venv/bin/python -m pytest tests/ -v; \
	else \
		echo "No existe el entorno virtual .venv."; \
		echo ""; \
		echo "Para crearlo e instalar dependencias, ejecuta:"; \
		echo "  python3 -m venv .venv"; \
		echo "  .venv/bin/pip install -r requirements.txt"; \
		echo ""; \
		echo "Luego podrás usar: make test-local"; \
		exit 1; \
	fi

# --- Linters ---
# Ruff en el host (requiere .venv con requirements-dev.txt)
lint:
	@if [ -d .venv ]; then \
		.venv/bin/ruff check config/ src/ tests/ && .venv/bin/ruff format --check config/ src/ tests/; \
	else \
		echo "No existe .venv. Crea el venv e instala: pip install -r requirements-dev.txt"; \
		exit 1; \
	fi

lint-local: lint

help:
	@echo "Luz Informer Bot - make [objetivo]"
	@echo ""
	@echo "Build:"
	@echo "  build - Construir imagen de producción (código dentro de la imagen)"
	@echo ""
	@echo "Producción (sin montar código):"
	@echo "  up     - Levantar bot (docker compose up -d)"
	@echo "  down   - Parar servicios"
	@echo "  down-v - Parar y eliminar volúmenes"
	@echo ""
	@echo "Desarrollo (hot reload, monta código y reinicia al cambiar .py):"
	@echo "  up-dev     - Levantar con compose de dev"
	@echo "  down-dev   - Parar servicios de dev"
	@echo "  down-dev-v - Parar y eliminar volúmenes"
	@echo ""
	@echo "Tests:"
	@echo "  test       - Tests en contenedor (montando tests/)"
	@echo "  test-dev   - Tests en contenedor con stack de dev"
	@echo "  test-local - Tests en el host con .venv"
	@echo ""
	@echo "Linters (requiere .venv + requirements-dev.txt):"
	@echo "  lint / lint-local - Ruff check + format"
	@echo ""
	@echo "CI: GitHub Actions usa Python en el runner (pytest, ruff). Ver .github/workflows/"
	@echo ""
	@echo "  help - Mostrar esta ayuda"
