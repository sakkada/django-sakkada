.PHONY: clean develop

help:
	@echo "clean - remove Python file artifacts"
	@echo "develop - prepare environment for developing"
	@echo "lint - check style (flake8, isort)"
	@echo "lint.report - check style and report to according files"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run test in all allowed environments (tox)"
	@echo "coverage - check code coverage quickly with the default Python"

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +

develop:
	pip install -e .[testing,docs]

lint:
	flake8 sakkada tests --show-source
	isort --check-only --diff --recursive sakkada tests

lint.text:
	flake8 sakkada tests --output-file=.flake8.text --show-source --exit-zero
	isort --check-only --diff --recursive sakkada tests > .isort.text

test:
	python tests/manage.py makemigrations
	python tests/manage.py test tests

test-all:
	tox

coverage:
	python -m coverage run tests/manage.py test tests
	python -m coverage report -m
	python -m coverage html
	open .coverage.html/index.html
