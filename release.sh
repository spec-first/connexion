#!/bin/sh

if [ $# -ne 1 ]; then
    >&2 echo "usage: $0 <version>"
    exit 1
fi

set -o errexit
set -o xtrace

python3 --version
git --version

version=$1

if [[ "$OSTYPE" == "darwin"* ]]; then
	sed -i "" "s/__version__ = .*/__version__ = '${version}'/" */__init__.py
else
	sed -i "s/__version__ = .*/__version__ = '${version}'/" */__init__.py
fi

tox -e py39-pypi,flake8 --skip-missing-interpreters

rm -fr dist/*
python3 setup.py sdist bdist_wheel
twine upload dist/*

# revert version
git checkout -- */__init__.py

git tag "${version}"
git push --tags
