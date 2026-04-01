import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
except Exception:  # optional at runtime
    webdriver = None
    ChromeOptions = None
    ChromeDriverManager = None
    ChromeService = None


VENEZUELA_DEFAULT = "VE"
MAX_RADIUS_MILES = 100.0
MAX_RADIUS_KM = 160.934

PROMOTION_KEYWORDS = [
    "comida", "restaurantes", "all you can eat", "massages", "cambio de aceite",
    "gasolina", "movistar", "digitel", "vehiculos", "motos", "repuestos", "bujias",
    "turbobujias", "cuidados", "centros medicos", "panaderias", "licor", "cerveza",
    "cigarro", "yummy", "ridery", "mrw", "tealca", "clinicas", "seguros", "instagram",
    "facebook", "farmacias", "farmatodo", "redvital", "hamburguesas", "perros",
    "ferreterias", "sambil", "valencia", "naguanagua", "prebo", "trigal", "centro",
    "av bolivar", "descuento", "promocion", "promoción", "cupon", "cupón", "coupon"
]

CODE_OR_NUMBER_RE = re.compile(r"(?:\b\d{1,3}%\b|\b[A-Z]{0,6}\d[A-Z\d]{2,}\b|\b\d+[\.,]?\d*\b)", re.IGNORECASE)


@dataclass
class RoutingDecision:
    should_call_mcp: bool
    matched_keywords: List[str]
    extracted_codes: List[str]
    country: str
    radius_miles: float
    title_hint: Optional[str]


class QueryRouter:
    def __init__(self, default_country: str = VENEZUELA_DEFAULT, max_radius_miles: float = MAX_RADIUS_MILES):
        self.default_country = default_country
        self.max_radius_miles = max_radius_miles

    def normalize_scope(self, country: Optional[str] = None, radius_miles: Optional[float] = None) -> Tuple[str, float]:
        final_country = (country or self.default_country).upper()
        final_radius = min(radius_miles or self.max_radius_miles, self.max_radius_miles)
        return final_country, final_radius

    def route_query(self, text: str, country: Optional[str] = None, radius_miles: Optional[float] = None) -> RoutingDecision:
        normalized = (text or "").lower()
        matched = [kw for kw in PROMOTION_KEYWORDS if kw in normalized]
        codes = [m.group(0) for m in CODE_OR_NUMBER_RE.finditer(text or "")]
        final_country, final_radius = self.normalize_scope(country, radius_miles)
        title_hint = matched[0].title() if matched else None
        should_call_mcp = bool(matched and codes)
        return RoutingDecision(
            should_call_mcp=should_call_mcp,
            matched_keywords=matched,
            extracted_codes=list(dict.fromkeys(codes)),
            country=final_country,
            radius_miles=final_radius,
            title_hint=title_hint,
        )

    def robots_allowed(self, url: str, user_agent: str = "*") -> bool:
        parsed = urlparse(url)
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        rp = RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(user_agent, url)
        except Exception:
            return False

    def fetch_safe_text(self, url: str, use_selenium: bool = False, timeout: float = 15.0) -> Dict[str, Any]:
        if not self.robots_allowed(url):
            return {"status": "blocked", "reason": "robots.txt disallows access", "url": url}

        if use_selenium and webdriver and ChromeOptions and ChromeDriverManager and ChromeService:
            options = ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            try:
                driver.get(url)
                html = driver.page_source
            finally:
                driver.quit()
        else:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; LogisticaBot/1.0)"}
            resp = httpx.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            html = resp.text

        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            text = " ".join(soup.stripped_strings)
        else:
            text = re.sub(r"<[^>]+>", " ", html)
        return {"status": "ok", "url": url, "text": text[:8000]}
