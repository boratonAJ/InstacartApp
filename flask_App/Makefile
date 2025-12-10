.PHONY: run venv install

run:
	bash run.sh

venv:
	python3.10 -m venv .venv

install: venv
	. .venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
