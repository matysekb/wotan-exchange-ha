FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache \
    python3 \
    py3-pip \
    git \
    curl \
    ca-certificates \
    jq \
    unzip

WORKDIR /opt/wotan-exchange

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install --no-cache-dir \
       "git+https://github.com/ShermanGu/exchange-ews-mcp.git"

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
