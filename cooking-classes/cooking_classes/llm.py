"""Thin wrapper around the Anthropic SDK shared by the search and extract steps."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Server-side fallback: if a safety classifier declines a request, the API
# re-runs it on Anthropic's recommended fallback model in the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_BODY = {"fallbacks": "default"}


class RefusalError(RuntimeError):
    pass


def get_client():
    import anthropic  # imported lazily so the non-LLM parts run without the SDK

    return anthropic.Anthropic()


def check_refusal(response) -> None:
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        raise RefusalError(f"Claude declined the request: {details}")


def create_with_server_tools(client, *, max_turns: int = 5, **params):
    """messages.create that resumes `pause_turn` (long server-tool loops)."""
    messages = list(params.pop("messages"))
    for _ in range(max_turns):
        response = client.beta.messages.create(
            messages=messages,
            betas=[FALLBACK_BETA],
            extra_body=FALLBACK_BODY,
            **params,
        )
        check_refusal(response)
        if response.stop_reason != "pause_turn":
            return response
        log.debug("pause_turn; resuming")
        messages.append({"role": "assistant", "content": response.content})
    return response


def text_of(response) -> str:
    return "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
