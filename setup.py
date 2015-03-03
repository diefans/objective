"""setup for objective"""

import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


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
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "python-dateutil",
        "pytz"
    ],
    tests_require=[
        "pytest",
        "pytest-random",
        "pytest-pep8",
    ],
    cmdclass={'test': PyTest},
)
