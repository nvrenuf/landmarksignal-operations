"""Read-only authenticated model check before installing the Jeeves policy.

Never invokes the provider resolver, starts a server, generates text or claims
a Kanban card. Credentials stay inside the loopback HTTP request.
"""

import json
import logging
import sqlite3
from urllib.parse import urlsplit
import urllib.error
import urllib.request

import yaml

from install_jeeves_policy import bootstrap


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def main():
    logging.disable(logging.CRITICAL)
    root, _, profile = bootstrap()
    cfg = yaml.safe_load((profile / "config.yaml").read_bytes())
    model = cfg.get("model", {})
    if model.get("default") != "Qwen3.5-9B-Q4_K_M" or model.get("provider") not in {"llamacpp", "local"}:
        raise RuntimeError("Jeeves model/provider differs from the reviewed local route")
    from hermes_cli.local_runtime.endpoint import _state_endpoint
    endpoint = _state_endpoint()
    if not endpoint:
        raise RuntimeError("No ownership-verified managed model endpoint; no restart attempted")
    route = urlsplit(endpoint.get("base_url", ""))
    if (route.scheme != "http" or route.hostname not in {"localhost", "127.0.0.1"}
            or route.port != 18434 or route.path.rstrip("/") != "/v1"
            or route.username or route.password or route.query or route.fragment):
        raise RuntimeError("Managed model route differs from expected loopback port 18434")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request("http://127.0.0.1:18434/v1/models", headers={
        "Authorization": "Bearer " + str(endpoint.get("api_key", "")),
        "Accept": "application/json",
    })
    try:
        with opener.open(request, timeout=8) as response:
            result = json.loads(response.read(262144))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Local model authentication/API failed: HTTP {exc.code}") from None
    except Exception as exc:
        raise RuntimeError("Local model API failed: " + type(exc).__name__) from None
    names = [item.get("id") for item in result.get("data", []) if isinstance(item, dict)]
    if model["default"] not in names:
        raise RuntimeError("Configured Jeeves model is absent from the authenticated model list")
    print("PASS: ownership-verified local model API authenticates; configured model is listed")
    board = root / "kanban/boards/landmarksignal/kanban.db"
    if not board.is_file():
        raise RuntimeError("Existing LandmarkSignal board is missing")
    with sqlite3.connect(board.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as conn:
        if conn.execute("SELECT COUNT(*) FROM tasks WHERE status='running'").fetchone()[0]:
            raise RuntimeError("LandmarkSignal has a running task; policy installation stopped")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        print("Board worker fingerprint column:", "present" if "worker_started_at" in columns else "MISSING - acceptance schema review required")
    print("PASS: existing LandmarkSignal board has no running task; no board writes performed")
    print("Agent generation and Issue #19 acceptance remain separate checks")


if __name__ == "__main__":
    main()
