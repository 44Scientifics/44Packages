from setuptools import find_packages, setup


with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()

setup(
    name="FortyFour",
    version="2025.05.24",
    description="This package puts together all the tools I have created",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    author="44 SCIENTIFICS LTD",
    author_email="44scientifics@gmail.com",
    url="https://github.com/44Scientifics/44Packages.git",
)
