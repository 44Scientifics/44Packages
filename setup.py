import os
from datetime import datetime

from setuptools import find_packages, setup


def build_version() -> str:
    version = os.environ.get("FORTYFOUR_VERSION")
    if version:
        return version

    today = datetime.now()
    return f"{today.year}.{today.month}.{today.day}"


with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()

setup(
    name="FortyFour",
    version=build_version(),
    description="This package puts together all the tools I have created",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    author="44 SCIENTIFICS LTD",
    author_email="44scientifics@gmail.com",
    url="https://github.com/44Scientifics/44Packages.git",
)
