ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache \
    python3 \
    py3-pip \
    git \
    curl \
    ca-certificates

WORKDIR /opt/wotan-exchange

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install --no-cache-dir \
       "git+https://github.com/ShermanGu/exchange-ews-mcp.git"

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
