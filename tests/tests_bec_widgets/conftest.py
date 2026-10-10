"""Qt + BEC fixtures for the widget tests in this folder (same wiring as bec_widgets core).

bec_widgets >= 3.38 ships them as ``bec_widgets.tests.fixtures``; the shared dev venv is on 3.37.3,
where only ``bec_widgets.tests.utils`` (fake devices, DMMock) is packaged and the fixtures live in
the core repo's own tests/unit_tests/conftest.py. The fallback below reproduces the ones these tests
need: mocked client on fakeredis, dispatcher / RPC-registry reset, leaked-widget and leaked-thread
checks. Left out of the fallback: the QTimer leak tracker, the widgets here own no timers.
TODO: delete the fallback once the venv runs bec_widgets >= 3.38; the star import then covers it.
"""

import os

# Keep ophyd on its dummy control layer so importing it never opens an EPICS CA context.
os.environ.setdefault("OPHYD_CONTROL_LAYER", "dummy")

try:
    from bec_widgets.tests.fixtures import *  # noqa: F401,F403
except ImportError:
    import threading
    from unittest import mock

    import fakeredis
    import pytest
    from bec_lib import service_config
    from bec_lib.client import BECClient
    from bec_qthemes import apply_theme
    from bec_qthemes._theme import Theme
    from bec_widgets.tests.utils import DEVICES, DMMock
    from bec_widgets.utils import bec_dispatcher as bec_dispatcher_module
    from bec_widgets.utils import error_popups
    from bec_widgets.utils.bec_dispatcher import QtRedisConnector
    from bec_widgets.utils.rpc_register import RPCRegister
    from ophyd._dummy_shim import _dispatcher as ophyd_dispatcher
    from pytestqt.exceptions import TimeoutError as QtBotTimeoutError
    from qtpy.QtCore import QEvent, QEventLoop, QRunnable, QThreadPool
    from qtpy.QtWidgets import QApplication, QMessageBox

    _FAILED = pytest.StashKey[bool]()

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(item, call):
        outcome = yield
        if call.when == "call":
            item.stash[_FAILED] = outcome.get_result().failed

    def _process_all_deferred_deletes(qapp):
        qapp.sendPostedEvents(None, QEvent.DeferredDelete)
        qapp.processEvents(QEventLoop.AllEvents)

    @pytest.fixture(autouse=True)
    def qapplication(qtbot, request):
        """Light theme before the test; afterwards every top-level widget must be gone."""
        qapp = QApplication.instance()
        _process_all_deferred_deletes(qapp)
        if not isinstance(getattr(qapp, "theme", None), Theme) or qapp.theme.theme != "light":
            apply_theme("light")
            qapp.processEvents()
        yield
        ophyd_dispatcher.stop()
        _process_all_deferred_deletes(qapp)
        if request.node.stash.get(_FAILED, False):
            return  # report the assertion, not the leak it caused
        qapp.processEvents()
        try:
            qtbot.waitUntil(lambda: qapp.topLevelWidgets() == [])
        except QtBotTimeoutError as exc:
            raise TimeoutError(f"Failed to close all widgets: {qapp.topLevelWidgets()}") from exc

    @pytest.fixture(autouse=True)
    def rpc_register():
        yield RPCRegister()
        RPCRegister.reset_singleton()

    _REDIS_CONN = None

    def _mock_qt_redis_connector(*_, **__):
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
                config=service_config.ServiceConfig(
                    config={"redis": {"host": "localhost", "port": 1}}
                ),
                connector_cls=_mock_qt_redis_connector,
            )
            client.start()
        client.device_manager.add_devices(DEVICES)
        return client

    @pytest.fixture(autouse=True)
    def bec_dispatcher(threads_check):  # threads_check: bec_lib's pytest plugin
        with mock.patch.object(bec_dispatcher_module, "BECClient", _mock_client):
            dispatcher = bec_dispatcher_module.BECDispatcher()
        yield dispatcher
        dispatcher.disconnect_all()
        dispatcher.client.shutdown()
        dispatcher.stop_cli_server()
        bec_dispatcher_module.BECDispatcher.reset_singleton()

    @pytest.fixture
    def mocked_client(bec_dispatcher):
        """Per-test BECClient on fakeredis with the fake devices from bec_widgets.tests.utils."""
        # A fresh session has no scan; the auto MagicMock would otherwise leak into widgets.
        bec_dispatcher.client.queue.scan_storage.current_scan = None
        yield bec_dispatcher.client
        bec_dispatcher.client.connector.shutdown()

    @pytest.fixture(autouse=True)
    def clean_singleton():
        error_popups._popup_utility_instance = None

    @pytest.fixture(autouse=True)
    def suppress_message_box(monkeypatch):
        monkeypatch.setattr(QMessageBox, "exec_", lambda *args, **kwargs: QMessageBox.Ok)

    @pytest.fixture(scope="session", autouse=True)
    def _register_worker_thread_dummies():
        """submit_task runs on the global QThreadPool; the first Python call inside such a thread
        registers a permanent threading._DummyThread that threads_check would report mid-test.
        Saturate the pool once, with expiry disabled, so every registration happens up front."""
        pool = QThreadPool.globalInstance()
        pool.setExpiryTimeout(-1)
        barrier = threading.Barrier(pool.maxThreadCount() + 1, timeout=10)

        class _Warmup(QRunnable):
            def run(self):
                threading.current_thread()
                try:
                    barrier.wait()
                except threading.BrokenBarrierError:
                    pass

        for _ in range(pool.maxThreadCount()):
            pool.start(_Warmup())
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
