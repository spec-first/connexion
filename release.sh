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

tox --skip-missing-interpreters

python3 setup.py sdist bdist_wheel
#twine upload dist/*

# revert version
git checkout -- */__init__.py

git tag -s ${version} -m "${version}"
git push --tags
