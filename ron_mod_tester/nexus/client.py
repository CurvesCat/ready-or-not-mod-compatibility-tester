"""Thin, read-only Nexus Mods REST v1 client with polite rate limiting.

Only metadata endpoints are used. Nothing is ever uploaded to Nexus other than
the small file fingerprint (MD5) required by the lookup, plus the user's own
Personal API key in the request header.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from .. import VERSION

GAME_DOMAIN = "readyornot"
GAME_ID = 4205
BASE_URL = "https://api.nexusmods.com/v1"
REQUEST_TIMEOUT = 25
DEFAULT_MIN_INTERVAL = 1.1
USER_AGENT = f"RoNCT/{VERSION} (Ready or Not mod compatibility tester)"
GRAPHQL_URL = "https://api.nexusmods.com/v2/graphql"


class NexusError(Exception):
    """Base class for Nexus API failures."""


class NexusAuthError(NexusError):
    """The API key is missing, invalid, or lacks permission."""


class NexusRateLimitError(NexusError):
    """Nexus is telling us to slow down."""


class NexusNetworkError(NexusError):
    """Could not reach the Nexus API (offline / DNS / TLS / timeout)."""


class NexusClient:
    """Minimal client for the endpoints RoNCT currently needs."""

    def __init__(
        self,
        api_key: str,
        game_domain: str = GAME_DOMAIN,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.game_domain = game_domain
        self.min_interval = min_interval
        self.timeout = timeout
        self._last_request_at = 0.0

    # ------------------------------------------------------------- API
    def validate(self) -> dict[str, Any]:
        return self._get("/users/validate.json")

    def search_md5(self, md5: str) -> list[dict[str, Any]]:
        return self._get(
            f"/games/{self.game_domain}/mods/md5_search/{md5.lower()}.json",
            not_found_ok=True,
        )

    def search_mods(self, term: str, limit: int = 8) -> list[dict[str, Any]]:
        """Fuzzy name search over a single game via the Nexus GraphQL API."""
        query = """
        query RoNCTSearch($game: String!, $term: String!, $count: Int!) {
          mods(
            filter: {
              gameDomainName: [{ value: $game, op: EQUALS }]
              nameStemmed: [{ value: $term, op: MATCHES }]
            }
            count: $count
          ) {
            nodes {
              modId
              name
              author
              game { domainName }
            }
          }
        }
        """
        body = {
            "query": query,
            "variables": {
                "game": self.game_domain,
                "term": term,
                "count": int(limit),
            },
        }
        data = self._post_graphql(body)
        nodes = ((data or {}).get("data") or {}).get("mods") or {}
        nodes = nodes.get("nodes") if isinstance(nodes, dict) else []
        out: list[dict[str, Any]] = []
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            mod_id = node.get("modId")
            try:
                mod_id = int(mod_id) if mod_id not in (None, "") else None
            except (TypeError, ValueError):
                mod_id = None
            if mod_id is None:
                continue
            out.append(
                {
                    "mod_id": mod_id,
                    "mod_name": str(node.get("name") or ""),
                    "author": str(node.get("author") or ""),
                    "mod_url": (
                        f"https://www.nexusmods.com/{self.game_domain}/mods/{mod_id}"
                    ),
                }
            )
        return out

    def mod_requirements(self, mod_id: int | str) -> dict[str, Any]:
        """Return DLC + Nexus-mod requirements for one Ready or Not mod."""
        query = """
        query RoNCTRequirements($gameId: ID!, $modId: ID!) {
          mod(gameId: $gameId, modId: $modId) {
            modId
            name
            modRequirements {
              dlcRequirements {
                notes
                gameExpansion { name }
              }
              nexusRequirements {
                nodes {
                  modId
                  modName
                  externalRequirement
                  notes
                  url
                }
              }
            }
          }
        }
        """
        body = {
            "query": query,
            "variables": {
                "gameId": int(GAME_ID),
                "modId": int(mod_id),
            },
        }
        data = self._post_graphql(body)
        mod = ((data or {}).get("data") or {}).get("mod") or {}
        req = mod.get("modRequirements") or {}
        dlc = []
        for item in req.get("dlcRequirements") or []:
            if not isinstance(item, dict):
                continue
            expansion = item.get("gameExpansion") or {}
            dlc.append(
                {
                    "name": expansion.get("name") or "",
                    "notes": item.get("notes") or "",
                }
            )
        nexus = []
        page = req.get("nexusRequirements") or {}
        for item in page.get("nodes") or []:
            if not isinstance(item, dict):
                continue
            try:
                req_mod_id = int(item.get("modId") or 0)
            except (TypeError, ValueError):
                req_mod_id = 0
            url = str(item.get("url") or "")
            if not url and req_mod_id > 0:
                url = (
                    f"https://www.nexusmods.com/{self.game_domain}/mods/{req_mod_id}"
                )
            nexus.append(
                {
                    "mod_id": req_mod_id,
                    "mod_name": item.get("modName") or "",
                    "external": bool(item.get("externalRequirement")),
                    "notes": item.get("notes") or "",
                    "url": url,
                }
            )
        return {
            "mod_id": int(mod_id),
            "mod_name": mod.get("name") or "",
            "dlc": dlc,
            "nexus": nexus,
        }

    def mod_info(self, mod_id: int | str) -> dict[str, Any]:
        return self._get(f"/games/{self.game_domain}/mods/{mod_id}.json")

    # ------------------------------------------------------------- request
    def _get(self, path: str, not_found_ok: bool = False) -> Any:
        if not self.api_key:
            raise NexusAuthError("No Nexus API key configured.")
        headers = {
            "apikey": self.api_key,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        return self._request_with_retry(
            urllib.request.Request(BASE_URL + path, headers=headers),
            not_found_ok=not_found_ok,
        )

    def _post_graphql(self, body: dict[str, Any]) -> Any:
        if not self.api_key:
            raise NexusAuthError("No Nexus API key configured.")
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Origin": "https://www.nexusmods.com",
            "Referer": "https://www.nexusmods.com/",
        }
        request = urllib.request.Request(
            GRAPHQL_URL,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        return self._request_with_retry(request, not_found_ok=False)

    def _request_with_retry(
        self,
        request: urllib.request.Request,
        not_found_ok: bool = False,
    ) -> Any:
        attempts = 0
        while True:
            attempts += 1
            self._throttle()
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                return json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    raise NexusAuthError(
                        f"Nexus rejected the API key (HTTP {exc.code})."
                    ) from exc
                if exc.code == 404 and not_found_ok:
                    return []
                if exc.code == 429:
                    retry_after = self._retry_after_seconds(exc)
                    if attempts < 4 and retry_after <= 60:
                        time.sleep(retry_after)
                        continue
                    raise NexusRateLimitError(
                        "Nexus rate limit reached; try again in a minute."
                    ) from exc
                raise NexusError(f"Nexus API error (HTTP {exc.code}).") from exc
            except urllib.error.URLError as exc:
                raise NexusNetworkError(str(exc.reason or exc)) from exc
            except TimeoutError as exc:
                raise NexusNetworkError("Nexus request timed out.") from exc
            except OSError as exc:
                raise NexusNetworkError(str(exc)) from exc

    def _throttle(self) -> None:
        wait = self._last_request_at + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _retry_after_seconds(exc: urllib.error.HTTPError) -> float:
        value = exc.headers.get("Retry-After") if exc.headers else None
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 2.0
