"""API client for Hertel Grillgenuss Standortsuche."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from .const import BASE_URL, DEFAULT_SEARCH_OPT

_LOGGER = logging.getLogger(__name__)

# Wochentag-Kürzel → Sortierschlüssel (Mo=0 … So=6)
WEEKDAY_ORDER: dict[str, int] = {
    "Mo": 0,
    "Di": 1,
    "Mi": 2,
    "Do": 3,
    "Fr": 4,
    "Sa": 5,
    "So": 6,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant/HertelGrillgenuss)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://hertel-grillgenuss.de",
    "Referer": "https://hertel-grillgenuss.de/standortsuche",
}


@dataclass
class HertelLocation:
    """Represents a single Hertel Grillgenuss Standort."""

    # Day info
    day: str = ""           # e.g. "Mi"
    day_full: str = ""      # e.g. "Mittwoch"
    day_order: int = 99     # 0=Mo … 6=So, 99=unknown

    # Distance from search point
    distance: str = ""      # e.g. "0,22 km"

    # Address
    zipcode: str = ""       # data-plz
    city: str = ""          # data-city
    hint: str = ""          # e.g. "REWE, Frauenrichter Straße 33"
    address: str = ""       # data-address from .hint element

    # Time
    time: str = ""          # e.g. "09:30 - 18:30 Uhr"

    # Coordinates
    latitude: float | None = None
    longitude: float | None = None

    # Extra
    shape_id: str = ""      # data-shapeid

    def as_dict(self) -> dict[str, Any]:
        """Return location as dict for HA state attributes."""
        return {
            "day": self.day,
            "day_full": self.day_full,
            "zipcode": self.zipcode,
            "city": self.city,
            "hint": self.hint,
            "address": self.address,
            "time": self.time,
            "distance": self.distance,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


# Full weekday name lookup
_DAY_FULL: dict[str, str] = {
    "Mo": "Montag",
    "Di": "Dienstag",
    "Mi": "Mittwoch",
    "Do": "Donnerstag",
    "Fr": "Freitag",
    "Sa": "Samstag",
    "So": "Sonntag",
}


class HertelGrillgenussApiClient:
    """POST to hertel-grillgenuss.de/standortsuche and parse .locationshape rows."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        latitude: float,
        longitude: float,
        zipcode: str | None = None,
    ) -> None:
        self._session = session
        self._latitude = latitude
        self._longitude = longitude
        self._zipcode = zipcode.strip() if zipcode else None

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    @property
    def _request_url(self) -> str:
        return (
            f"{BASE_URL}"
            f"?latitude={self._latitude}"
            f"&longitude={self._longitude}"
            f"&searchopt={DEFAULT_SEARCH_OPT}"
        )

    @property
    def _post_data(self) -> dict[str, str]:
        data: dict[str, str] = {
            "latitude": str(self._latitude),
            "longitude": str(self._longitude),
            "searchopt": DEFAULT_SEARCH_OPT,
        }
        if self._zipcode:
            data["zipcode"] = self._zipcode
        return data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def async_get_locations(self) -> list[HertelLocation]:
        """Fetch locations, parse, filter by PLZ, sort by weekday."""
        try:
            async with self._session.post(
                self._request_url,
                data=self._post_data,
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=True,
            ) as response:
                response.raise_for_status()
                html = await response.text()
        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error fetching Hertel locations: %s", err)
            raise

        _LOGGER.debug("Fetched %d bytes from %s", len(html), self._request_url)
        return self._parse_html(html)

    # ------------------------------------------------------------------
    # Parsing  –  targets <div class="row seperator locationshape" …>
    # ------------------------------------------------------------------

    def _parse_html(self, html: str) -> list[HertelLocation]:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("div.locationshape")

        if not rows:
            _LOGGER.warning(
                "No .locationshape elements found – the site may have changed its markup."
            )
            return []

        locations: list[HertelLocation] = []
        for row in rows:
            loc = self._parse_row(row)
            if loc is None:
                continue

            # PLZ filter (client-side, optional)
            if self._zipcode and loc.zipcode and loc.zipcode != self._zipcode:
                continue

            locations.append(loc)

        # Sort by weekday (Mo → So), then by distance as secondary key
        locations.sort(key=lambda l: (l.day_order, self._km_float(l.distance)))

        _LOGGER.debug(
            "Parsed %d locations (PLZ filter: %s)", len(locations), self._zipcode or "–"
        )
        return locations

    def _parse_row(self, row) -> HertelLocation | None:
        """Extract all fields from a single .locationshape row."""
        loc = HertelLocation()

        # ── Coordinates & meta from data attributes on the row itself ──
        loc.latitude  = self._safe_float(row.get("data-lat"))
        loc.longitude = self._safe_float(row.get("data-long"))
        loc.shape_id  = row.get("data-shapeid", "")
        loc.time      = row.get("data-time", "").strip()

        # ── Day  (.day element, also has data-days attribute) ──
        day_el = row.select_one(".day")
        if day_el:
            day_abbr = (day_el.get("data-days") or day_el.get_text(strip=True))[:2]
            loc.day       = day_abbr
            loc.day_full  = _DAY_FULL.get(day_abbr, day_abbr)
            loc.day_order = WEEKDAY_ORDER.get(day_abbr, 99)

        # ── Distance ──
        dist_el = row.select_one(".distance")
        if dist_el:
            loc.distance = dist_el.get_text(strip=True)

        # ── PLZ  (span.filterplz, data-plz attribute) ──
        plz_el = row.select_one(".filterplz")
        if plz_el:
            loc.zipcode = (plz_el.get("data-plz") or plz_el.get_text(strip=True)).strip()

        # ── City  (span.filtercity, data-city attribute) ──
        city_el = row.select_one(".filtercity")
        if city_el:
            loc.city = (city_el.get("data-city") or city_el.get_text(strip=True)).strip()

        # ── Hint (store name + address visible text) ──
        hint_el = row.select_one(".hint")
        if hint_el:
            loc.hint    = hint_el.get_text(strip=True)           # e.g. "REWE, Frauenrichter Straße 33"
            loc.address = (hint_el.get("data-address") or "").strip()  # street only

        # ── Time fallback from .startAndEndTime if not in data-time ──
        if not loc.time:
            time_el = row.select_one(".startAndEndTime")
            if time_el:
                loc.time = time_el.get_text(strip=True)

        # Require at least coordinates or a meaningful address
        if not (loc.latitude or loc.longitude or loc.hint):
            return None

        return loc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _km_float(distance_str: str) -> float:
        """Turn '0,22 km' → 0.22 for sorting."""
        try:
            return float(distance_str.replace(",", ".").split()[0])
        except (ValueError, IndexError):
            return 9999.0
