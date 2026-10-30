"""The two measures and the picture the steps share."""

import numpy as np
from PIL import Image


def _scaled(plane):
    low, high = np.percentile(plane, (1, 99.8))
    return np.clip((plane - low) / max(high - low, 1e-6), 0, 1)


def overlay(fixed, moving, path):
    """Fixed in green, moving in magenta: where they agree, the picture turns white."""
    green, magenta = _scaled(np.asarray(fixed, float)), _scaled(np.asarray(moving, float))
    rgb = np.stack([magenta, green, magenta], axis=-1)
    Image.fromarray((rgb * 255).astype(np.uint8)).save(path)


def ncc(fixed, moving):
    """Normalized cross-correlation over the tissue: 1 is a perfect match."""
    fixed, moving = np.asarray(fixed, float), np.asarray(moving, float)
    tissue = fixed > np.percentile(fixed, 60)
    a, b = fixed[tissue] - fixed[tissue].mean(), moving[tissue] - moving[tissue].mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def dice(a, b):
    """Overlap of two label images: 1 is a perfect match."""
    a, b = np.asarray(a) > 0, np.asarray(b) > 0
    return float(2 * (a & b).sum() / (a.sum() + b.sum()))
