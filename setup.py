from setuptools import setup, find_packages

setup(
    name="pocketoptionapi",
    version="1.8.6",
    description="PocketOption API v1: cliente síncrono y streaming empaquetado",
    author="yosoyjorgeh29",
    url="https://github.com/yosoyjorgeh29/merakbotapi",
    packages=find_packages(include=["pocketoptionapi", "pocketoptionapi.*"]),
    install_requires=[
        "websockets>=10.0.0",     # Cliente WebSocket
        "pydantic>=1.8.2",        # Modelos de datos
        "loguru>=0.5.3",          # Logging mejorado
        "requests>=2.25.1",       # Llamadas REST
        "tzlocal>=2.1",           # Zona horaria local
        "python-dateutil>=2.8.1", # Parseo de fechas
    ],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
