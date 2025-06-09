from setuptools import setup, find_packages

setup(
    name="research-workflow",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "rich",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "research-workflow=src.cli:main",
        ],
    },
)
