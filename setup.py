'''
Python client for Stride

Copyright (c) 2016 PipelineDB
'''
import os
import sys

from setuptools import setup

# Don't import stride module here, since dependencies may not be installed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stride'))
from version import VERSION  # noqa

long_description = '''
This is the official Python client that wraps the Stride HTTP API

Learn more at https://stride.io/.
'''

setup(
    name='stride',
    version=VERSION,
    url='https://github.com/pipelinedb/pystride',
    author='PipelineDB',
    author_email='eng@pipelinedb.com',
    maintainer='PipelineDB',
    maintainer_email='eng@pipelinedb.com',
    packages=['stride', 'stride.test'],
    license='MIT License',
    install_requires=['requests>=2.6.1'],
    setup_requires=['pytest-runner>=2.9'],
    tests_require=['pytest>=2.6.3', 'responses>=0.5.1'],
    description='Python client for Stride',
    long_description=long_description,
    classifiers=[
        'Development Status :: 4 - Beta', 'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent', 'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
    ], )
