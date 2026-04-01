from typing import Optional, List
from PIL import Image
from sentence_transformers import SentenceTransformer
import numpy as np

# Use a CLIP-like model from sentence-transformers
CLIP_MODEL = "clip-ViT-B-32"

class MultimodalEmbedder:
    def __init__(self, model_name: Optional[str] = None):
        self.model = SentenceTransformer(model_name or CLIP_MODEL)

    def embed_text(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True)

    def embed_image(self, image_path: str) -> np.ndarray:
        img = Image.open(image_path).convert('RGB')
        emb = self.model.encode([img], convert_to_numpy=True)
        return emb

    def image_and_text_similarity(self, image_path: str, texts: List[str]):
        img_emb = self.embed_image(image_path)
        txt_emb = self.embed_text(texts)
        # cosine similarity
        ni = img_emb / (np.linalg.norm(img_emb, axis=1, keepdims=True) + 1e-8)
        nt = txt_emb / (np.linalg.norm(txt_emb, axis=1, keepdims=True) + 1e-8)
        sims = (ni @ nt.T).squeeze(0)
        return sims.tolist()
