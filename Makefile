fmt:
	ruff check --select I --fix .
	ruff format .

lint:
	ruff check .
	ruff format --check .