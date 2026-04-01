import os
import json
import math
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple

import httpx
from dotenv import load_dotenv

# Optional imports for STT/TTS — used only if available
try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    from gtts import gTTS
except Exception:
    gTTS = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Returns distance in kilometers between two lat/lon points
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


class Promotion:
    def __init__(self, id: str, title: str, description: str, latitude: Optional[float], longitude: Optional[float], country: Optional[str], is_public: bool, owner: Optional[str], expires_at: Optional[datetime]):
        self.id = id
        self.title = title
        self.description = description
        self.latitude = latitude
        self.longitude = longitude
        self.country = country
        self.is_public = is_public
        self.owner = owner
        self.expires_at = expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "country": self.country,
            "is_public": self.is_public,
            "owner": self.owner,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class ChatbotManager:
    """
    ChatbotManager handles promotions search, simple LLM integration, STT/TTS hooks, and timestamped queries.

    It is intentionally dependency-light and defensive: if optional audio libraries are not installed the
    voice pathways will raise informative errors so you can choose a provider (Vosk, Whisper, Google STT, etc.).
    """

    def __init__(self):
        # In a real app you'd load promotions from Supabase/pgvector + metadata table.
        self.promotions: List[Promotion] = []
        self._load_sample_promotions()

    def _load_sample_promotions(self):
        # Add a few sample promotions for demonstration
        now = datetime.now(timezone.utc)
        self.promotions = [
            Promotion("p1", "10% off Pizza", "10% off all pizzas today", 10.4806, -66.9036, "VE", True, None, now + timedelta(hours=6)),
            Promotion("p2", "Free Coffee", "Buy 1 get 1 free—limited time", 40.7128, -74.0060, "US", True, None, now + timedelta(days=2)),
            Promotion("p3", "50% Haircut", "Early-bird discount", None, None, None, True, None, now + timedelta(hours=1)),
        ]

    def add_promotion(self, promo: Promotion):
        self.promotions.append(promo)

    def find_promotions(self, query_text: str = "", gps: Optional[Tuple[float, float]] = None, radius_km: float = 50.0, country: Optional[str] = None, worldwide: bool = False, expiring_within_hours: Optional[float] = None, limit: int = 10) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        results: List[Tuple[Promotion, float]] = []
        for p in self.promotions:
            # expiry filter
            if p.expires_at and expiring_within_hours is not None:
                if (p.expires_at - now) > timedelta(hours=expiring_within_hours):
                    continue
            # country filter
            if country and p.country and p.country.lower() != country.lower():
                continue
            if (not worldwide) and gps and p.latitude is not None and p.longitude is not None:
                d = haversine_km(gps[0], gps[1], p.latitude, p.longitude)
                if d > radius_km:
                    continue
                score = d
            else:
                # fallback score: time to expiry in minutes (lower is more urgent)
                if p.expires_at:
                    ttl = max(0.0, (p.expires_at - now).total_seconds() / 60.0)
                else:
                    ttl = 1e9
                score = ttl
            # text matching (very basic): check if query terms in title/description
            if query_text:
                q = query_text.lower()
                text_blob = (p.title + " " + p.description).lower()
                if q not in text_blob:
                    continue
            results.append((p, score))
        # sort by score ascending
        results.sort(key=lambda x: x[1])
        out = [p.to_dict() for p, _ in results[:limit]]
        return out

    async def call_llm(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        """
        Minimal LLM call wrapper. Uses OPENAI_API_KEY if set. If no key available it returns
        a simple canned response so the rest of the flow can be tested offline.
        """
        if not OPENAI_API_KEY:
            # Fallback: simple template reply
            return ("(local fallback) I found some promotions matching your request. "
                    "Please run with an OpenAI API key to enable richer reasoning.")

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        # Compose a minimal chat completion payload; adapt to your LLM vendor
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that finds nearby promotions and coupons."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 512,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(OPENAI_API_URL, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            # This parsing assumes OpenAI-compatible response
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception:
                return json.dumps(data)

    def process_text_input(self, text: str, user_id: Optional[str] = None, gps: Optional[Tuple[float, float]] = None, country: Optional[str] = None, worldwide: bool = False, expiring_within_hours: Optional[float] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Process a text query synchronously. Returns a dict with promotions and a short assistant reply.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        matches = self.find_promotions(query_text=text, gps=gps, country=country, worldwide=worldwide, expiring_within_hours=expiring_within_hours, limit=limit)
        # Prepare a small prompt for LLM (non-blocking call left to the caller)
        prompt = f"User query (timestamp={timestamp}): {text}\nFound {len(matches)} matches: {json.dumps(matches)}\nRespond concisely with suggestions and actions the user can take."
        # For simplicity we will not await call_llm here (to keep sync API). Caller can call async LLM separately.
        return {
            "timestamp": timestamp,
            "matches": matches,
            "prompt_for_llm": prompt,
        }

    def process_voice_input(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Accept a path to an audio file (wav/mp3) and return the same structure as process_text_input.
        Requires `speech_recognition` to be installed and functional.
        """
        if sr is None:
            raise RuntimeError("SpeechRecognition is not installed. Install `SpeechRecognition` or provide a different STT backend.")
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
        except Exception as e:
            raise RuntimeError(f"STT failed: {e}")
        return self.process_text_input(text, **kwargs)

    def synthesize_text_to_speech(self, text: str, out_path: str = "response.mp3") -> str:
        """
        Synthesize text to an audio file. Tries gTTS first, then pyttsx3.
        Returns path to written file.
        """
        if gTTS is not None:
            tts = gTTS(text=text, lang="en")
            tts.save(out_path)
            return out_path
        if pyttsx3 is not None:
            engine = pyttsx3.init()
            engine.save_to_file(text, out_path)
            engine.runAndWait()
            return out_path
        raise RuntimeError("No TTS backend available. Install gTTS or pyttsx3.")


if __name__ == "__main__":
    # Quick manual test
    bot = ChatbotManager()
    res = bot.process_text_input("pizza near me expiring soon", gps=(10.4806, -66.9036), expiring_within_hours=12)
    print(json.dumps(res, indent=2))
