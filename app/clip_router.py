"""
CLIP-based component router.

Strategy: CLIP handles visual grounding (what does this look like?),
LLM handles reasoning (what does this mean for inspection?).

When to use CLIP routing over VisionLLM routing:
- You have labeled reference images per component type
- Latency is critical (CLIP is ~10x faster than a vision LLM call)
- You want deterministic, reproducible routing (no LLM variance)

Limitation: CLIP struggles with industrial components that look visually
similar (hydraulic hose vs cooling hose). Use VisionLLM routing unless
you have a solid labeled reference image set.
"""
import base64
import io
import os
from typing import Optional

from PIL import Image

from .prompts import COMPONENT_TYPES

# Reference images directory: Pass/Fail images tagged by component type.
# Structure: references/<component_type>/<image>.jpg
REFERENCES_DIR = os.path.join(os.path.dirname(__file__), "..", "references")

# Lazy-loaded model + processor
_model = None
_processor = None
_embeddings: dict[str, list] = {}  # component_type -> list of embedding vectors


def _load_clip():
    global _model, _processor
    if _model is not None:
        return

    try:
        from transformers import CLIPModel, CLIPProcessor
        import torch

        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _model.eval()
    except ImportError:
        raise ImportError(
            "CLIP routing requires: pip install transformers torch Pillow\n"
            "Or switch to VisionLLM routing (default)."
        )


def _embed_image(image_bytes: bytes) -> "torch.Tensor":
    _load_clip()
    import torch
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    inputs = _processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = _model.get_image_features(**inputs)
    return features / features.norm(dim=-1, keepdim=True)


def build_reference_index() -> None:
    """
    Pre-compute CLIP embeddings for all reference images.
    Call once at startup if using CLIP routing.

    Reference images are loaded from:
      references/<component_type>/<any>.jpg
    """
    if not os.path.isdir(REFERENCES_DIR):
        return

    _load_clip()
    import torch
    for component_type in COMPONENT_TYPES:
        comp_dir = os.path.join(REFERENCES_DIR, component_type)
        if not os.path.isdir(comp_dir):
            continue

        vecs = []
        for fname in os.listdir(comp_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            path = os.path.join(comp_dir, fname)
            with open(path, "rb") as f:
                try:
                    vec = _embed_image(f.read())
                    vecs.append(vec)
                except Exception:
                    continue

        if vecs:
            _embeddings[component_type] = torch.cat(vecs, dim=0)


def classify_with_clip(image_bytes: bytes) -> tuple[str, float, str]:
    """
    Classify component type using CLIP visual similarity.

    Returns (component_type, confidence, description).
    Falls back to 'unknown' if no reference embeddings are loaded.

    CLIP provides grounding — it finds the visually closest reference.
    The downstream VisionLLM then handles all reasoning about the image.
    """
    if not _embeddings:
        return "unknown", 0.5, "No CLIP reference index built"

    import torch

    query_vec = _embed_image(image_bytes)

    best_type = "unknown"
    best_score = -1.0

    for component_type, ref_vecs in _embeddings.items():
        # Cosine similarity against all reference images, take max
        sims = (query_vec @ ref_vecs.T).squeeze(0)
        score = float(sims.max().item())
        if score > best_score:
            best_score = score
            best_type = component_type

    # Confidence: map cosine sim [0.2, 0.9] → [0.0, 1.0]
    confidence = min(1.0, max(0.0, (best_score - 0.2) / 0.7))

    # If similarity is too low, fall back to unknown
    if best_score < 0.25:
        best_type = "unknown"
        confidence = 0.3

    description = f"CLIP match: {best_type.replace('_', ' ')} (sim={best_score:.2f})"
    return best_type, confidence, description
