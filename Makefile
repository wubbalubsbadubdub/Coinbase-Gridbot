.PHONY: dev down test

dev:
	docker-compose -f docker/docker-compose.yml up --build

down:
	docker-compose -f docker/docker-compose.yml down

test:
	docker-compose -f docker/docker-compose.yml run backend pytest
