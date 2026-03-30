import pytest
from core.mcp_bridge import RemoteMCPBridge

bridge = RemoteMCPBridge()

@pytest.mark.parametrize("text,expected", [
    ("Usa el código FIRST2026 para 20%", ["FIRST2026"]),
    ("Promo: PROMO10 desc", ["PROMO10"]),
    ("No coupons here", []),
    ("Multiple codes ABC12 and XYZ99 in caption", ["ABC12", "XYZ99"]),
    ("Mention code: abc123", ["ABC123"]),
])
def test_extract_coupons(text, expected):
    res = bridge._extract_coupons_from_text(text)
    assert res == expected
