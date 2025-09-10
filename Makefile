SHELL := /bin/bash

.PHONY: test test-sqlite docker-up-http docker-test-sqlite docker-down

test:
	PYTHONPATH=src pytest -q -o asyncio_mode=auto

test-sqlite:
	PYTHONPATH=src pytest -q -o asyncio_mode=auto tests/test_sqlite_vec_storage.py

docker-up-http:
	cd tools/docker && docker compose up -d

docker-test-sqlite: docker-up-http
	CID=$$(docker ps --format '{{.ID}} {{.Names}}' | awk '$$2=="docker-mcp-memory-service-1"{print $$1}'); \
	if [ -z "$$CID" ]; then echo "Container not running"; exit 1; fi; \
	docker cp tests $$CID:/app/tests; \
	docker cp pytest.ini $$CID:/app/pytest.ini; \
	docker exec $$CID sh -lc 'python -m pip install -q pytest pytest-asyncio && PYTHONPATH=/app pytest -q -o asyncio_mode=auto tests/test_sqlite_vec_storage.py';

docker-down:
	cd tools/docker && docker compose down
