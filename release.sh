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

poetry version ${version}

poetry lock
poetry install -E dev
#tox -e py27-pypi,py35-pypi,py36-pypi,isort-check,isort-check-examples,isort-check-tests,flake8 --skip-missing-interpreters
poetry run

poetry build # TODO publish

# revert version
git checkout -- */__init__.py
poetry version 2018.dev

git tag -s ${version} -m "${version}"
git push --tags
