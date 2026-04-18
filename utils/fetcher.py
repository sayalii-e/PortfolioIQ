"""
utils/fetcher.py
================
Responsible for:
  - Calling an external API and returning parsed JSON
  - Diagnosing common failure modes and returning a user-friendly hint
  - Flattening nested JSON into a flat dict
  - Converting raw API responses into a pandas DataFrame
"""

import requests
import pandas as pd


# ── Hint lookup for common HTTP / network errors ───────────────────────────────

def _hint_for_error(err_str: str, status_code: int | None = None) -> str:
    """Return a short, actionable hint given a raw error message."""
    e = err_str.lower()
    if status_code == 401 or "401" in e or "unauthorized" in e:
        return "The API requires authentication. Add a valid auth header (e.g. API key or Bearer token)."
    if status_code == 403 or "403" in e or "forbidden" in e:
        return "Access denied. Check that your API key has the correct permissions or plan."
    if status_code == 404 or "404" in e or "not found" in e:
        return "Endpoint not found. Double-check the URL path and query parameters."
    if status_code == 429 or "429" in e or "rate limit" in e or "too many" in e:
        return "Rate limit hit. Wait a moment, reduce request frequency, or upgrade your API plan."
    if status_code and status_code >= 500:
        return "The remote server returned an error. Try again later or contact the API provider."
    if "timeout" in e:
        return "Request timed out (15 s limit). The server may be slow — try again or increase timeout."
    if "name or service not known" in e or "nodename nor servname" in e or "getaddrinfo" in e:
        return "DNS resolution failed. Check the URL hostname for typos."
    if "connection refused" in e:
        return "Connection refused. The server may be down or the port is wrong."
    if "ssl" in e or "certificate" in e:
        return "SSL/TLS error. The server certificate may be invalid or expired."
    if "json" in e or "decode" in e:
        return "Response is not valid JSON. The endpoint may return HTML (e.g. login redirect) instead of data."
    return "Verify the URL is reachable and returns JSON. Check network connectivity."


# ── HTTP fetch ─────────────────────────────────────────────────────────────────

def fetch_api(url: str, headers: dict | None = None) -> tuple[dict | list | None, str | None, str | None]:
    """
    GET *url* with optional extra *headers*.

    Returns:
        (parsed_json, None,      None)       on success
        (None,        error_msg, hint_msg)   on failure
    """
    base_headers = {"Accept": "application/json", "User-Agent": "FinDQE/1.0"}
    if headers:
        base_headers.update(headers)

    status_code = None
    try:
        resp = requests.get(url, headers=base_headers, timeout=15)
        status_code = resp.status_code
        resp.raise_for_status()

        # Make sure the body is actually JSON
        content_type = resp.headers.get("Content-Type", "")
        if "json" not in content_type and not resp.text.strip().startswith(("{", "[")):
            err = f"Non-JSON response (Content-Type: {content_type})"
            return None, err, _hint_for_error(err)

        return resp.json(), None, None

    except requests.exceptions.Timeout:
        err = "Request timed out after 15 s"
        return None, err, _hint_for_error(err)
    except requests.exceptions.HTTPError as exc:
        err = f"HTTP {exc.response.status_code} {exc.response.reason}"
        return None, err, _hint_for_error(err, exc.response.status_code)
    except requests.exceptions.ConnectionError as exc:
        err = str(exc)
        return None, err, _hint_for_error(err)
    except ValueError as exc:
        # JSON decode error
        err = f"JSON decode error: {exc}"
        return None, err, _hint_for_error(err)
    except Exception as exc:
        err = str(exc)
        return None, err, _hint_for_error(err, status_code)


# ── JSON flattening ────────────────────────────────────────────────────────────

def _flatten(obj, prefix: str = "") -> dict:
    """Recursively flatten nested JSON to dot-notation keys (max 50 list items)."""
    items: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                items.update(_flatten(v, key))
            else:
                items[key] = v
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            items.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        items[prefix] = obj
    return items


# ── DataFrame conversion ───────────────────────────────────────────────────────

def to_dataframe(data: dict | list) -> pd.DataFrame:
    """
    Best-effort conversion of raw API data to a tidy DataFrame.

    Strategy (in order):
      1. List of dicts  → json_normalize directly
      2. Dict containing a list-of-dicts value → use that nested list
      3. Any dict → flatten the whole thing into a single row
    """
    if isinstance(data, list):
        try:
            return pd.json_normalize(data)
        except Exception:
            return pd.DataFrame({"value": data})

    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                return pd.json_normalize(v)
        return pd.DataFrame([_flatten(data)])

    return pd.DataFrame()
