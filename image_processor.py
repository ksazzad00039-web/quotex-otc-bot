import io
import hashlib
import logging
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageEnhance, ImageOps, ImageFilter

# Fallback Configuration Logging Setup
try:
    from config import logger
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.ImageProcessor")


class ImageProcessor:
    """
    Enterprise-Grade Image Preprocessing Pipeline for OTC Binary Options Charts.
    Handles Chart Normalization, Dual Cryptographic Hashing (SHA256 + dHash/aHash),
    Contrast Tuning, and Aspect Ratio Validation for 1-Hour & 1-Day Chart Screenshots.
    """

    def __init__(self, max_width: int = 1920, max_height: int = 1080, quality: int = 88):
        self.max_width = max_width
        self.max_height = max_height
        self.quality = quality

    def compute_sha256_hash(self, image_bytes: bytes) -> str:
        """Computes cryptographic SHA-256 hash to identify exact duplicate screenshot files."""
        return hashlib.sha256(image_bytes).hexdigest()

    def compute_perceptual_ahash(self, image_bytes: bytes) -> str:
        """Computes Average Perceptual Hash (aHash) for baseline chart visual matching."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                avg = sum(pixels) / len(pixels)
                bits = "".join(["1" if pixel >= avg else "0" for pixel in pixels])
                return f"{int(bits, 2):016x}"
        except Exception as e:
            logger.error(f"Failed to compute aHash: {str(e)}")
            return ""

    def compute_difference_dhash(self, image_bytes: bytes) -> str:
        """
        Computes Difference Perceptual Hash (dHash) for high-precision structural similarity matching.
        Extremely effective at matching candlestick structures despite compression artifacts.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Resize to 9x8 to compute 8 gradient differences
                img = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                difference = []
                for row in range(8):
                    for col in range(8):
                        pixel_left = pixels[row * 9 + col]
                        pixel_right = pixels[row * 9 + col + 1]
                        difference.append(pixel_left > pixel_right)

                bits = "".join(["1" if val else "0" for val in difference])
                return f"{int(bits, 2):016x}"
        except Exception as e:
            logger.error(f"Failed to compute dHash: {str(e)}")
            return ""

    def validate_chart_dimensions(self, image_bytes: bytes) -> Tuple[bool, str, Tuple[int, int]]:
        """
        Validates whether provided image file meets minimum structural requirements
        needed for 1-Hour OTC candlestick analysis.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size

                # Minimum threshold check
                if width < 350 or height < 350:
                    return (
                        False,
                        f"Screenshot resolution too low ({width}x{height}). Minimum required: 350x350 for clear wick analysis.",
                        (width, height)
                    )

                # Extreme Aspect Ratio Check
                aspect_ratio = width / float(height)
                if aspect_ratio > 4.0 or aspect_ratio < 0.25:
                    return (
                        False,
                        f"Abnormal aspect ratio ({aspect_ratio:.2f}). Please capture a standard chart view.",
                        (width, height)
                    )

                return True, "Valid chart image dimensions.", (width, height)

        except Exception as e:
            logger.error(f"Image validation exception: {str(e)}")
            return False, "Corrupted or invalid image file.", (0, 0)

    def optimize_chart_for_vision(
        self,
        image_bytes: bytes,
        enhance_contrast: bool = True,
        sharpen_wicks: bool = True
    ) -> Optional[bytes]:
        """
        Optimizes screenshot for AI Vision processing:
        - Normalizes colors and strips EXIF tags
        - Enhances contrast for dim dark themes
        - Sharpens thin wicks for support/resistance rejection detection
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert non-standard RGBA/Palette images to clean RGB
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")

                # Transpose according to EXIF rotation tags
                img = ImageOps.exif_transpose(img)

                # Dynamic Resizing while retaining structural aspect ratio
                orig_w, orig_h = img.size
                if orig_w > self.max_width or orig_h > self.max_height:
                    img.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
                    logger.info(f"Resized screenshot: {orig_w}x{orig_h} -> {img.width}x{img.height}")

                # Contrast Tuning for dark Quotex OTC chart layouts
                if enhance_contrast:
                    contrast_enhancer = ImageEnhance.Contrast(img)
                    img = contrast_enhancer.enhance(1.15)  # 15% Contrast boost

                # Color Saturation boost for clear green/red candle differentiation
                color_enhancer = ImageEnhance.Color(img)
                img = color_enhancer.enhance(1.10)

                # Optional Sharpening filter to make thin rejection wicks vivid for Vision AI
                if sharpen_wicks:
                    img = img.filter(ImageFilter.SMOOTH_MORE)
                    sharpener = ImageEnhance.Sharpness(img)
                    img = sharpener.enhance(1.20)

                # Export compressed buffer
                output_buffer = io.BytesIO()
                img.save(
                    output_buffer,
                    format="JPEG",
                    quality=self.quality,
                    optimize=True
                )
                optimized_bytes = output_buffer.getvalue()

                logger.info(
                    f"Image optimization successful | Size reduction: "
                    f"{len(image_bytes)} -> {len(optimized_bytes)} bytes."
                )
                return optimized_bytes

        except Exception as e:
            logger.error(f"Image optimization pipeline failed: {str(e)}")
            return None

    def process_screenshot(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Master execution pipeline for chart processing.
        
        Returns:
            Dict containing validity status, processed bytes, sha256 hash, and dual perceptual hashes.
        """
        is_valid, msg, dims = self.validate_chart_dimensions(image_bytes)
        if not is_valid:
            return {
                "success": False,
                "message": msg,
                "processed_bytes": None,
                "sha256": "",
                "ahash": "",
                "dhash": "",
                "dimensions": dims
            }

        sha256_h = self.compute_sha256_hash(image_bytes)
        a_hash = self.compute_perceptual_ahash(image_bytes)
        d_hash = self.compute_difference_dhash(image_bytes)

        processed_bytes = self.optimize_chart_for_vision(
            image_bytes,
            enhance_contrast=True,
            sharpen_wicks=True
        )

        if processed_bytes is None:
            return {
                "success": False,
                "message": "Optimization pipeline failed.",
                "processed_bytes": None,
                "sha256": sha256_h,
                "ahash": a_hash,
                "dhash": d_hash,
                "dimensions": dims
            }

        return {
            "success": True,
            "message": "Chart screenshot processed successfully.",
            "processed_bytes": processed_bytes,
            "sha256": sha256_h,
            "ahash": a_hash,
                "dhash": d_hash,
            "dimensions": dims
        }


# Global Instance Export
processor = ImageProcessor()
# Class Alias for Flexible Importing
ChartImageProcessor = ImageProcessor

if __name__ == "__main__":
    print("Image Processor Module Ready.")
