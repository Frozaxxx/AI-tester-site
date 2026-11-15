import json
from unittest.mock import patch

import pytest

from app.infra.telegram import TelegramNotifier


async def test_disabled_without_complete_config() -> None:
    with patch("app.infra.telegram.urlopen") as send:
        await TelegramNotifier("", "123").send("run-1", "completed")
        await TelegramNotifier("secret", "").send("run-1", "completed")
        send.assert_not_called()


async def test_payload_and_secret_not_logged(caplog) -> None:
    with patch("app.infra.telegram.urlopen") as send:
        send.return_value.__enter__.return_value.read.return_value = b'{"ok":true}'
        await TelegramNotifier("secret-token", "123").send("run-1", "completed")
        request = send.call_args.args[0]
        payload = json.loads(request.data)
        assert payload["chat_id"] == "123"
        assert "run-1" in payload["text"] and "completed" in payload["text"]
        assert "parse_mode" not in payload
        send.side_effect = RuntimeError("https://api.telegram.org/botsecret-token/sendMessage")
        await TelegramNotifier("secret-token", "123").send("run-1", "failed")
    assert "secret-token" not in caplog.text
    assert "notification failed" in caplog.text


@pytest.mark.parametrize("status", ["completed", "failed"])
async def test_api_rejection_is_nonfatal(status) -> None:
    with patch("app.infra.telegram.urlopen") as send:
        send.return_value.__enter__.return_value.read.return_value = b'{"ok":false}'
        await TelegramNotifier("secret", "123").send("run-1", status)
