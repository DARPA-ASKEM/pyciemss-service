FROM python:3.10

RUN pip install poetry
WORKDIR /api
COPY README.md README.md

ADD pyproject.toml pyproject.toml

RUN poetry config virtualenvs.create false && \
    poetry install --no-root

EXPOSE 8000