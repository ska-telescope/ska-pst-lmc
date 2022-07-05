ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder-alpine:9.3.30"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime-alpine:9.3.18"
FROM $BUILD_IMAGE AS buildenv

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN mkdir -p /app/tests && \
  poetry export --format requirements.txt --output requirements.txt --without-hashes && \
  poetry export --format requirements.txt --output tests/requirements.txt --without-hashes --dev

FROM $BASE_IMAGE

USER root

# Tar is needed for how the k8s-test runs
RUN apk --update add --no-cache tar

RUN poetry config virtualenvs.create false

WORKDIR /app

COPY --from=buildenv --chown=tango:tango /app/requirements.txt /app/
COPY --from=buildenv --chown=tango:tango /app/tests/requirements.txt /app/tests

RUN pip install -r requirements.txt && \
    rm pyproject.toml poetry.lock

USER tango

ENV PYTHONPATH=/app/src:/usr/local/lib/python3.9/site-packages
