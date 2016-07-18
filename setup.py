"""setup for objective"""

import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

__version__ = "0.0.9"


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
    version=__version__,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
    ],

    keywords="serialization deserialization serialize deserialize declarative object objective validation suckless",

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
