.PHONY: dev test lint docs install demo demo-windows ui-demo ui-demo-windows clean

dev:
	docker-compose up

test:
	pytest tests/

lint:
	ruff check .

docs:
	mkdocs serve

install:
	pip install -e ".[ui]"

demo:
	bash scripts/demo.sh

demo-windows:
	powershell -ExecutionPolicy Bypass -File scripts/demo.ps1

ui-demo:
	bash scripts/ui_demo.sh

ui-demo-windows:
	powershell -ExecutionPolicy Bypass -File scripts/ui_demo.ps1

clean:
	docker-compose down
