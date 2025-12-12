import types
import sys


def pytest_configure(config):
    # Provide minimal stubs for telegram modules if not installed.
    if "telegram" not in sys.modules:
        telegram = types.ModuleType("telegram")
        telegram.Update = type("Update", (), {})  # minimal placeholder
        sys.modules["telegram"] = telegram

    if "telegram.ext" not in sys.modules:
        ext = types.ModuleType("telegram.ext")

        class _DummyChat:
            async def send_message(self, text: str):
                return None

        class _DummyApplication:
            def __init__(self):
                self.handlers = []

            def add_handler(self, handler):
                self.handlers.append(handler)

            async def initialize(self):
                return None

            async def start(self):
                return None

            class updater:
                @staticmethod
                async def start_polling():
                    return None

                @staticmethod
                async def stop():
                    return None

            async def stop(self):
                return None

            async def shutdown(self):
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
