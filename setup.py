from setuptools import setup, find_packages

setup(
    name="pocketoptionapi",
    version="1.8.6",
    description="PocketOption API v1: cliente síncrono y streaming empaquetado",
    author="TU_USUARIO",
    url="https://github.com/TU_USUARIO/PocketOptionAPI",
    # Asume que has renombrado 'pocketoptionapi_async/' a 'pocketoptionapi/' en tu fork
    packages=find_packages(include=["pocketoptionapi", "pocketoptionapi.*"]),
    install_requires=[
        "websockets>=10.0.0",     # para WS
        "pydantic>=1.8.2",        # modelos de datos
        "loguru>=0.5.3",          # logging mejorado
        "requests>=2.25.1",       # REST
        "tzlocal>=2.1",           # zona horaria local
        "python-dateutil>=2.8.1", # parseo de fechas
    ],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
