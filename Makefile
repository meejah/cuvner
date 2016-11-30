# chicken-and-egg problem a bit here; run "make venv" first before
# creating this variable works properly :/
VERSION = ${shell ./venv/bin/python -c 'import cuv; print("{v.major}.{v.minor}.{v.micro}".format(v=cuv.__version__))'}

version: venv
	echo "Version:" ${VERSION}

venv: setup.py
	-virtualenv venv
	./venv/bin/pip install --editable .[dev]
	echo ${VERSION}

dist: dist/cuvner-${VERSION}-py2-none-any.whl

dist-sigs: dist/cuvner-${VERSION}-py2-none-any.whl.asc

dist/cuvner-${VERSION}-py2-none-any.whl:
	python setup.py bdist_wheel

dist/cuvner-${VERSION}-py2-none-any.whl.asc: dist/cuvner-${VERSION}-py2-none-any.whl
	gpg --verify dist/cuvner-${VERSION}-py2-none-any.whl.asc || gpg --no-version --detach-sign --armor --local-user meejah@meejah.ca dist/cuvner-${VERSION}-py2-none-any.whl

release: dist/cuvner-${VERSION}-py2-none-any.whl.asc dist/cuvner-${VERSION}-py2-none-any.whl
	twine upload -r pypi -c "cuvner v${VERSION} wheel" dist/cuvner-${VERSION}-py2-none-any.whl dist/cuvner-${VERSION}-py2-none-any.whl.asc
