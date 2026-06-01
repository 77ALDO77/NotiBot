import logging
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers model...")
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("Model loaded.")
    return _model


def encode_texts(texts: list[str]) -> np.ndarray:
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    return np.array(embeddings, dtype=np.float32)


def reduce_to_3d(embeddings: np.ndarray) -> np.ndarray:
    t = torch.from_numpy(embeddings)

    mean = t.mean(dim=0, keepdim=True)
    t_centered = t - mean
    U, S, V = torch.pca_lowrank(t_centered, q=3)

    coords_3d = (t_centered @ V).numpy()

    sx, sy, sz = coords_3d.max(axis=0) - coords_3d.min(axis=0)
    scales = np.array([sx, sy, sz])
    scales[scales == 0] = 1.0
    coords_3d = (coords_3d - coords_3d.min(axis=0)) / (scales + 1e-8)
    coords_3d = coords_3d * 2 - 1

    return coords_3d.astype(np.float64)
