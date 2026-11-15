import asyncio
import json
import logging
from urllib.request import Request, urlopen

logger = logging.getLogger("runner.telegram")


class TelegramNotifier:
    """Optional operator notifications; never exposes site contents or credentials."""

    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id

    async def send(self, run_id: str, status: str) -> None:
        if not self._token or not self._chat_id:
            return
        try:
            await asyncio.to_thread(self._send, run_id, status)
        except Exception:
            # HTTP exceptions may contain the bot token in their URL.
            logger.warning("Telegram notification failed for run %s", run_id)

    def _send(self, run_id: str, status: str) -> None:
        payload = json.dumps(
            {
                "chat_id": self._chat_id,
                "text": f"Scout: прогон {run_id}\nСтатус: {status}",
                "link_preview_options": {"is_disabled": True},
            }
        ).encode()
        request = Request(
            f"https://api.telegram.org/bot{self._token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=8) as response:
            if not json.load(response).get("ok"):
                raise RuntimeError("Telegram rejected notification")
