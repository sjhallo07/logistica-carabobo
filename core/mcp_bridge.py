import httpx
from typing import Dict, Any

class RemoteMCPBridge:
    BASE_URL = "http://api.logistica-carabobo.io/mcp"

    ALLOWED_SEGMENTS = ["San Diego", "Lomas del Este", "Guacara", "La Entrada"]

    def get_traffic_arc(self, segment: str) -> Dict[str, Any]:
        if segment not in self.ALLOWED_SEGMENTS:
            raise ValueError(f"Segmento inválido: {segment}. Debe ser uno de: {', '.join(self.ALLOWED_SEGMENTS)}")
        resp = httpx.post(f"{self.BASE_URL}/get_traffic_arc", json={"segment": segment}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def verify_logistics_coupon(self, code: str) -> Dict[str, Any]:
        if not isinstance(code, str):
            raise ValueError("El código debe ser un string")
        resp = httpx.post(f"{self.BASE_URL}/verify_logistics_coupon", json={"code": code}, timeout=10)
        resp.raise_for_status()
        return resp.json()
