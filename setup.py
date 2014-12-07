from setuptools import setup, find_packages


setup(
    name="objective",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    #namespace_packages=['da'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "pytest",
        "pytest-random",
        "pytest-cov",
        "pytest-greendots",
        "pytest-pep8",
        "pylama",
        "pylama-pylint"
    ],
    tests_require=[],
)
