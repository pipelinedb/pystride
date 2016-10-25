.PHONY: test dist

test:
	python setup.py test

install:
	python setup.py install

dist:
	python setup.py sdist upload -r pypi

installdeps:
	pip install -r requirements.txt

clean:
	find . -type f -name '*.py[cod]' -delete
