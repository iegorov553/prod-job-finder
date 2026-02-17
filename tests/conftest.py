import sys
import types
from importlib.util import find_spec


def pytest_configure(config):  # noqa: C901
    # Provide minimal stubs for telegram modules if not installed.
    if "telegram" not in sys.modules:
        telegram = types.ModuleType("telegram")
        telegram.Update = type("Update", (), {})  # minimal placeholder
        telegram.Chat = type("Chat", (), {})  # minimal placeholder
        telegram.LinkPreviewOptions = type(
            "LinkPreviewOptions",
            (),
            {"__init__": lambda self, is_disabled=False: None},
        )
        sys.modules["telegram"] = telegram

    if "telegram.ext" not in sys.modules:
        ext = types.ModuleType("telegram.ext")

        class _DummyChat:
            async def send_message(self, text: str):
                return None

        class _DummyApplication:
            def __init__(self):
                self.handlers = []
                self.running = False

            def add_handler(self, handler):
                self.handlers.append(handler)

            async def initialize(self):
                self.running = True
                return None

            async def start(self):
                self.running = True
                return None

            async def run_polling(self):
                self.running = True
                return None

            async def shutdown(self):
                self.running = False
                return None

        class _DummyBuilder:
            def token(self, token: str):
                return self

            def build(self):
                return _DummyApplication()

        ext.Application = _DummyApplication
        ext.ApplicationBuilder = lambda: _DummyBuilder()
        ext.CommandHandler = lambda *args, **kwargs: None
        ext.ContextTypes = types.SimpleNamespace(DEFAULT_TYPE=None)
        sys.modules["telegram.ext"] = ext

    if "apscheduler.schedulers.asyncio" not in sys.modules:
        sched_mod = types.ModuleType("apscheduler.schedulers.asyncio")

        class _DummyScheduler:
            def __init__(self, *args, **kwargs):
                self.jobs = {}
                self.running = False

            def start(self):
                self.running = True

            def shutdown(self, wait=False):
                self.running = False

            def add_job(self, func, trigger, id=None, replace_existing=True):
                self.jobs[id] = (func, trigger)

            def get_job(self, job_id):
                return self.jobs.get(job_id)

            def remove_job(self, job_id):
                self.jobs.pop(job_id, None)

        sched_mod.AsyncIOScheduler = _DummyScheduler
        sys.modules["apscheduler.schedulers.asyncio"] = sched_mod

    if "apscheduler.triggers.cron" not in sys.modules:
        cron_mod = types.ModuleType("apscheduler.triggers.cron")

        class CronTrigger:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        cron_mod.CronTrigger = CronTrigger
        sys.modules["apscheduler.triggers.cron"] = cron_mod

    if find_spec("fastapi") is None and "fastapi" not in sys.modules:
        fastapi = types.ModuleType("fastapi")

        class FastAPI:
            def __init__(self, *args, **kwargs):
                self.state = types.SimpleNamespace()
                self._routes = {}

            def include_router(self, router):
                self._routes.update(router._routes)

        class APIRouter:
            def __init__(self):
                self._routes = {}

            def post(self, path: str, status_code: int = 200, **kwargs):
                def _decorator(func):
                    self._routes[("POST", path)] = (func, status_code)
                    return func

                return _decorator

        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str | None = None):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class Request:
            def __init__(self):
                self.app = types.SimpleNamespace(state=types.SimpleNamespace())

        def Header(default=None):  # noqa: N802
            return default

        fastapi.FastAPI = FastAPI
        fastapi.APIRouter = APIRouter
        fastapi.HTTPException = HTTPException
        fastapi.Request = Request
        fastapi.Header = Header
        fastapi.status = types.SimpleNamespace(
            HTTP_202_ACCEPTED=202,
            HTTP_401_UNAUTHORIZED=401,
            HTTP_409_CONFLICT=409,
        )
        sys.modules["fastapi"] = fastapi

        testclient = types.ModuleType("fastapi.testclient")

        class _Response:
            def __init__(self, status_code: int, data: dict):
                self.status_code = status_code
                self._data = data

            def json(self) -> dict:
                return self._data

        class TestClient:
            __test__ = False

            def __init__(self, app):
                self.app = app

            def post(self, path: str, headers: dict | None = None):
                import asyncio
                import inspect

                route = self.app._routes.get(("POST", path))
                if route is None:
                    return _Response(404, {"detail": "Not Found"})
                handler, success_status = route
                request = Request()
                request.app = self.app
                kwargs = {}
                params = inspect.signature(handler).parameters
                if "request" in params:
                    kwargs["request"] = request
                if "authorization" in params:
                    kwargs["authorization"] = headers.get("Authorization") if headers else None
                try:
                    data = asyncio.run(handler(**kwargs))
                    return _Response(success_status, data)
                except HTTPException as exc:
                    return _Response(exc.status_code, {"detail": exc.detail})

        testclient.TestClient = TestClient
        sys.modules["fastapi.testclient"] = testclient

    if find_spec("uvicorn") is None and "uvicorn" not in sys.modules:
        uvicorn = types.ModuleType("uvicorn")

        class Config:
            def __init__(self, app, host: str, port: int, log_level: str = "info"):
                self.app = app
                self.host = host
                self.port = port
                self.log_level = log_level

        class Server:
            def __init__(self, config):
                self.config = config
                self.should_exit = False

            async def serve(self):
                return None

        uvicorn.Config = Config
        uvicorn.Server = Server
        sys.modules["uvicorn"] = uvicorn
