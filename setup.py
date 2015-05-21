#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from connexion.version import version


setup(
    name='connexion',
    packages=find_packages(),
    version=version,
    description='Connexion - API first applications with swagger and flask',
    long_description=open('README.rst').read(),
    author='Zalando SE',
    url='https://github.com/zalando/connexion',
    license='Apache License Version 2.0',
    install_requires=['flask', 'PyYAML', 'tornado', 'requests'],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    include_package_data=True,  # needed to include swagger-ui (see MANIFEST.in)

)
