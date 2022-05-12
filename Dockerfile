ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.3.28"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.3.16"
FROM $BUILD_IMAGE AS buildenv

FROM $BASE_IMAGE

# Install Poetry
USER root

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python - && \
    chmod a+x /opt/poetry/bin/poetry && \
    /opt/poetry/bin/poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
WORKDIR /app

COPY pyproject.toml poetry.lock* ./

# Install runtime dependencies and the app
RUN /opt/poetry/bin/poetry install --no-dev

USER tango

ENTRYPOINT [ "/bin/bash" ]
