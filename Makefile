PYTHON ?= python3
LOCAL_MARIADB_URL ?= mysql://campusflow:campusflow_dev@127.0.0.1:3307/campusflow

.PHONY: verify jsonl-smoke local-db-up local-db-down local-db-import local-db-check local-db-smoke local-db-demo

verify:
	$(PYTHON) scripts/validate_data.py
	$(PYTHON) scripts/verify_integrity.py
	$(PYTHON) scripts/verify_rag_refs.py

jsonl-smoke:
	DATA_BACKEND=jsonl $(PYTHON) scripts/smoke_test_mcp.py

local-db-up:
	docker compose up -d mariadb

local-db-down:
	docker compose down

local-db-import:
	DATA_BACKEND=mariadb MARIADB_URL="$(LOCAL_MARIADB_URL)" $(PYTHON) scripts/import_mariadb.py

local-db-check:
	DATA_BACKEND=mariadb MARIADB_URL="$(LOCAL_MARIADB_URL)" $(PYTHON) scripts/check_mariadb_backend.py

local-db-smoke:
	DATA_BACKEND=mariadb MARIADB_URL="$(LOCAL_MARIADB_URL)" $(PYTHON) scripts/smoke_test_mcp.py

local-db-demo: local-db-up
	@echo "Waiting for local MariaDB to accept connections..."
	@sleep 10
	$(MAKE) local-db-import
	$(MAKE) local-db-check
	$(MAKE) local-db-smoke

