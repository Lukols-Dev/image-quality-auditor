"""Image quality metrics computation.

Computes three quality metrics from an image's grayscale representation:
mean brightness, contrast (standard deviation), and sharpness (variance of
the Laplacian). These are the raw measurements that the scanner compares
against configured thresholds to classify image quality.

All metric functions operate on a 2D grayscale NumPy array (dtype uint8,
shape (height, width)). Loading and grayscale conversion are handled by
load_grayscale, which raises ImageLoadError for unreadable files.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from image_quality_auditor.models import ImageMetrics


class ImageLoadError(Exception):
    """Raised when an image file cannot be read or decoded."""


def load_grayscale(path: Path) -> np.ndarray:
    """Load an image from disk and convert it to grayscale.

    Args:
        path: Path to the image file.

    Returns:
        A 2D grayscale image as a uint8 NumPy array of shape
        (height, width).

    Raises:
        ImageLoadError: If the file cannot be read or decoded (missing,
            corrupted, or an unsupported format).
    """
    # cv2.imread returns None on failure instead of raising.
    image = cv2.imread(str(path))
    if image is None:
        msg = f"Cannot read or decode image: {path}"
        raise ImageLoadError(msg)

    # Convert BGR (OpenCV's default channel order) to single-channel gray.
    gray: np.ndarray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray


def compute_brightness(gray: np.ndarray) -> float:
    """Compute mean brightness as the average pixel value.

    Args:
        gray: 2D grayscale image (uint8).

    Returns:
        Mean pixel value in the range 0.0-255.0.
    """
    return float(np.mean(gray))


def compute_contrast(gray: np.ndarray) -> float:
    """Compute contrast as the standard deviation of pixel values.

    A higher standard deviation indicates greater spread between light and
    dark regions, i.e., higher contrast.

    Args:
        gray: 2D grayscale image (uint8).

    Returns:
        Standard deviation of pixel values (>= 0.0).
    """
    return float(np.std(gray))


def compute_sharpness(gray: np.ndarray) -> float:
    """Compute sharpness as the variance of the Laplacian.

    The Laplacian highlights edges (rapid intensity changes). A sharp image
    has many strong edges, producing a high variance; a blurred image has
    weak edges, producing a low variance. This is a standard blur-detection
    metric.

    The Laplacian is computed in 64-bit float (CV_64F) so that negative
    edge responses are preserved; using uint8 would clip them to zero and
    distort the variance.

    Args:
        gray: 2D grayscale image (uint8).

    Returns:
        Variance of the Laplacian (>= 0.0). Higher means sharper.
    """
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def compute_metrics(gray: np.ndarray) -> ImageMetrics:
    """Compute all quality metrics for a grayscale image.

    Args:
        gray: 2D grayscale image (uint8).

    Returns:
        An ImageMetrics value object holding brightness, contrast, and
        sharpness.
    """
    return ImageMetrics(
        mean_brightness=compute_brightness(gray),
        contrast_std=compute_contrast(gray),
        sharpness_laplacian_variance=compute_sharpness(gray),
    )
