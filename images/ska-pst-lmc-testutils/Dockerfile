ARG RECV_IMAGE="registry.gitlab.com/ska-telescope/pst/ska-pst-recv/ska-pst-recv:0.4.1"
ARG LMC_IMAGE="registry.gitlab.com/ska-telescope/pst/ska-pst-lmc/ska-pst-lmc:0.2.2"

FROM $RECV_IMAGE as recv_env

FROM $LMC_IMAGE as lmc_env

USER root
# Copy udpgen and dependencies
COPY --from=recv_env /usr/local/bin/ska_pst_recv_udpgen /usr/local/bin
COPY --from=recv_env /usr/local/lib/libska_pst_recv.so  /usr/local/lib
COPY --from=recv_env /usr/local/lib/libska_pst_smrb.so  /usr/local/lib
COPY --from=recv_env /usr/local/lib/libska_pst_lmc.so   /usr/local/lib
COPY --from=recv_env /usr/local/lib/libpsrdada.so.1     /usr/local/lib

WORKDIR /usr/lib/x86_64-linux-gnu/
COPY --from=recv_env /usr/lib/x86_64-linux-gnu/libibverbs.so.1              /usr/lib/x86_64-linux-gnu/libibverbs.so.1
COPY --from=recv_env /usr/lib/x86_64-linux-gnu/librdmacm.so.1               /usr/lib/x86_64-linux-gnu/librdmacm.so.1
COPY --from=recv_env /usr/lib/x86_64-linux-gnu/libnl-route-3.so.200.26.0    /usr/lib/x86_64-linux-gnu/libnl-route-3.so.200.26.0
COPY --from=recv_env /usr/lib/x86_64-linux-gnu/libnl-route-3.so.200         /usr/lib/x86_64-linux-gnu/libnl-route-3.so.200
COPY --from=recv_env /usr/lib/x86_64-linux-gnu/libnl-3.so.200               /usr/lib/x86_64-linux-gnu/libnl-3.so.200

ENV LD_LIBRARY_PATH=/app/lib/
WORKDIR /app

# Copy ska-pst-lmc test scripts
