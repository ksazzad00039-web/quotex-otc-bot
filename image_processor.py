import io
import hashlib
import logging
from typing import Tuple, Optional
from PIL import Image, ImageEnhance, ImageOps

logger = logging.getLogger("OTC_Enterprise_Quant.ImageProcessor")

class ImageProcessor:
    """
    Enterprise-grade image preprocessing engine for chart screenshots.
    Handles image dynamic scaling, compression, hashing, contrast optimization,
    and metadata cleanup before feeding image bytes to AI Vision engines.
    """

    def __init__(self, max_width: int = 1920, max_height: int = 1080, quality: int = 85):
        self.max_width = max_width
        self.max_height = max_height
        self.quality = quality

    def compute_sha256_hash(self, image_bytes: bytes) -> str:
        """
        Computes a SHA-256 cryptographic hash of the raw image bytes 
        to track and filter duplicate screenshot submissions.
        """
        return hashlib.sha256(image_bytes).hexdigest()

    def compute_perceptual_hash(self, image_bytes: bytes) -> str:
        """
        Computes a simplistic average perceptual hash (aHash) for visual similarity matching.
        Helps detect visually identical charts even if rendered with slight compression artifacts.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                avg = sum(pixels) / len(pixels)
                bits = "".join(["1" if pixel >= avg else "0" for pixel in pixels])
                hex_str = f"{int(bits, 2):016x}"
                return hex_str
        except Exception as e:
            logger.error(f"Failed to compute perceptual hash: {str(e)}")
            return ""

    def validate_image_dimensions(self, image_bytes: bytes) -> Tuple[bool, str, Tuple[int, int]]:
        """
        Verifies if the provided file is a valid image and meets basic resolution thresholds.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                if width < 300 or height < 300:
                    return False, "Resolution too low for candle structure analysis (min 300x300).", (width, height)
                return True, "Valid image", (width, height)
        except Exception as e:
            logger.error(f"Image validation exception: {str(e)}")
            return False, "Corrupted or invalid image file.", (0, 0)

    def optimize_chart_for_vision(
        self, 
        image_bytes: bytes, 
        enhance_contrast: bool = False
    ) -> Optional[bytes]:
        """
        Processes and resizes large screenshots to ensure fast transmission
        to the Gemini Vision API without losing candlestick clarity.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert RGBA or Palette formats to standard RGB
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")

                # Auto-orient based on EXIF tag if present
                img = ImageOps.exif_transpose(img)

                # Resize if image exceeds maximum allowed dimensions
                orig_w, orig_h = img.size
                if orig_w > self.max_width or orig_h > self.max_height:
                    img.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
                    logger.info(f"Resized screenshot from {orig_w}x{orig_h} to {img.width}x{img.height}")

                # Optional contrast enhancement for dim or low-contrast chart themes
                if enhance_contrast:
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.2)  # Boost contrast by 20%

                # Save compressed JPEG to memory buffer
                output_buffer = io.BytesIO()
                img.save(
                    output_buffer, 
                    format="JPEG", 
                    quality=self.quality, 
                    optimize=True
                )
                optimized_bytes = output_buffer.getvalue()
                logger.info(f"Image optimization complete. Compression ratio: {len(image_bytes)} -> {len(optimized_bytes)} bytes.")
                return optimized_bytes

        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            return None

    def process_screenshot(self, image_bytes: bytes) -> Tuple[bool, str, Optional[bytes], str, str]:
        """
        Master execution pipeline for image processing.
        Returns: (is_valid, status_message, processed_bytes, sha256_hash, perceptual_hash)
        """
        is_valid, msg, dims = self.validate_image_dimensions(image_bytes)
        if not is_valid:
            return False, msg, None, "", ""

        sha256_h = self.compute_sha256_hash(image_bytes)
        p_hash = self.compute_perceptual_hash(image_bytes)

        processed_bytes = self.optimize_chart_for_vision(image_bytes, enhance_contrast=False)
        if processed_bytes is None:
            return False, "Failed during image optimization pipeline.", None, sha256_h, p_hash

        return True, "Image processed successfully", processed_bytes, sha256_h, p_hash

