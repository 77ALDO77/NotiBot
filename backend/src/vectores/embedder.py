import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from umap import UMAP

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_reducer: UMAP | None = None


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
    return np.array(embeddings, dtype=np.float64)


def reduce_to_3d(embeddings: np.ndarray) -> np.ndarray:
    global _reducer
    n_samples = embeddings.shape[0]
    if n_samples < 4:
        coords = np.zeros((n_samples, 3), dtype=np.float64)
        if n_samples > 0:
            coords[0, 0] = 0.5
        if n_samples > 1:
            coords[1, 1] = 0.5
        if n_samples > 2:
            coords[2, 2] = 0.5
        return coords

    logger.info(f"Running UMAP on {n_samples} samples...")
    if _reducer is None:
        _reducer = UMAP(
            n_components=3,
            n_neighbors=min(15, n_samples - 1),
            min_dist=0.15,
            metric="cosine",
            random_state=42,
            low_memory=False,
        )
    else:
        n_neighbors = min(15, n_samples - 1)
        if _reducer.n_neighbors != n_neighbors:
            _reducer = UMAP(
                n_components=3,
                n_neighbors=n_neighbors,
                min_dist=0.15,
                metric="cosine",
                random_state=42,
                low_memory=False,
            )

    coords = _reducer.fit_transform(embeddings)

    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    scales = maxs - mins
    scales[scales == 0] = 1.0
    coords = (coords - mins) / scales
    coords = coords * 2 - 1

    return coords.astype(np.float64)
