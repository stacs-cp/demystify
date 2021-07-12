from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="demystify",
    version="0.0.10",
    description="Demystify is a tool which allows puzzles to be expressed in a high-level constraint programming language and uses MUSes to automatically produce descriptions of steps in the puzzle solving.",
    packages = ['demystify', 'demystify.solvers'],
    url="https://github.com/stacs-cp/demystify",
    author="Chris Jefferson",
    author_email="caj21@st-andrews.ac.uk",
    classifiers=[
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
    ],
    install_requires = [
        "python-sat",
        "z3-solver",
        "numpy",
        "sortedcontainers"
    ],
    long_description=long_description,
    long_description_content_type="text/markdown"

)