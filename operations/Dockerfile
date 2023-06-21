FROM python:3.10

RUN pip install --no-cache-dir poetry==1.5.1
ADD pyproject.toml pyproject.toml
ADD poetry.lock poetry.lock
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --extras worker

# PROCESS TO INSTALL PYCIEMSS
COPY pyciemss pyciemss
WORKDIR /pyciemss
RUN pip install --no-cache-dir --default-timeout=900 -e .

WORKDIR /
COPY operations operations
COPY README.md README.md

WORKDIR /operations