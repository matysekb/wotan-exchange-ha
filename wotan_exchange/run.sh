#!/usr/bin/with-contenv bashio

set -e

EWS_URL="$(bashio::config 'ews_url')"
EWS_USERNAME="$(bashio::config 'ews_username')"
EWS_PASSWORD="$(bashio::config 'ews_password')"
COMPANY_DOMAIN="$(bashio::config 'company_domain')"
TIMEZONE="$(bashio::config 'timezone')"
TUNNEL_ID="$(bashio::config 'tunnel_id')"
CONTROL_PLANE_API_KEY="$(bashio::config 'control_plane_api_key')"

if [ -z "${EWS_PASSWORD}" ]; then
    bashio::log.fatal "Exchange password is not configured."
    exit 1
fi

if [ -z "${TUNNEL_ID}" ]; then
    bashio::log.fatal "OpenAI Tunnel ID is not configured."
    exit 1
fi

if [ -z "${CONTROL_PLANE_API_KEY}" ]; then
    bashio::log.fatal "OpenAI runtime API key is not configured."
    exit 1
fi

export TZ="${TIMEZONE}"
export CONTROL_PLANE_API_KEY

bashio::log.info "Starting Wotan Exchange MCP..."
bashio::log.info "EWS endpoint: ${EWS_URL}"
bashio::log.info "Exchange user: ${EWS_USERNAME}"
bashio::log.info "Company domain: ${COMPANY_DOMAIN}"

exec /opt/wotan-exchange/start-wotan.sh
