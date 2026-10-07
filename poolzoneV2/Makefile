.PHONY: dev db api web

# Everyday run: DB up, then backend + frontend together (Ctrl-C stops both).
dev: db
	./.venv/bin/uvicorn app.api.main:app --reload --port 8000 & \
	cd frontend && npm run dev & \
	wait

db:
	docker compose up -d

api: db
	./.venv/bin/uvicorn app.api.main:app --reload --port 8000

web:
	cd frontend && npm run dev
