import sys
import os
import shutil
import re
from setuptools import setup

setup(
    name='cuvner',
    use_incremental=True,
    setup_requires=['incremental'],
    description='A commanding (terminal) view of your test-coverage.',
    long_description=open('cuv/README.rst', 'r').read(),
    keywords=['python', 'coverage'],
    install_requires=[
        'pygments',
        'click',
        'ansicolors==1.0.2',
        'coverage',
        'six',
        'incremental',
        'unidiff',
        'watchdog',
    ],
    extras_require={
        "dev": [
            "Sphinx",
            "wheel",
        ]
    },
    author='meejah',
    author_email='meejah@meejah.ca',
    url='https://meejah.ca/projects/cuvner',
    license='MIT',
    packages=['cuv'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'cuv=cuv.cli:cuv',
        ],
    },
)
