"""Simple CLI client for the demo chatbot.

Run the FastAPI service (uvicorn) in another terminal, then execute:

    python examples/demo_chatbot/client.py

The script will maintain session state, display replies, and forward optional
traceparent headers to mimic how AgentEval campaigns call the target system.
"""

from __future__ import annotations

import argparse
import sys
import uuid

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CLI driver for the demo chatbot")
    parser.add_argument("--url", default="http://localhost:5057/chat", help="Chat endpoint URL")
    parser.add_argument("--persona", default=None, help="Optional persona hint to send")
    parser.add_argument("--trace", action="store_true", help="Forward generated traceparent headers")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session_id: str | None = None
    trace_id = uuid.uuid4().hex if args.trace else None

    print("Connected to", args.url)
    print("Type 'exit' to quit.\n")

    with httpx.Client(timeout=10.0) as client:
        while True:
            try:
                prompt = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0

            if not prompt:
                continue
            if prompt.lower() in {"exit", "quit"}:
                return 0

            payload = {"message": prompt}
            if session_id:
                payload["session_id"] = session_id
            if args.persona:
                payload["persona"] = args.persona

            headers = {}
            if trace_id:
                headers["traceparent"] = f"00-{trace_id}-0123456789abcdef-01"

            try:
                response = client.post(args.url, json=payload, headers=headers)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"error> {exc}")
                continue

            data = response.json()
            session_id = data.get("session_id", session_id)
            reply = data.get("reply", "<no reply>")
            latency = data.get("latency_ms", "?")
            trace = data.get("trace_id", "?")
            flags = data.get("flags", [])

            print(f"bot> {reply}")
            meta = f"latency={latency}ms trace={trace}"
            if flags:
                meta += f" flags={','.join(flags)}"
            print(f"    {meta}")


if __name__ == "__main__":
    sys.exit(main())
