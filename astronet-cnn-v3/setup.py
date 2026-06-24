from setuptools import setup, find_packages

setup(
    name="kepler-input",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
    ],
    python_requires=">=3.8",
    author="EXOPLANET HUNTERS Team",
    description="Módulo para descargar datos Kepler y ejecutar Astronet automáticamente",
    url="https://github.com/exoplanet-hunters/astronet-cnn-v3",
)
