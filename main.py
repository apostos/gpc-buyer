import asyncio
import traceback
import signal
import sys

from pyrogram import Client

from app.core.banner import display_title, get_app_info, set_window_title
from app.core.callbacks import process_gift
from app.notifications import send_start_message
from app.utils.detector import gift_monitoring
from app.utils.logger import info, error
from data.config import config, t, get_language_display

app_info = get_app_info()


class Application:
    @staticmethod
    async def run() -> None:
        set_window_title(app_info)
        display_title(app_info, get_language_display(config.LANGUAGE))

        client = Client(
                name=config.SESSION,
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                phone_number=config.PHONE_NUMBER
        )

        shutdown_event = asyncio.Event()

        def signal_handler():
            if not shutdown_event.is_set():
                info("Shutdown signal received, stopping...")
                shutdown_event.set()

        loop = asyncio.get_running_loop()
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)

        monitoring_task = None
        try:
            await client.start()
            info("Client started.")
            await send_start_message(client)

            monitoring_task = asyncio.create_task(gift_monitoring(client, process_gift))

            await shutdown_event.wait()
        finally:
            if monitoring_task:
                monitoring_task.cancel()
                try:
                    await asyncio.wait_for(asyncio.gather(monitoring_task, return_exceptions=True), timeout=5.0)
                except asyncio.TimeoutError:
                    error("Monitoring task did not cancel within 5 seconds.")

            if client.is_connected:
                info("Stopping client...")
                try:
                    await asyncio.wait_for(client.stop(), timeout=5.0)
                    info("Client stopped.")
                except asyncio.TimeoutError:
                    error("Client did not stop within 5 seconds.")

    @staticmethod
    def main() -> None:
        try:
            asyncio.run(Application.run())
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception:
            error(t("console.unexpected_error"))
            traceback.print_exc()
        finally:
            info(t("console.terminated"))


Application.main() if __name__ == "__main__" else None
