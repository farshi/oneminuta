#!/usr/bin/env python3
"""
Setup script for OneMinuta CLI
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "OneMinuta - Property Marketplace Platform"

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
else:
    requirements = [
        "telethon>=1.28.0",
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
        "pytest>=7.0.0",
    ]

setup(
    name="oneminuta",
    version="1.0.0",
    description="Property marketplace platform with geo-sharded storage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="OneMinuta Team",
    author_email="dev@oneminuta.com",
    url="https://github.com/oneminuta/oneminuta",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "oneminuta=oneminuta_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Database :: Database Engines/Servers",
    ],
    keywords="property marketplace geo-sharding telegram analytics",
    project_urls={
        "Documentation": "https://github.com/oneminuta/oneminuta/blob/main/README.md",
        "Source": "https://github.com/oneminuta/oneminuta",
        "Tracker": "https://github.com/oneminuta/oneminuta/issues",
    },
)