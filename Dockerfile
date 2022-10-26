ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.3.32"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.3.19"
ARG PST_COMMON_BUILDER_IMAGE="registry.gitlab.com/ska-telescope/pst/ska-pst-common/ska-pst-common-builder:0.3.0"
ARG PROTOBUF_IMAGE="registry.gitlab.com/ska-telescope/pst/ska-pst-common/ska-pst-common-proto:0.3.0"

FROM $PST_COMMON_BUILDER_IMAGE AS pstbuilder

FROM $PROTOBUF_IMAGE as proto

FROM $BUILD_IMAGE AS buildenv

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

RUN mkdir -p /app/tests && \
  poetry config virtualenvs.create false && \
  poetry install --with dev

RUN mkdir -p "$(pwd)/generated" && \
    python3 -m grpc_tools.protoc --proto_path="$(pwd)/protobuf" \
    --python_out="$(pwd)/src" \
    --init_python_out="$(pwd)/src" \
    --init_python_opt=imports=protobuf+grpcio \
    --grpc_python_out="$(pwd)/src" \
    $(find "$(pwd)/protobuf" -iname "*.proto")

RUN pytest --forked tests/

FROM $BASE_IMAGE

USER root

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
COPY --from=buildenv --chown=tango:tango /app/src/ska_pst_lmc_proto/ /app/src/ska_pst_lmc_proto

RUN poetry config virtualenvs.create false && \
  poetry install --without dev && \
  rm pyproject.toml poetry.lock

USER tango
