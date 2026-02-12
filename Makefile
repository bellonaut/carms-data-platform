.PHONY: demo demo-windows demo-local demo-local-windows stop-local clean

demo:
	bash scripts/demo.sh

demo-windows:
	powershell -ExecutionPolicy Bypass -File scripts/demo.ps1

demo-local:
	bash scripts/demo_local.sh

demo-local-windows:
	powershell -ExecutionPolicy Bypass -File scripts/demo_local.ps1

stop-local:
	@if [ -f .demo-local.pids ]; then xargs kill < .demo-local.pids && rm .demo-local.pids; fi

clean:
	docker-compose down
