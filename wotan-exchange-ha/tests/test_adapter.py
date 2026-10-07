import json
import os
from pathlib import Path
import pytest
import keyring
from keyring.errors import KeyringError, PasswordDeleteError
from ha_keyring import HomeAssistantKeyring
from launcher import prepare


def test_adapter_config_and_upstream_client(tmp_path, monkeypatch):
    from exchange_ews_mcp import config, state_store
    # platformdirs follows native Windows paths here; emulate Linux XDG path
    # without ever writing to the existing Windows installation.
    monkeypatch.setattr(config, 'user_config_dir', lambda *a, **k: str(tmp_path/'config/exchange-ews-mcp'))
    monkeypatch.setattr(state_store, 'user_data_dir', lambda *a, **k: str(tmp_path/'state/exchange-ews-mcp'))
    options = dict(ews_url='https://mail.example.invalid/EWS/Exchange.asmx',
                   ews_username='TEST\\dummy', ews_password='dummy-test-only',
                   primary_email='dummy@example.invalid', company_domain='example.invalid',
                   timezone='Europe/Prague', mode='preflight', tunnel_id='', control_plane_api_key='')
    path=tmp_path/'options.json';path.write_text(json.dumps(options))
    prepare(path,tmp_path)
    from exchange_ews_mcp.credentials import get_password
    from exchange_ews_mcp.service import configured_client
    assert get_password(options['ews_username']) == 'dummy-test-only'
    assert keyring.get_password('other-service',options['ews_username']) is None
    assert keyring.get_password('exchange-ews-mcp','other-user') is None
    client=configured_client()
    assert client.session.verify is True
    cfg=config.load_config()
    assert cfg.calendar_workdays == [0,1,2,3,4]
    assert (cfg.calendar_workday_start,cfg.calendar_workday_end,cfg.calendar_slot_interval_minutes)==('07:00','17:00',30)
    assert 'dummy-test-only' not in config.config_path().read_text()
    options['ews_password']='rotated-dummy';path.write_text(json.dumps(options))
    assert get_password(options['ews_username']) == 'rotated-dummy'
    with pytest.raises(KeyringError):keyring.set_password('exchange-ews-mcp',options['ews_username'],'x')
    with pytest.raises(PasswordDeleteError):keyring.delete_password('exchange-ews-mcp',options['ews_username'])
    store=state_store.ReferenceStore()
    assert store.path.is_relative_to(tmp_path)


def test_backend_selected_by_environment(monkeypatch,tmp_path):
    monkeypatch.setenv('PYTHON_KEYRING_BACKEND','ha_keyring.HomeAssistantKeyring')
    keyring.core.init_backend()
    assert isinstance(keyring.get_keyring(),HomeAssistantKeyring)


def test_missing_options_does_not_leak(monkeypatch,tmp_path):
    monkeypatch.setenv('WOTAN_OPTIONS_PATH',str(tmp_path/'missing'))
    with pytest.raises(KeyringError,match='Cannot read local'):
        HomeAssistantKeyring().get_password('exchange-ews-mcp','dummy')


def test_launcher_failure_does_not_log_raw_secret(monkeypatch,capsys):
    import launcher
    def fail():raise ValueError('dummy-sensitive-test-value')
    monkeypatch.setattr(launcher,'prepare',fail)
    assert launcher.main()==1
    assert 'dummy-sensitive-test-value' not in capsys.readouterr().out


def test_tunnel_launch_arguments_do_not_contain_key(monkeypatch,capsys):
    import launcher
    from exchange_ews_mcp import service
    options=dict(mode='tunnel',control_plane_api_key='dummy-test-key',tunnel_id='tunnel_'+'0'*32)
    monkeypatch.setattr(launcher,'prepare',lambda:options)
    class Client:
        def test_connection(self):return 'dummy inbox'
    monkeypatch.setattr(service,'configured_client',lambda:Client())
    captured={}
    class Child:
        def poll(self):return 0
        def wait(self,**kw):return 0
    def spawn(args,**kw):captured.update(args=args,**kw);return Child()
    monkeypatch.setattr(launcher.subprocess,'Popen',spawn)
    monkeypatch.setattr(launcher.signal,'signal',lambda *a:None)
    assert launcher.main()==0
    assert '--mcp.command=exchange-ews-mcp serve' in captured['args']
    assert not any('dummy-test-key' in x for x in captured['args'])
    assert captured['env']['CONTROL_PLANE_API_KEY']=='dummy-test-key'
    assert 'dummy-test-key' not in capsys.readouterr().out
