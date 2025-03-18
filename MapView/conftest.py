import pytest
from threading import Thread
from kivy.base import EventLoop
from main import MyApp

@pytest.fixture(scope="session", autouse=True)
def setup_kivy():
    EventLoop.ensure_window()
    yield
    EventLoop.close()

@pytest.fixture(scope="module")
def app():
    app = MyApp()
    thread = Thread(target=app.run)
    thread.start()
    yield app
    app.stop()
    thread.join()