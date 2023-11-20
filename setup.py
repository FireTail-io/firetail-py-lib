#!/usr/bin/env python3

import inspect
import os
import sys

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand

__location__ = os.path.join(os.getcwd(), os.path.dirname(inspect.getfile(inspect.currentframe())))


def read_version(package):
    with open(os.path.join(package, "__init__.py")) as fd:
        for line in fd:
            if line.startswith("__version__ = "):
                return line.split()[-1].strip().strip("'")


version = read_version("firetail")

install_requires = [
    "clickclick>=1.2,<21",
    "jsonschema>=4.0.1,<5",
    "PyYAML>=6.0.1,<7",
    "PyJWT>=2.4.0",
    "requests>=2.31,<3",
    "inflection>=0.3.1,<0.6",
    "werkzeug>=2.2.2,<3",
    "starlette>=0.27,<1",
    "packaging>=23.2",
]

swagger_ui_require = "swagger-ui-bundle>=0.0.2,<0.1"

flask_require = [
    "flask[async]==2.2.5",
    "a2wsgi>=1.4,<2",
]

aiohttp_require = [
    "aiohttp>=2.3.10,<4",
    "aiohttp-jinja2>=0.14.0,<2",
    "MarkupSafe>=0.23",
]

tests_require = ["pytest>=6,<7", "pytest-cov>=2,<3", "testfixtures>=6,<7", *flask_require, swagger_ui_require]

tests_require.extend(aiohttp_require)
tests_require.append("pytest-aiohttp")
tests_require.append("aiohttp-remotes")

docs_require = ["sphinx-autoapi==1.8.1"]


class PyTest(TestCommand):
    user_options = [("cov-html=", None, "Generate junit html report")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.cov = None
        self.pytest_args = ["--cov", "firetail", "--cov-report", "term-missing", "-v"]
        self.cov_html = False

    def finalize_options(self):
        TestCommand.finalize_options(self)
        if self.cov_html:
            self.pytest_args.extend(["--cov-report", "html"])
        self.pytest_args.extend(["tests"])

    def run_tests(self):
        import pytest

        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


def readme():
    try:
        return open("README.rst", encoding="utf-8").read()
    except TypeError:
        return open("README.rst").read()


setup(
    name="firetail",
    packages=find_packages(),
    version=version,
    description="Firetail - API first applications with OpenAPI/Swagger and Flask",
    long_description=readme(),
    # long_description_content_type="text/x-rst",
    author="FireTail International (TM)",
    url="https://github.com/FireTail-io/firetail-py-lib",
    keywords="openapi oai swagger rest api oauth flask microservice framework",
    license="LGPLv3",
    # setup_requires=['flake8'],
    python_requires=">=3.6",
    install_requires=install_requires + flask_require,
    tests_require=tests_require,
    extras_require={
        "tests": tests_require,
        "flask": flask_require,
        "swagger-ui": swagger_ui_require,
        "docs": docs_require,
    },
    cmdclass={"test": PyTest},
    test_suite="tests",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    # needed to include swagger-ui (see MANIFEST.in)
    include_package_data=True,
    entry_points={"console_scripts": ["Firetail = Firetail.cli:main"]},
)
