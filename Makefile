.PHONY: install seed reseed dev stop clean reset check

# ── Setup ──────────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt

# ── Database ───────────────────────────────────────────────────────────────────

seed:
	python seed.py

seed-days:
	python seed.py $(DAYS)

reseed: clean seed

# ── Server ─────────────────────────────────────────────────────────────────────

dev:
	uvicorn aeo.api:app --port 8000 --reload

stop:
	pkill -f "uvicorn aeo.api" || true

# ── Maintenance ────────────────────────────────────────────────────────────────

clean:
	rm -f aeo.db

reset: stop clean seed

# ── Smoke test ─────────────────────────────────────────────────────────────────

check:
	@echo "Checking API endpoints..."
	@curl -sf http://localhost:8000/api/brands        > /dev/null && echo "  brands         OK"
	@curl -sf http://localhost:8000/api/topics        > /dev/null && echo "  topics         OK"
	@curl -sf http://localhost:8000/api/engines       > /dev/null && echo "  engines        OK"
	@curl -sf "http://localhost:8000/api/brands/1/overview"         > /dev/null && echo "  overview       OK"
	@curl -sf "http://localhost:8000/api/brands/1/visibility-score" > /dev/null && echo "  visibility     OK"
	@curl -sf "http://localhost:8000/api/brands/1/trend"            > /dev/null && echo "  trend          OK"
	@curl -sf "http://localhost:8000/api/brands/1/engines"          > /dev/null && echo "  engines-bkdn   OK"
	@curl -sf "http://localhost:8000/api/brands/1/top-queries"      > /dev/null && echo "  top-queries    OK"
	@curl -sf "http://localhost:8000/api/brands/1/top-pages"        > /dev/null && echo "  top-pages      OK"
	@curl -sf "http://localhost:8000/api/brands/1/gaps"             > /dev/null && echo "  gaps           OK"
	@curl -sf "http://localhost:8000/api/brands/1/recommendations"  > /dev/null && echo "  recs           OK"
	@curl -sf "http://localhost:8000/api/brands/1/by-intent"        > /dev/null && echo "  by-intent      OK"
	@curl -sf "http://localhost:8000/api/topics/1/share-of-voice"   > /dev/null && echo "  share-of-voice OK"
	@curl -sf "http://localhost:8000/api/explore?q=crm"             > /dev/null && echo "  explore        OK"
	@echo "All checks passed."
