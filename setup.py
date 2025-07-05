from setuptools import setup, find_packages

setup(
    name="pocketoptionapi",
    version="1.8.6",
    description="PocketOption API v1: cliente síncrono y streaming empaquetado",
    author="yosoyjorgeh29",
    url="https://github.com/yosoyjorgeh29/merakbotapi",
    # Esto le dice a setuptools que busque paquetes dentro de la carpeta PocketOptionAPI
    packages=find_packages(where="PocketOptionAPI"),
    package_dir={"": "PocketOptionAPI"},
    install_requires=[
        "websockets>=10.0.0",
        "pydantic>=1.8.2",
        "loguru>=0.5.3",
        "requests>=2.25.1",
        "tzlocal>=2.1",
        "python-dateutil>=2.8.1",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
