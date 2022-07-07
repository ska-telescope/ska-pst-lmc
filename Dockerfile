ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder-alpine:9.3.30"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime-alpine:9.3.18"
ARG PROTOBUF_IMAGE="registry.gitlab.com/ska-telescope/pst/ska-pst-common/ska-pst-common-proto:0.1.0"

FROM $PROTOBUF_IMAGE as proto

FROM $BUILD_IMAGE AS buildenv

WORKDIR /app

COPY --from=proto /app/protobuf/ska/pst/lmc/ska_pst_lmc.proto /app/protobuf/ska_pst_lmc_proto/ska_pst_lmc.proto
RUN apk add --no-cache protobuf-dev grpc-dev && \
  mkdir -p /app/generated

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false

RUN mkdir -p /app/tests && \
  pip install --upgrade pip && \
  poetry export --format requirements.txt --output requirements.txt --without-hashes && \
  poetry export --format requirements.txt --output tests/requirements.txt --without-hashes --dev && \
  pip install -r tests/requirements.txt

RUN python3 -m grpc_tools.protoc --proto_path="$(pwd)/protobuf" \
    --python_out="$(pwd)/generated" \
    --init_python_out="$(pwd)/generated" \
    --init_python_opt=imports=protobuf+grpcio \
    --grpc_python_out="$(pwd)/generated" \
    $(find "$(pwd)/protobuf" -iname "*.proto")

FROM $BASE_IMAGE

USER root

# Tar is needed for how the k8s-test runs
RUN apk --update add --no-cache tar protobuf grpc

RUN poetry config virtualenvs.create false

WORKDIR /app

COPY --from=buildenv --chown=tango:tango /app/generated /app/generated
COPY --from=buildenv --chown=tango:tango /app/requirements.txt /app/
COPY --from=buildenv --chown=tango:tango /app/tests/requirements.txt /app/tests

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    rm pyproject.toml poetry.lock

USER tango

ENV PYTHONPATH=/app/src:/app/generated:/usr/local/lib/python3.9/site-packages
