.PHONY: run test install install-dev lint clean

run:
	python main.py

test:
	python -m pytest tests/ -v

install:
	pip install -r requirements.txt

install-dev:
	pip install -e ".[dev]"

lint:
	python -m py_compile src/agent.py
	python -m py_compile src/rag.py
	python -m py_compile src/tools.py
	python -m py_compile src/api.py
	python -m py_compile src/config.py
	python -m py_compile main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf dist/ build/ *.egg-info
