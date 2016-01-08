import sys
import os
import shutil
import re
from setuptools import setup

setup(
    name='cuvner',
    version='0.0.0',
    description='A commanding view of your test-coverage.',
    long_description=open('cuv/README.rst', 'r').read(),
    keywords=['python', 'twisted'],
    install_requires=[
        'pygments',
        'click',
        'ansicolors',
        'coverage',
        'svgwrite',
        'six',
        'Pillow',
    ],
    author='meejah',
    author_email='meejah@meejah.ca',
    url='fixme',
    license='MIT',
    packages=['cuv'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'cuv=cuv.cli:cuv',
        ],
        'pygments.lexer': [
            'pixel = cuv.formatter.PixelFormatter',
        ]
    },
)
