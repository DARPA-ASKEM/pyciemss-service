FROM python:3.10

RUN pip install --no-cache-dir poetry==1.5.1
WORKDIR /api
COPY README.md README.md

COPY pyproject.toml pyproject.toml

RUN poetry config virtualenvs.create false && \
    poetry install --no-root

EXPOSE 8000