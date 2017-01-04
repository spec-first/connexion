#!/bin/sh

if [ $# -ne 1 ]; then
    >&2 echo "usage: $0 <version>"
    exit 1
fi

set -xe

python3 --version
git --version

version=$1

sed -i "s/__version__ = .*/__version__ = '${version}'/" */__init__.py

tox

python3 setup.py sdist bdist_wheel upload

git tag ${version}
git push --tags

# revert version
git co -- */__init__.py
