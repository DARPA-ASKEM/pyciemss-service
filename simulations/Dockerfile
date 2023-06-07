FROM python:3.10

COPY simulations simulations
COPY README.md README.md

RUN pip install --no-cache-dir poetry
ADD pyproject.toml pyproject.toml
RUN poetry config virtualenvs.create false && \
    poetry install --no-root


# PROCESS TO INSTALL PYCIEMSS
COPY pyciemss pyciemss
WORKDIR /pyciemss
RUN pip install --default-timeout=900 -e .

WORKDIR /simulations