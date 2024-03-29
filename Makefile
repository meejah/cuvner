# chicken-and-egg problem a bit here; run "make venv" first before
# creating this variable works properly :/
VERSION = ${shell ./venv/bin/python -c 'import cuv; print("{v.major}.{v.minor}.{v.micro}".format(v=cuv.__version__))'}

version: venv
	echo "Version:" ${VERSION}

venv: setup.py
	-virtualenv venv
	./venv/bin/pip install --editable .[dev]
	echo ${VERSION}

dist: dist/cuvner-${VERSION}-py2.py3-none-any.whl

dist-sigs: dist/cuvner-${VERSION}-py2.py3-none-any.whl.asc

dist/cuvner-${VERSION}-py2.py3-none-any.whl:
	python setup.py bdist_wheel

dist/cuvner-${VERSION}-py2.py3-none-any.whl.asc: dist/cuvner-${VERSION}-py2.py3-none-any.whl
	gpg --verify dist/cuvner-${VERSION}-py2.py3-none-any.whl.asc dist/cuvner-${VERSION}-py2.py3-none-any.whl || gpg --no-version --detach-sign --armor --local-user meejah@meejah.ca dist/cuvner-${VERSION}-py2.py3-none-any.whl

release: dist/cuvner-${VERSION}-py2.py3-none-any.whl.asc dist/cuvner-${VERSION}-py2.py3-none-any.whl
	twine check dist/cuvner-${VERSION}-py2.py3-none-any.whl
	git tag -u 0xC2602803128069A7 --message "Release ${VERSION}" v${VERSION}
	twine upload -r pypi -c "cuvner v${VERSION} wheel" dist/cuvner-${VERSION}-py2.py3-none-any.whl dist/cuvner-${VERSION}-py2.py3-none-any.whl.asc
	git push --tags
