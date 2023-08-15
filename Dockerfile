ARG BUILD_IMAGE=""
ARG BASE_IMAGE=""
ARG PST_COMMON_BUILDER_IMAGE=""
ARG PROTOBUF_IMAGE=""
ARG POETRY_VERSION="1.2.2"

FROM $PST_COMMON_BUILDER_IMAGE AS pstbuilder

FROM $PROTOBUF_IMAGE as proto

FROM $BUILD_IMAGE AS buildenv

ARG POETRY_VERSION

RUN apt update && \
  apt list --upgradable && \
  apt upgrade -y && \
  poetry self update ${POETRY_VERSION}

WORKDIR /app

COPY --from=proto /app/protobuf/ska/pst/lmc/ska_pst_lmc.proto /app/protobuf/ska_pst_lmc_proto/ska_pst_lmc.proto
COPY --from=pstbuilder /usr/local/lib/libprotobuf*.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libgrpc*.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libabsl*.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libaddress_sorting.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libcrypto.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libgpr.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libre2.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libssl.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libupb.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libz.so* ./lib/

COPY pyproject.toml poetry.lock* /app/
# This is needed to run tests
COPY src/ska_pst_lmc/ /app/src/ska_pst_lmc/
COPY tests/ /app/tests/
COPY resources/ska-pst-testutils/ /app/resources/ska-pst-testutils/

RUN mkdir -p /app/tests && \
  poetry config virtualenvs.create false && \
  poetry install --with dev

RUN mkdir -p "$(pwd)/generated" && \
    python3 -m grpc_tools.protoc --proto_path="$(pwd)/protobuf" \
    --python_out="$(pwd)/generated" \
    --init_python_out="$(pwd)/generated" \
    --init_python_opt=imports=protobuf+grpcio \
    --grpc_python_out="$(pwd)/generated" \
    $(find "$(pwd)/protobuf" -iname "*.proto")

RUN PYTHONPATH="/app/src:/app/generated" pytest --forked tests/

FROM $BASE_IMAGE

ARG POETRY_VERSION

USER root

RUN apt update && \
  apt list --upgradable && \
  apt upgrade -y && \
  poetry self update ${POETRY_VERSION}

COPY --from=pstbuilder /usr/local/lib/libprotobuf*.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libgrpc*.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libabsl*.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libaddress_sorting.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libcrypto.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libgpr.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libre2.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libssl.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libupb.so* ./lib/
COPY --from=pstbuilder /usr/local/lib/libz.so* ./lib/

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/
COPY --from=buildenv --chown=tango:tango /app/generated/ /app/src

RUN poetry config virtualenvs.create false && \
  poetry install --without dev --without docs

RUN mkdir -m777 -p /mnt/lfs

USER tango
