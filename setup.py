from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="netbridge",
    version="0.1.0",
    author="Dani ISsac",
    author_email="reachme@daniissac.com",
    description="Convert CML/VIRL YAML files to GNS3 projects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/daniissac/netbridge",
    project_urls={
        "Bug Tracker": "https://github.com/daniissac/netbridge/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Networking",
    ],
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
        "jinja2>=3.0.0",
        "jsonschema>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "netbridge=netbridge.cli:main",
        ],
    },
)