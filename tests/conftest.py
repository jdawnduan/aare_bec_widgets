"""Minimal BEC client mock for widget tests.

Why: bec_widgets keeps its qtbot/mocked_client fixtures in its own tests/ tree (not in the package), so a
plugin repo cannot import them. This is the smallest subset: a BECDispatcher on a fakeredis connector with
the packaged fake devices. The core's widget/timer leak checks are left out until a widget here needs them.
"""

import os

os.environ.setdefault("OPHYD_CONTROL_LAYER", "dummy")  # keep ophyd off a real EPICS CA context

from unittest import mock

import fakeredis
import pytest
from bec_lib import service_config
from bec_lib.client import BECClient
from bec_widgets.tests.utils import DEVICES, DMMock
from bec_widgets.utils import bec_dispatcher as bec_dispatcher_module
from bec_widgets.utils.bec_dispatcher import QtRedisConnector
from bec_widgets.utils.rpc_register import RPCRegister

_REDIS_CONN: QtRedisConnector | None = None


def _fake_qt_redis_connector(*_, **__):
    global _REDIS_CONN
    if _REDIS_CONN is None:
        _REDIS_CONN = QtRedisConnector(bootstrap="localhost:1", redis_cls=fakeredis.FakeRedis)
    return _REDIS_CONN


def _mock_client(*_, **__):
    with (
        mock.patch("bec_lib.client.DeviceManagerBase", DMMock),
        mock.patch("bec_lib.client.DAPPlugins"),
        mock.patch("bec_lib.client.Scans"),
        mock.patch("bec_lib.client.ScanManager"),
        mock.patch("bec_lib.bec_service.BECAccess"),
    ):
        client = BECClient(
            config=service_config.ServiceConfig(config={"redis": {"host": "localhost", "port": 1}}),
            connector_cls=_fake_qt_redis_connector,
        )
        client.start()
    client.device_manager.add_devices(DEVICES)
    return client


@pytest.fixture(autouse=True)
def rpc_register():
    yield RPCRegister()
    RPCRegister.reset_singleton()


@pytest.fixture
def mocked_client(threads_check):  # threads_check: bec_lib pytest plugin
    with mock.patch.object(bec_dispatcher_module, "BECClient", _mock_client):
        dispatcher = bec_dispatcher_module.BECDispatcher()
    dispatcher.client.queue.scan_storage.current_scan = None
    yield dispatcher.client
    dispatcher.disconnect_all()
    dispatcher.client.shutdown()
    dispatcher.stop_cli_server()
    bec_dispatcher_module.BECDispatcher.reset_singleton()
