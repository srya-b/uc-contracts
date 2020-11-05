from setuptools import setup, find_packages

setup(
    name='uc',
    version='0.1.0',
    description='Implementation of UC in python.',
    packages=find_packages(exclude=('teste', 'docs'))
)
