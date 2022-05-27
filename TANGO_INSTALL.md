TANGO INSTALL
=============

Development of TANGO devices need at least 9.3.3, these instructions are based
on the `ska-tango-images` Dockerfiles to set up a TANGO enviroment. The instructions
may not purely meet your development environment but following these instructions
should get you to the point of having TANGO 9.3.5.  All the commands below are to
be run as `root`

## Install 0MQ

```
mkdir /usr/src/zeromq
cd /usr/src/zeromq
curl -kfsSL "https://github.com/zeromq/libzmq/archive/v4.3.4.tar.gz" -o zeromq.tar.gz \
    && tar xf zeromq.tar.gz -C /usr/src/zeromq --strip-components=1 \
    && ./autogen.sh \
    && ./configure --enable-static=no \
    && make -C /usr/src/zeromq -j$(nproc) \
    && make -C /usr/src/zeromq install \
    && rm -r /usr/src/zeromq
```

```
mkdir /usr/src/cppzmq
cd /usr/src/cppzmq
curl -kfsSL "https://github.com/zeromq/cppzmq/archive/v4.8.1.tar.gz" -o cppzmq.tar.gz \
    && tar xf cppzmq.tar.gz -C /usr/src/cppzmq --strip-components=1 \
    && mkdir build \
    && cd build \
    && cmake -DCPPZMQ_BUILD_TESTS=OFF .. \
    && make -j4 install \
    && apt-get purge -y --auto-remove $buildDeps \
    && rm -r /usr/src/cppzmq
```

## Install OmniORB

```
mkdir /usr/src/omniorb
cd /usr/src/omniorb
curl -kfsSL "https://sourceforge.net/projects/omniorb/files/omniORB/omniORB-4.2.4/omniORB-4.2.4.tar.bz2/download" -o omniorb.tar.bz2 \
    && tar xf omniorb.tar.bz2 -C /usr/src/omniorb --strip-components=1 \
    && ./configure --enable-static=no \
    && make -C /usr/src/omniorb -j$(nproc) \
    && make -C /usr/src/omniorb install \
    && apt-get purge -y --auto-remove $buildDeps \
    && rm -r /usr/src/omniorb
```

## Install essentials tools for development
```
apt-get update && \
apt-get -y install --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        curl \
        file \
        git \
        libmariadbclient-dev \
        libmariadbclient-dev-compat \
        pkg-config python
```

## Install TANGO

```
mkdir -p /usr/src/idl
cd /usr/src/idl

git clone --depth 1 https://gitlab.com/tango-controls/tango-idl.git /usr/src/idl && \
    mkdir -p /usr/src/idl/build && \
    cmake -B /usr/src/idl/build -DCMAKE_INSTALL_PREFIX=/usr/local/ /usr/src/idl && \
    make  -j$(nproc) -C /usr/src/idl/build install
```

```
mkdir -p /usr/src/tango
cd /usr/src/tango

git clone https://gitlab.com/tango-controls/cppTango.git /usr/src/tango && \
    cd /usr/src/tango && git checkout 9.3.5 && \
    mkdir build && \
    cmake . -B build \
      -DBUILD_TESTING=OFF \
      -DCPPZMQ_BASE=/usr/local/ \
      -DIDL_BASE=/usr/local/ \
      -DOMNI_BASE=/usr/local/ \
      -DZMQ_BASE=/usr/local/ && \
    make -C /usr/src/tango/build -j$(nproc) && \
    make -C /usr/src/tango/build install && \
    ldconfig && \
    rm -r /usr/src/tango
```

```
git clone https://gitlab.com/tango-controls/tango_admin.git /usr/src/tango_admin && \
    cd /usr/src/tango_admin
    cmake -B /usr/src/tango_admin/build -DCMAKE_INSTALL_PREFIX=/usr/local/ /usr/src/tango_admin && \
    make  -j$(nproc) -C /usr/src/tango_admin/build install
```

```
apt-get update && \
    apt-get -y install --no-install-recommends \
        libmariadb3 

git clone --depth 1 https://gitlab.com/tango-controls/TangoDatabase.git /usr/src/TangoDatabase && \
    cd /usr/src/TangoDatabase
    cmake -B /usr/src/TangoDatabase/build -DCMAKE_INSTALL_PREFIX=/usr/local/ /usr/src/TangoDatabase && \
    make  -j$(nproc) -C /usr/src/TangoDatabase/build install
```
