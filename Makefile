.PHONY: all python-poetry python-dependencies git-hooks-init build run

all: python-poetry python-dependencies git-hooks-init
	echo "---- Your working directory is all set :) ----"

python-poetry:
	@echo "---- Installing Python Poetry ----"
	pip install -U pip
	pip install -U poetry
	poetry config virtualenvs.in-project true
	poetry config virtualenvs.path ".venv"

python-dependencies: python-poetry
	@echo "---- Installing Python dependencies ----"
	poetry install

git-hooks-init:
	@echo "---- Git hooks init (using Gookme) ----"
	curl -sSL https://raw.githubusercontent.com/LMaxence/gookme/main/scripts/install.sh | bash
	gookme init --all

build:
	docker build -t app-cli .

run:
	@if [ -z "$(file)" ]; then \
		echo "Error: Please specify a file with 'make run file=/path/to/scan.zip'"; \
		exit 1; \
	fi
	docker run -it -v $(file):/app/scan.zip app-cli analyze /app/scan.zip