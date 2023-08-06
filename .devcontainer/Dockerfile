FROM registry.gitlab.com/ska-telescope/pst/ska-pst-common/ska-pst-common-builder:0.9.1 AS pstbuilder
FROM registry.gitlab.com/ska-telescope/pst/ska-pst-common/ska-pst-common-proto:0.9.1 as proto
FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.32 AS buildenv

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
    --python_out="$(pwd)/generated" \
    --init_python_out="$(pwd)/generated" \
    --init_python_opt=imports=protobuf+grpcio \
    --grpc_python_out="$(pwd)/generated" \
    $(find "$(pwd)/protobuf" -iname "*.proto")

USER tango
