#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inspect
import os
import platform
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

__location__ = os.path.join(os.getcwd(), os.path.dirname(inspect.getfile(inspect.currentframe())))


def read_version(package):
    with open(os.path.join(package, '__init__.py'), 'r') as fd:
        for line in fd:
            if line.startswith('__version__ = '):
                return line.split()[-1].strip().strip("'")

version = read_version('connexion')

py_major_version, py_minor_version, _ = (int(v.rstrip('+')) for v in platform.python_version_tuple())


def get_install_requirements(path):
    content = open(os.path.join(__location__, path)).read()
    requires = [req for req in content.split('\\n') if req != '']
    if py_major_version == 2 or (py_major_version == 3 and py_minor_version < 4):
        requires.append('pathlib')
    return requires


class PyTest(TestCommand):

    user_options = [('cov-html=', None, 'Generate junit html report')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.cov = None
        self.pytest_args = ['--cov', 'connexion', '--cov-report', 'term-missing', '-v']
        self.cov_html = False

    def finalize_options(self):
        TestCommand.finalize_options(self)
        if self.cov_html:
            self.pytest_args.extend(['--cov-report', 'html'])

    def run_tests(self):
        import pytest

        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='connexion',
    packages=find_packages(),
    version=version,
    description='Connexion - API first applications with OpenAPI/Swagger and Flask',
    long_description=open('README.rst').read(),
    author='Zalando SE',
    url='https://github.com/zalando/connexion',
    keywords='openapi oai swagger rest api oauth flask microservice framework',
    license='Apache License Version 2.0',
    setup_requires=['flake8'],
    install_requires=get_install_requirements('requirements.txt'),
    tests_require=['pytest-cov', 'pytest', 'mock', 'decorator'],
    cmdclass={'test': PyTest},
    test_suite='tests',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
    ],
    include_package_data=True,  # needed to include swagger-ui (see MANIFEST.in)

)
