from setuptools import find_packages, setup

setup(
    name="FortyFour",
    version="2025.04.24-1",
    description="This package puts together all the tools I have created",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    author="44 SCIENTIFICS LTD",
    author_email="44scientifics@gmail.com",
    url="https://github.com/44Scientifics/44Packages.git",
)
