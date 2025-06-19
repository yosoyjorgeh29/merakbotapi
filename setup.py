"""
Setup script for the Professional Async PocketOption API
"""

from setuptools import setup, find_packages

with open("README_ASYNC.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="pocketoption-async-api",
    version="2.0.0",
    author="PocketOptionAPI Team",
    author_email="support@pocketoptionapi.com",
    description="Professional async PocketOption API with modern Python practices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/PocketOptionAPI",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "examples": [
            "jupyter>=1.0.0",
            "matplotlib>=3.5.0",
            "seaborn>=0.11.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pocketoption-migrate=migration_guide:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/your-username/PocketOptionAPI/issues",
        "Source": "https://github.com/your-username/PocketOptionAPI",
        "Documentation": "https://github.com/your-username/PocketOptionAPI#readme",
    },
    keywords="pocketoption trading api async binary options forex crypto",
    include_package_data=True,
    zip_safe=False,
)
