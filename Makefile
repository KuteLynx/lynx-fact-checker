.PHONY: dev-backend dev-frontend dev build clean deploy-backend

dev-backend:
	cd backend && uv run uvicorn main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Abre dos terminales:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"
	@echo ""
	@echo "Frontend: http://localhost:5173"
	@echo "Backend:  http://localhost:8000"

build:
	cd frontend && npm run build

clean:
	rm -rf frontend/dist backend/.venv

# Producción (backend)
deploy-backend:
	cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
