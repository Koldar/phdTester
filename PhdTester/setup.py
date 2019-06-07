from typing import Iterable

import semantic_version
from setuptools import setup, find_packages

VERSION = "0.4-alpha"


def load_readme() -> str:
    with open("README.md", "r") as fh:
        return fh.read()


def load_requirements() -> Iterable[str]:
    useless = [
        "ansicolors",
        "bleach",
        "certifi",
        "chardet",
        "coloredlogs",
        "cycler",
        "docutils",
        "humanfriendly",
        "idna",
        "kiwisolver",
        "pkg-resources",
        "pkginfo",
        "Pygments",
        "pyparsing",
        "python-dateutil",
        "readme-renderer",
        "requests",
        "requests-toolbelt",
        "setuptools",
        "six",
        "tqdm",
        "twine",
        "urllib3",
        "webencodings",
    ]

    with open("requirements.txt", "r") as fh:
        for l in fh.readlines():
            l = l.strip()
            name = l.split("==")[0]
            version = semantic_version.Version.coerce(l.split("==")[1])
            min = version
            max = version.next_major()
            if l.split("==")[0] not in useless:
                result = f"{name}>={min},<{max}"
                print(f"add {result} to the requirements...")
                yield result

setup(
    name='phd-tester',
    version=VERSION,
    author='Massimo Bono',
    author_email='massimobono1@gmail.com',
    description="""
        Package to generate all possible combinations of your awesome research program. Then it generates plots and a
        pdf report.
    """,
    long_description=load_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Koldar/phdTester",
    packages=find_packages(),
    install_requires=list(load_requirements()),
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Testing",
        "Intended Audience :: Science/Research",
    ],


)
