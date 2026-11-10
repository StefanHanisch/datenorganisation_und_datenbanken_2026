# syntax=docker/dockerfile:1
# Stages sorted by how rarely they change, so Docker can reuse the cache:
#   deps    -> only rebuilt when pyproject.toml changes
#   dev     -> deps + dev tools, NO app code (Dev Container mounts the workspace)
#   runtime -> deps + app code (default target, last stage)

FROM python:3.12-slim AS deps
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/hoteldb
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -c "import tomllib; p=tomllib.load(open('pyproject.toml','rb'))['project']; print('\n'.join(p['dependencies']))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt

FROM deps AS dev
RUN --mount=type=cache,target=/root/.cache/pip \
    python -c "import tomllib; p=tomllib.load(open('pyproject.toml','rb'))['project']; print('\n'.join(p['optional-dependencies']['dev']))" > /tmp/requirements-dev.txt \
    && pip install -r /tmp/requirements-dev.txt

FROM deps AS runtime
RUN useradd -r -u 10001 hoteldb
COPY app ./app
USER hoteldb
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
