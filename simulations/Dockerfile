FROM python:3.10

WORKDIR /
COPY simulations simulations
COPY README.md README.md

RUN pip install --no-cache-dir poetry==1.5.1
COPY pyproject.toml pyproject.toml
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --extras torch


# PROCESS TO INSTALL PYCIEMSS
COPY pyciemss pyciemss
WORKDIR /pyciemss
RUN pip install --no-cache-dir --default-timeout=900 -e .

WORKDIR /simulations