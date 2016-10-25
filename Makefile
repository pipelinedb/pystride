.PHONY: test dist

test:
	python setup.py test

install:
	python setup.py install

dist:
	python setup.py sdist upload

installdeps:
	pip install -r requirements.txt
