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

# Do not tag/push on Go CD
if [ -z "$GO_PIPELINE_LABEL" ]; then
    python3 setup.py clean
    python3 setup.py test
    python3 setup.py flake8

    git add */__init__.py

    git commit -m "Bumped version to $version"
    git push
fi

python3 setup.py sdist bdist_wheel upload

if [ -z "$GO_PIPELINE_LABEL" ]; then
    git tag ${version}
    git push --tags
fi
