import os
import faiss
import numpy as np
import pickle
from typing import List, Tuple, Dict, Any, Optional
from sentence_transformers import SentenceTransformer

INDEX_DIR = os.getenv("VECTOR_INDEX_DIR", "./data/faiss")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

class FaissVectorStore:
    def __init__(self, dim: Optional[int] = None, model_name: str = None):
        self.model = SentenceTransformer(model_name or EMBED_MODEL)
        self.index = None
        self.id_to_meta: Dict[int, Dict[str, Any]] = {}
        self.dim = dim or self.model.get_sentence_embedding_dimension()
        self._ensure_index()

    def _ensure_index(self):
        if not os.path.exists(INDEX_DIR):
            os.makedirs(INDEX_DIR, exist_ok=True)
        index_path = os.path.join(INDEX_DIR, "index.faiss")
        meta_path = os.path.join(INDEX_DIR, "meta.pkl")
        if os.path.exists(index_path) and os.path.exists(meta_path):
            self.index = faiss.read_index(index_path)
            with open(meta_path, "rb") as f:
                self.id_to_meta = pickle.load(f)
        else:
            # use IndexFlatL2 for simplicity (replace with IVF for large corpora)
            self.index = faiss.IndexFlatL2(self.dim)
            self.id_to_meta = {}

    def save(self):
        index_path = os.path.join(INDEX_DIR, "index.faiss")
        meta_path = os.path.join(INDEX_DIR, "meta.pkl")
        faiss.write_index(self.index, index_path)
        with open(meta_path, "wb") as f:
            pickle.dump(self.id_to_meta, f)

    def embed(self, texts: List[str]) -> np.ndarray:
        embs = self.model.encode(texts, convert_to_numpy=True)
        return embs

    def add_documents(self, docs: List[Tuple[str, str, Dict[str, Any]]]):
        """
        docs: list of (doc_id, text, metadata)
        doc_id will be mapped to integer internal id.
        """
        texts = [d[1] for d in docs]
        embs = self.embed(texts)
        n_before = self.index.ntotal
        ids = []
        for i, (doc_id, _, meta) in enumerate(docs):
            internal_id = n_before + i
            self.id_to_meta[internal_id] = {"doc_id": doc_id, "meta": meta}
            ids.append(internal_id)
        self.index.add(embs.astype('float32'))
        self.save()
        return ids

    def search(self, query: str, top_k: int = 5):
        q_emb = self.embed([query]).astype('float32')
        D, I = self.index.search(q_emb, top_k)
        results = []
        for dist, idx in zip(D[0].tolist(), I[0].tolist()):
            if idx < 0:
                continue
            meta = self.id_to_meta.get(idx, {})
            results.append({"doc_id": meta.get("doc_id"), "meta": meta.get("meta"), "score": float(dist)})
        return results

    def reset(self):
        self.index = faiss.IndexFlatL2(self.dim)
        self.id_to_meta = {}
        self.save()
