.PHONY: benchmark benchmark-clean

benchmark:
	docker compose -f benchmarks/docker-compose.yml up --build --abort-on-container-exit
	@echo ""
	@echo "Results in benchmarks/results/"

benchmark-clean:
	docker compose -f benchmarks/docker-compose.yml down --rmi local
	rm -rf benchmarks/results
