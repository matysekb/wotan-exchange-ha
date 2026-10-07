"""Read-only keyring adapter; no password copies or desktop keyring needed."""
import json
import os
from pathlib import Path
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError


class HomeAssistantKeyring(KeyringBackend):
    priority = 1

    def get_password(self, service, username):
        if service != 'exchange-ews-mcp':
            return None
        try:
            options = json.loads(Path(os.environ.get('WOTAN_OPTIONS_PATH', '/data/options.json')).read_text(encoding='utf-8'))
            if username != options.get('ews_username'):
                return None
            password = options.get('ews_password')
            return password if isinstance(password, str) and password else None
        except (OSError, ValueError):
            raise KeyringError('Cannot read local Home Assistant options') from None

    def set_password(self, service, username, password):
        raise KeyringError('Configure credentials in Home Assistant')

    def delete_password(self, service, username):
        raise PasswordDeleteError('Manage credentials in Home Assistant')
