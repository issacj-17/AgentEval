#!/usr/bin/env python3
"""
AgentEval Chatbot Demo
======================

Spin up the demo chatbot application and run the full AgentEval live-workflow
against it using real AWS Bedrock models (including the configured inference
profiles). This provides a richer end-to-end scenario than the default live
demo which targets Postman Echo.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import subprocess
import sys
from multiprocessing import Process
from pathlib import Path
from typing import Optional

import httpx


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agenteval.utils.live_demo_env import bootstrap_live_demo_env, refresh_settings
from agenteval.config import settings


def _run_chatbot_server(host: str, port: int, log_level: str = "warning") -> None:
    """Launch the demo chatbot (FastAPI + uvicorn) in a separate process."""
    import uvicorn

    uvicorn.run(
        "examples.demo_chatbot.app:create_app",
        host=host,
        port=port,
        log_level=log_level,
        access_log=False,
        lifespan="on",
    )


async def _wait_for_health(url: str, timeout: int) -> None:
    """Poll the chatbot health endpoint until it answers or timeout occurs."""
    deadline = asyncio.get_running_loop().time() + timeout
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(url, timeout=2.0)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass

            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Chatbot did not become ready within {timeout} seconds")
            await asyncio.sleep(0.5)


def _print_model_summary() -> None:
    """Log the model + inference profile configuration being used."""
    print("\nModel configuration:")
    print(f"  Persona model        : {settings.aws.bedrock_persona_model}")
    persona_profile = settings.aws.bedrock_persona_profile_arn or "(none configured)"
    print(f"  Persona profile ARN  : {persona_profile}")

    print(f"  Red-team model       : {settings.aws.bedrock_redteam_model}")
    red_profile = settings.aws.bedrock_redteam_profile_arn or "(none configured)"
    print(f"  Red-team profile ARN : {red_profile}")

    print(f"  Judge model          : {settings.aws.bedrock_judge_model}")
    judge_profile = settings.aws.bedrock_judge_profile_arn or "(none configured)"
    print(f"  Judge profile ARN    : {judge_profile}")


async def run_demo(args: argparse.Namespace) -> int:
    env_loaded = bootstrap_live_demo_env()
    if not env_loaded:
        print("❌ .env.live-demo not found. Run scripts/setup-live-demo.sh first.")
        return 1

    os.environ["AWS_REGION"] = args.region
    chatbot_url = f"http://{args.host}:{args.port}/chat"
    os.environ["DEMO_TARGET_URL"] = chatbot_url
    os.environ["DEMO_FALLBACK_TARGET_URL"] = chatbot_url

    refreshed_settings = refresh_settings()
    global settings
    settings = refreshed_settings

    from demo.agenteval_live_demo import LiveDemoRunner  # Local import to capture refreshed settings

    _print_model_summary()

    print(f"\nTarget application     : {chatbot_url}")
    print(f"Bedrock region         : {refreshed_settings.aws.region}")
    print(f"Environment            : {refreshed_settings.app.environment}")

    process: Optional[Process] = None
    started_locally = False

    try:
        if not args.use_existing_server:
            process = Process(
                target=_run_chatbot_server,
                args=(args.host, args.port, args.uvicorn_log_level),
                daemon=True,
            )
            process.start()
            started_locally = True
            print(f"\n⚙️  Starting demo chatbot on http://{args.host}:{args.port} ...")

        health_url = f"http://{args.host}:{args.port}/health"
        await _wait_for_health(health_url, timeout=args.startup_timeout)
        print("✅ Chatbot is ready.")

        runner = LiveDemoRunner(quick_mode=args.quick)
        success = await runner.run()

        if success and args.auto_teardown:
            print("\n🧹 Auto teardown enabled – invoking scripts/teardown-live-demo.sh ...")
            teardown_cmd = ["scripts/teardown-live-demo.sh", "--region", args.region]
            if args.force_teardown:
                teardown_cmd.append("--force")
            result = subprocess.run(teardown_cmd, cwd=REPO_ROOT, check=False)
            if result.returncode != 0:
                print("⚠️  Teardown script returned a non-zero exit code.")

        return 0 if success else 1

    finally:
        if process and started_locally:
            if process.is_alive():
                process.terminate()
                try:
                    process.join(timeout=5)
                except Exception:
                    pass
                if process.is_alive():
                    os.kill(process.pid, signal.SIGKILL)
            print("🛑 Chatbot process stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the AgentEval live demo against the local chatbot application."
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region for Bedrock + infrastructure")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for the chatbot server")
    parser.add_argument("--port", type=int, default=5057, help="Port for the chatbot server")
    parser.add_argument("--startup-timeout", type=int, default=30, help="Seconds to wait for chatbot health")
    parser.add_argument("--quick", action="store_true", help="Create campaigns without executing turns")
    parser.add_argument("--auto-teardown", action="store_true", help="Run teardown script after a successful demo")
    parser.add_argument("--force-teardown", action="store_true", help="Pass --force to the teardown script")
    parser.add_argument("--use-existing-server", action="store_true", help="Do not launch the chatbot; assume it is already running")
    parser.add_argument(
        "--uvicorn-log-level",
        default="warning",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level for the embedded uvicorn server",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        exit_code = asyncio.run(run_demo(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
