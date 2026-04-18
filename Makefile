.PHONY: clean-all clean-start-nasiko backend-app router orchestrator redis-listener start-nasiko compose-up gateway-logs gateway-restart help

# Default target
help:
	@echo "Available targets:"
	@echo "  clean-all            - Stop all containers, remove volumes and images"
	@echo "  clean-start-nasiko   - Clean all and start orchestrator services"
	@echo "  start-nasiko         - Delete all volumes and bring up full stack (compose + gateway + listener)"
	@echo "  compose-up           - Bring up docker-compose.local.yml stack with .nasiko-local.env"
	@echo "  gateway-logs         - Tail LLM gateway logs"
	@echo "  gateway-restart      - Restart LLM gateway (picks up config.yaml changes)"
	@echo "  backend-app          - Stop app compose, remove app backend image, start app compose, start redis listener"
	@echo "  router               - Stop router compose, remove router image, start router compose"
	@echo "  orchestrator         - Run orchestrator service"
	@echo "  redis-listener       - Run redis stream listener"
	@echo "  help                 - Show this help message"

# Stop all containers, clear volumes and images
clean-all:
	@echo "Stopping all Docker containers..."
	-docker stop $$(docker ps -aq)
	@echo "Removing all Docker containers..."
	-docker rm $$(docker ps -aq)
	@echo "Removing all Docker volumes..."
	-docker volume rm $$(docker volume ls -q)
	@echo "Removing all Docker images..."
	-docker rmi $$(docker images -q)
	@echo "Docker cleanup complete!"

# Clean everything and start orchestrator services
clean-start-nasiko: clean-all
	@$(MAKE) orchestrator
	@$(MAKE) redis-listener

# Stop app compose, remove app backend image, start app compose, start redis listener
backend-app:
	@echo "Stopping app docker compose..."
	-docker compose -f app/docker-compose.app.yaml down
	@echo "Removing app-nasiko-backend image..."
	-docker rmi app-nasiko-backend
	@echo "Starting app docker compose..."
	-docker compose -f app/docker-compose.app.yaml up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@$(MAKE) redis-listener
	@echo "App services restarted"

# Stop router compose, remove router image, restart router compose
router:
	@echo "Stopping router docker compose..."
	-docker compose -f router/docker-compose.yml down
	@echo "Removing router image..."
	-docker rmi router-app
	@echo "Starting router docker compose..."
	-docker compose -f router/docker-compose.yml up -d
	@echo "Router services restarted"

# Run orchestrator service
orchestrator:
	@echo "Starting orchestrator..."
	uv run orchestrator/orchestrator.py

# Run redis stream listener
redis-listener:
	@echo "Starting redis stream listener..."
	uv run orchestrator/redis_stream_listener.py

# Delete all volumes and bring up the full stack (compose + LLM gateway + listener)
start-nasiko:
	@echo "Stopping all Docker containers..."
	-docker stop $$(docker ps -aq)
	@echo "Removing all Docker containers..."
	-docker rm $$(docker ps -aq)
	@echo "Removing all Docker volumes..."
	-docker volume rm $$(docker volume ls -q)
	@echo "Docker cleanup complete!"
	@$(MAKE) compose-up

# Bring up docker-compose.local.yml with explicit env passthrough.
# This is the canonical local entrypoint — includes the LLM gateway.
compose-up:
	@echo "Starting Nasiko local stack (backend, gateway, kong, phoenix, listener)..."
	OPENAI_API_KEY=$$(grep ^OPENAI_API_KEY .nasiko-local.env 2>/dev/null | cut -d= -f2-) \
	OPENROUTER_API_KEY=$$(grep ^OPENROUTER_API_KEY .nasiko-local.env 2>/dev/null | cut -d= -f2-) \
	ANTHROPIC_API_KEY=$$(grep ^ANTHROPIC_API_KEY .nasiko-local.env 2>/dev/null | cut -d= -f2-) \
	LITELLM_MASTER_KEY=$$(grep ^LITELLM_MASTER_KEY .nasiko-local.env 2>/dev/null | cut -d= -f2-) \
	docker compose --env-file .nasiko-local.env -f docker-compose.local.yml up -d
	@echo "Stack up. Gateway: http://localhost:4500  Phoenix: http://localhost:6006  Kong: http://localhost:9100"

gateway-logs:
	docker logs -f llm-gateway

gateway-restart:
	@echo "Restarting LLM gateway (reloads config.yaml)..."
	docker compose --env-file .nasiko-local.env -f docker-compose.local.yml up -d --force-recreate llm-gateway