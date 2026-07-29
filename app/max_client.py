import ssl
from typing import Self

import certifi
import httpx


class MaxClient:
    def __init__(
        self,
        token: str,
        base_url: str,
        ca_cert_path: str,
        timeout: float = 15.0,
    ) -> None:
        if not token:
            raise ValueError("MAX_BOT_TOKEN is not configured")

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.load_verify_locations(cafile=ca_cert_path)

        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": token,
                "Content-Type": "application/json",
            },
            timeout=timeout,
            verify=ssl_context,
        )

    def send_message(
        self,
        text: str,
        *,
        chat_id: int | None = None,
        user_id: int | None = None,
        attachments: list[dict] | None = None,
    ) -> dict:
        if chat_id is None and user_id is None:
            raise ValueError("chat_id or user_id is required")

        params = {"chat_id": chat_id} if chat_id is not None else {"user_id": user_id}
        body: dict = {"text": text}
        if attachments:
            body["attachments"] = attachments

        response = self._client.post(
            "/messages",
            params=params,
            json=body,
        )
        response.raise_for_status()
        return response.json()

    def get_me(self) -> dict:
        response = self._client.get("/me")
        response.raise_for_status()
        return response.json()

    def send_action(self, chat_id: int, action: str) -> dict:
        response = self._client.post(
            f"/chats/{chat_id}/actions",
            json={"action": action},
        )
        response.raise_for_status()
        return response.json()

    def create_webhook(
        self,
        url: str,
        secret: str,
    ) -> dict:
        response = self._client.post(
            "/subscriptions",
            json={
                "url": url,
                "update_types": ["message_created", "bot_started"],
                "secret": secret,
            },
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
