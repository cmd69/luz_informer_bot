.PHONY: up down down-v up-dev down-dev down-dev-v test test-dev test-local help
.DEFAULT_GOAL := help

COMPOSE_DEV = -f docker-compose.yml -f docker-compose.dev.yml

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

help:
	@echo "Uso: make [objetivo]"
	@echo ""
	@echo "Producción:"
	@echo "  up         - Levantar servicios (docker compose up -d)"
	@echo "  down       - Parar servicios (docker compose down)"
	@echo "  down-v     - Parar servicios y eliminar volúmenes (docker compose down -v)"
	@echo ""
	@echo "Desarrollo (hot reload):"
	@echo "  up-dev     - Levantar con compose de dev (código montado, watchmedo)"
	@echo "  down-dev   - Parar servicios de dev"
	@echo "  down-dev-v - Parar servicios de dev y eliminar volúmenes"
	@echo ""
	@echo "Tests:"
	@echo "  test       - Ejecutar tests dentro del contenedor"
	@echo "  test-dev   - Ejecutar tests en contenedor con stack de dev"
	@echo "  test-local - Ejecutar tests en el host con .venv"
	@echo ""
	@echo "  help       - Mostrar esta ayuda"
