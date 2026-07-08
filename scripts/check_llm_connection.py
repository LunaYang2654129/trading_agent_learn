"""Check whether the project is configured to use deepseek-v4-flash.

Default mode is offline and does not call the model:

    python scripts/check_llm_connection.py

Live mode sends a minimal request through the configured OpenAI-compatible
Volcengine Ark endpoint:

    python scripts/check_llm_connection.py --live
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from multiple_agent_finance.llm.base import get_base_llm, get_base_llm_metadata


EXPECTED_MODEL = "deepseek-v4-flash"


def _status(ok: bool) -> str:
    return "ok" if ok else "failed"


def check_config() -> dict[str, Any]:
    metadata = get_base_llm_metadata()
    model_ok = metadata.get("model") == EXPECTED_MODEL
    runtime_model_ok = bool(metadata.get("runtime_model"))
    key_ok = bool(metadata.get("api_key_configured"))
    base_url_ok = bool(metadata.get("base_url"))
    provider_ok = bool(metadata.get("provider"))

    return {
        "status": _status(model_ok and runtime_model_ok and key_ok and base_url_ok and provider_ok),
        "expected_model": EXPECTED_MODEL,
        "checks": {
            "provider_configured": provider_ok,
            "model_is_deepseek_v4_flash": model_ok,
            "runtime_model_configured": runtime_model_ok,
            "endpoint_id_configured": bool(metadata.get("endpoint_id_configured")),
            "base_url_configured": base_url_ok,
            "api_key_configured": key_ok,
        },
        "metadata": metadata,
    }


def check_live() -> dict[str, Any]:
    result = check_config()
    if result["status"] != "ok":
        result["live_check"] = {
            "status": "skipped",
            "reason": "Offline configuration check failed.",
        }
        return result

    try:
        llm = get_base_llm()
        response = llm.invoke(
            "Reply with exactly: deepseek-v4-flash connected",
        )
        content = str(getattr(response, "content", "")).strip()
        result["live_check"] = {
            "status": _status("deepseek-v4-flash connected" in content),
            "response_preview": content[:200],
        }
    except Exception as exc:
        error = str(exc)
        result["live_check"] = {
            "status": "failed",
            "error": error,
        }
        if "InvalidEndpointOrModel.NotFound" in error:
            result["live_check"]["diagnosis"] = (
                "Volcengine Ark rejected the runtime model value. The OpenAI-compatible "
                "API usually requires an Ark endpoint id in the model field, or the account "
                "does not have access to this model."
            )
            result["live_check"]["fix"] = (
                "Set MAF_LLM_ENDPOINT_ID to the endpoint id from the Ark console. "
                "Keep MAF_LLM_MODEL=deepseek-v4-flash as the intended model label."
            )
        result["status"] = "failed"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deepseek-v4-flash LLM configuration.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Send a minimal live request to the configured LLM endpoint.",
    )
    args = parser.parse_args()

    result = check_live() if args.live else check_config()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
