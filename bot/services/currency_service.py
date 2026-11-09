import logging
import time
from typing import Optional
import urllib.request
import json

logger = logging.getLogger(__name__)

class CurrencyService:
    _cached_usd_rate: float = 12850.0  # Fallback default rate
    _last_update_ts: float = 0.0
    _CACHE_TTL: float = 14400.0  # 4 hours cache

    @classmethod
    def get_usd_rate(cls) -> float:
        """
        Returns official CBU (Центральный Банк Узбекистана) USD to UZS exchange rate.
        Uses in-memory cache to avoid unnecessary network requests.
        """
        now = time.time()
        if now - cls._last_update_ts < cls._CACHE_TTL:
            return cls._cached_usd_rate

        try:
            req = urllib.request.Request(
                "https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/",
                headers={"User-Agent": "PersonalFinanceBot/1.0"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if isinstance(data, list) and len(data) > 0:
                        rate_str = data[0].get("Rate")
                        if rate_str:
                            cls._cached_usd_rate = float(rate_str)
                            cls._last_update_ts = now
                            logger.info(f"CBU USD rate updated: 1 USD = {cls._cached_usd_rate} UZS")
        except Exception as e:
            logger.warning(f"Could not fetch fresh CBU rate, using cached {cls._cached_usd_rate}: {e}")

        return cls._cached_usd_rate

    @classmethod
    def to_usd_str(cls, amount_uzs: float) -> str:
        """Converts UZS to approximate USD string: e.g. '~$1 200'"""
        rate = cls.get_usd_rate()
        if rate <= 0:
            return ""
        usd_val = round(amount_uzs / rate)
        return f"~${usd_val:,.0f}".replace(",", " ")

