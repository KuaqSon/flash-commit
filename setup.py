from setuptools import setup

setup(
    name="flash_commit",
    version="0.0.1",
    install_requires=["typer[all]", "tiktoken", "openai"],
    entry_points={
        "console_scripts": ["flash_commit=flash_commit:main"]
    },
)
