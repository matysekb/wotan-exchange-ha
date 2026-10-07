FROM python:3.13.16-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641
ARG BUILD_VERSION=0.2.0
ARG BUILD_ARCH=aarch64
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="app" io.hass.arch="${BUILD_ARCH}"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/wotan \
    PYTHON_KEYRING_BACKEND=ha_keyring.HomeAssistantKeyring \
    XDG_CONFIG_HOME=/data/config XDG_DATA_HOME=/data/state
WORKDIR /opt/wotan
COPY requirements.lock /opt/wotan/requirements.lock
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.lock
COPY vendor/exchange-ews-mcp /opt/upstream
RUN pip install --no-cache-dir --no-deps --no-build-isolation /opt/upstream
COPY fetch_tunnel.py /opt/wotan/fetch_tunnel.py
RUN python fetch_tunnel.py && tunnel-client --version
COPY ha_keyring.py launcher.py /opt/wotan/
COPY run.sh /run.sh
RUN chmod 755 /run.sh
ENTRYPOINT ["/run.sh"]
