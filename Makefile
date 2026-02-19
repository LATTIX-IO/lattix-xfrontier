.PHONY: up down

up:
	docker compose -f docker-compose.local.yml up --build -d

down:
	docker compose -f docker-compose.local.yml down
