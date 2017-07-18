.PHONY: test dist

test:
	python setup.py test

install:
	python setup.py install

dist:
	python setup.py sdist
	twine upload dist/*.tar.gz

installdeps:
	pip install -r requirements.txt

clean:
	find . -type f -name '*.py[cod]' -delete
	find . -type d -name '__pycache__' -delete
