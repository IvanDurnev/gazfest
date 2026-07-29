import click
import httpx
from flask import Flask

from app.max_client import MaxClient


def register_commands(app: Flask) -> None:
    @app.cli.command("register-max-webhook")
    def register_max_webhook() -> None:
        """Register the public MAX webhook URL."""
        public_base_url = app.config["PUBLIC_BASE_URL"]
        secret = app.config["MAX_WEBHOOK_SECRET"]

        if not public_base_url:
            raise click.ClickException("PUBLIC_BASE_URL is not configured")
        if not secret:
            raise click.ClickException("MAX_WEBHOOK_SECRET is not configured")

        webhook_url = f"{public_base_url}{app.config['MAX_WEBHOOK_PATH']}"

        try:
            with MaxClient(
                token=app.config["MAX_BOT_TOKEN"],
                base_url=app.config["MAX_API_BASE_URL"],
                ca_cert_path=app.config["MAX_CA_CERT_PATH"],
            ) as client:
                result = client.create_webhook(webhook_url, secret)
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            details = error.response.text[:500]
            raise click.ClickException(
                f"MAX API returned HTTP {status}: {details}"
            ) from error
        except httpx.HTTPError as error:
            raise click.ClickException(
                f"Could not connect to MAX API: {error}"
            ) from error

        click.echo(f"Webhook registered: {webhook_url}")
        click.echo(result)
