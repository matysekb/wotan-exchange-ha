import os
import keyring.backend
from keyring.credentials import SimpleCredential


class HomeAssistantKeyring(keyring.backend.KeyringBackend):
    priority = 100

    def get_password(self, service, username):
        return os.environ.get("WOTAN_EWS_PASSWORD")

    def set_password(self, service, username, password):
        raise RuntimeError("Home Assistant keyring is read-only")

    def delete_password(self, service, username):
        raise RuntimeError("Home Assistant keyring is read-only")

    def get_credential(self, service, username):
        password = self.get_password(service, username)
        if password:
            return SimpleCredential(username, password)
        return None


keyring_backend = HomeAssistantKeyring()
