"""Payslip and attendance messages over SMS and WhatsApp. Pure Python; delivery is behind adapters.

Adapters are disabled until the company enters provider settings. No key is stored in code. With no
provider configured, every send reports "skipped" so nothing is lost silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Message:
    to: str
    body: str
    channel: str = "sms"  # sms or whatsapp


@dataclass
class SendResult:
    sent: int = 0
    skipped: int = 0
    failed: list = field(default_factory=list)


def payslip_text(employee_name: str, month: str, net_pay: str) -> str:
    """Bilingual short payslip notice (English and Bangla)."""
    return (f"Dear {employee_name}, your salary for {month} is ready. Net pay: {net_pay}. "
            f"প্রিয় {employee_name}, {month} মাসের বেতন প্রস্তুত। নিট বেতন: {net_pay}।")


class Adapter:
    """Base adapter. Subclasses call their provider; the base class never sends."""

    name = "none"

    def configured(self) -> bool:
        return False

    def send(self, message: Message) -> bool:  # pragma: no cover - provider specific
        raise NotImplementedError


class WebhookAdapter(Adapter):
    """Generic HTTP provider: POST JSON {to, body, channel} to a URL with a bearer token from settings."""

    name = "webhook"

    def __init__(self, url: str | None, token: str | None, http_post=None):
        self.url = url
        self.token = token
        self._post = http_post

    def configured(self) -> bool:
        return bool(self.url and self.token and self._post)

    def send(self, message: Message) -> bool:
        if not self.configured():
            return False
        response = self._post(self.url, {"to": message.to, "body": message.body, "channel": message.channel},
                              {"Authorization": f"Bearer {self.token}"})
        return 200 <= int(response) < 300


def dispatch(messages: list[Message], adapter: Adapter) -> SendResult:
    result = SendResult()
    if not adapter.configured():
        result.skipped = len(messages)
        return result
    for m in messages:
        try:
            if adapter.send(m):
                result.sent += 1
            else:
                result.failed.append(m.to)
        except Exception:
            result.failed.append(m.to)
    return result
