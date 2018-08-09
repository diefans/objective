"""setup for objective"""

import os
import sys

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand

__version__ = "0.0.12"


def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()


class PyTest(TestCommand):
    """Our test runner."""

    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        # pylint: disable=W0201
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name="objective",
    author="Oliver Berger",
    author_email="diefans@gmail.com",
    url="https://github.com/diefans/objective",
    description="declarative de/serialization of python structures",
    long_description=read('README.rst'),
    version=__version__,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
    ],

    keywords=("serialization deserialization serialize deserialize declarative"
              " object objective schema validation"),

    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "python-dateutil",
        "pytz",
        "validate_email",
    ],
    tests_require=[
        "pytest",
        "pytest-random",
        "pytest-pep8",
        "pytest-cov"
    ],
    cmdclass={'test': PyTest},
)
