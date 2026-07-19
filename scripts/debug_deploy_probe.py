"""Probe Dev/Prod vs local to diagnose stale deploys. Writes NDJSON debug logs."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[1] / "debug-89dc87.log"
SESSION_ID = "89dc87"
PROD_API = "https://api-prod-prod.up.railway.app"
DEV_API = "https://api-production-6b9aa.up.railway.app"
NEW_FEATURE_PATHS = (
    "/auth/pdv-login",
    "/auth/pdv-authorize",
    "/users/{user_id}/pdv-pin",
    "/users/{user_id}/pdv-id/regenerate",
)


def log(hypothesis_id: str, location: str, message: str, data: dict, run_id: str = "pre-fix") -> None:
    # #region agent log
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    # #endregion


def fetch_openapi(base: str) -> dict:
    with urllib.request.urlopen(f"{base}/openapi.json", timeout=30) as resp:
        return json.load(resp)


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    import os

    run_id = os.environ.get("DEBUG_RUN_ID", "pre-fix")
    local_sha = git_sha()
    log(
        "A",
        "debug_deploy_probe.py:main",
        "local HEAD sha",
        {"localSha": local_sha, "expectedProdTrigger": "tag v*", "mainPushDeploys": "dev-only"},
        run_id=run_id,
    )

    for env_name, base, hyp in (("prod", PROD_API, "B"), ("dev", DEV_API, "C")):
        try:
            spec = fetch_openapi(base)
            paths = set(spec.get("paths", {}))
            present = {p: (p in paths) for p in NEW_FEATURE_PATHS}
            log(
                hyp,
                f"debug_deploy_probe.py:{env_name}",
                f"{env_name} openapi feature check",
                {
                    "base": base,
                    "pathCount": len(paths),
                    "newFeaturePathsPresent": present,
                    "allNewFeaturesPresent": all(present.values()),
                },
                run_id=run_id,
            )
        except Exception as exc:  # noqa: BLE001 — probe must always log
            log(
                hyp,
                f"debug_deploy_probe.py:{env_name}",
                f"{env_name} openapi fetch failed",
                {"base": base, "error": str(exc)},
                run_id=run_id,
            )

    log(
        "D",
        "debug_deploy_probe.py:vercel_note",
        "Vercel prod last known SHA from MCP (redeploy of old build)",
        {
            "vercelProdShaKnown": "9130d82f481efcdffe07dcbfee1de54a83257b57",
            "localSha": local_sha,
            "shaMatch": local_sha.startswith("9130d82"),
            "note": "Redeploy action reuses originalDeploymentId commit, does not pull latest main",
        },
        run_id=run_id,
    )
    print(f"Wrote probe logs to {LOG_PATH} runId={run_id}")


if __name__ == "__main__":
    main()
