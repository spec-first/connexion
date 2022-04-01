#!/usr/bin/env python3

import inspect
import os

from setuptools import find_packages, setup

__location__ = os.path.join(os.getcwd(), os.path.dirname(inspect.getfile(inspect.currentframe())))


def read_version(package):
    with open(os.path.join(package, "__init__.py")) as fd:
        for line in fd:
            if line.startswith("__version__ = "):
                return line.split()[-1].strip().strip('"')


version = read_version("especifico")

install_requires = [
    "jsonschema>=2.5.1,<5",
    "PyYAML>=5.1,<7",
    "requests>=2.19.1,<3",
    "inflection>=0.3.1,<0.6",
    "werkzeug>=1.0,<3",
    'importlib-metadata>=1 ; python_version<"3.8"',
    "packaging>=20",
]

swagger_ui_require = "swagger-ui-bundle>=0.0.2,<0.1"

flask_require = [
    "flask>=1.0.4,<3",
    "itsdangerous>=0.24",
]
aiohttp_require = [
    "aiohttp>=2.3.10,<4",
    "aiohttp-jinja2>=0.14.0,<2",
    "MarkupSafe>=0.23",
]


def tests_require():
    return open("requirements-test.txt", encoding="utf-8").read().split("\n")


docs_require = ["sphinx-autoapi==1.8.1"]


def readme():
    return open("README.md", encoding="utf-8").read()


setup(
    name="especifico",
    packages=find_packages(),
    version=version,
    description="Específico - API first applications with OpenAPI/Swagger and Flask",
    long_description=readme(),
    long_description_content_type="text/markdown",
    author="Zalando SE & Athenian",
    url="https://github.com/athenianco/especifico",
    keywords="openapi oai swagger rest api oauth flask microservice framework",
    license="Apache License Version 2.0",
    python_requires=">=3.8",
    install_requires=install_requires + flask_require,
    tests_require=tests_require(),
    extras_require={
        "cli": ["clickclick>=1.2,<21"],
        "tests": tests_require(),
        "flask": flask_require,
        "swagger-ui": swagger_ui_require,
        "aiohttp": aiohttp_require,
        "docs": docs_require,
    },
    test_suite="tests",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    include_package_data=True,  # needed to include swagger-ui (see MANIFEST.in)
    entry_points={"console_scripts": ["especifico = especifico.cli:main"]},
)
