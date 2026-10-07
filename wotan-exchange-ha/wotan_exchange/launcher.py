"""HA options to upstream config, EWS preflight, then official stdio tunnel."""
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def prepare(options_path=Path('/data/options.json'), data_dir=Path('/data')):
    os.umask(0o077)
    options = json.loads(options_path.read_text(encoding='utf-8'))
    for field in ('ews_url', 'ews_username', 'ews_password', 'primary_email', 'company_domain', 'timezone'):
        if not isinstance(options.get(field), str) or not options[field].strip():
            raise ValueError('Missing required configuration')
    mode = options.get('mode', 'preflight')
    if mode not in ('preflight', 'tunnel'):
        raise ValueError('Invalid mode')
    if mode == 'tunnel':
        if not isinstance(options.get('control_plane_api_key'), str) or not options['control_plane_api_key'].strip():
            raise ValueError('Missing runtime API key')
        if not re.fullmatch(r'tunnel_[0-9a-f]{32}', options.get('tunnel_id', '')):
            raise ValueError('Invalid tunnel ID')
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        WOTAN_OPTIONS_PATH=str(options_path.resolve()),
        XDG_CONFIG_HOME=str((data_dir / 'config').resolve()),
        XDG_DATA_HOME=str((data_dir / 'state').resolve()),
        PYTHON_KEYRING_BACKEND='ha_keyring.HomeAssistantKeyring',
        TZ=options['timezone'],
    )
    import keyring
    from ha_keyring import HomeAssistantKeyring
    from exchange_ews_mcp.config import AppConfig, save_config
    keyring.set_keyring(HomeAssistantKeyring())
    save_config(AppConfig(
        ews_url=options['ews_url'], username=options['ews_username'],
        verify_tls=True, primary_email=options['primary_email'],
        company_email_domains=[options['company_domain']],
        calendar_time_zone=options['timezone'],
        calendar_workday_start='07:00', calendar_workday_end='17:00',
        calendar_workdays=[0, 1, 2, 3, 4], calendar_slot_interval_minutes=30,
        attachment_roots=[str((data_dir / 'attachments').resolve())],
    ))
    (data_dir / 'attachments').mkdir(exist_ok=True)
    return options


def main():
    try:
        options = prepare()
        from exchange_ews_mcp.service import configured_client
        # Read-only EWS test; never log server responses or raw exceptions.
        configured_client().test_connection()
    except Exception:
        print('Configuration or EWS preflight failed. Check local options, DNS, HTTPS trust and EWS access.', flush=True)
        return 1
    print('EWS preflight OK (TLS verification enabled).', flush=True)
    if options.get('mode', 'preflight') == 'preflight':
        print('Preflight mode: tunnel is disabled. Stop this app before changing mode.', flush=True)
        while True:
            time.sleep(60)
    env = os.environ.copy()
    env['CONTROL_PLANE_API_KEY'] = options['control_plane_api_key']
    env['CONTROL_PLANE_TUNNEL_ID'] = options['tunnel_id']
    # Keep runtime configuration explicit and isolated from user profiles.
    args = ['/usr/local/bin/tunnel-client', 'run',
            '--mcp.command=exchange-ews-mcp serve',
            '--health.listen-addr=127.0.0.1:8080',
            '--mcp.max-concurrent-requests=1']
    print('Starting official tunnel client; one active runtime per Tunnel ID.', flush=True)
    # Avoid raw upstream/tunnel stderr reaching HA logs (can contain EWS data).
    # Only lifecycle messages and locally tested EWS status are emitted.
    child = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def stop(signum, frame):
        child.terminate()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    ready = None
    while child.poll() is None:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=2) as response:
                current = response.status == 200
        except Exception:
            current = False
        if current != ready:
            print('Tunnel ready.' if current else 'Tunnel not ready; check runtime key, tunnel access and outbound HTTPS.', flush=True)
            ready = current
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    status = child.wait()
    print('Tunnel runtime stopped (exit status %d).' % status, flush=True)
    return status


if __name__ == '__main__':
    sys.exit(main())
