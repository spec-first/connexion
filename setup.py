#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import platform
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

version = '0.11.2'
py_major_version, py_minor_version, _ = (int(v) for v in platform.python_version_tuple())

requires = ['flask', 'PyYAML', 'requests', 'six', 'strict-rfc3339']

if py_major_version == 2 or (py_major_version == 3 and py_minor_version < 4):
    requires.append('pathlib')


class PyTest(TestCommand):
    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.cov = None
        self.pytest_args = ['--cov', 'connexion', '--cov-report', 'term-missing']

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest

        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='connexion',
    packages=find_packages(),
    version=version,
    description='Connexion - API first applications with Swagger and Flask',
    long_description=open('README.rst').read(),
    author='Zalando SE',
    url='https://github.com/zalando/connexion',
    keywords='swagger rest api oauth flask microservice framework',
    license='Apache License Version 2.0',
    install_requires=requires,
    tests_require=['pytest-cov', 'pytest', 'mock'],
    cmdclass={'test': PyTest},
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    include_package_data=True,  # needed to include swagger-ui (see MANIFEST.in)

)
