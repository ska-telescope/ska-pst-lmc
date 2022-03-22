FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10 AS buildenv

RUN apt-get update && \
    apt-get install gnupg2 python3-venv -y && \
    python3 -m pip install poetry && \
    poetry config virtualenvs.create false && \
    cd /usr/bin && \
    ln -sf python3 python

COPY . /app/

RUN poetry config virtualenvs.create false && \
    poetry install

USER tango

RUN poetry config virtualenvs.create

ENTRYPOINT [ "poetry", "run", "Hello" ]
