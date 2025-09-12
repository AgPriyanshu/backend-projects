import logging
import warnings
from pathlib import Path
from typing import Dict, List, Union

from fastai.vision.all import PILImage, load_learner
from PIL import Image

# Suppress PIL warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PIL.Image")

logger = logging.getLogger(__name__)


class DeviceClassifier:
    """
    FastAI-based gadget classifier for Django integration.

    Classifies images into gadget categories: smartphone, tablet, smartwatch, headphones, camera
    """

    def __init__(self, model_path: Union[str, Path, None] = None):
        """
        Initialize the classifier.

        Args:
            model_path: Path to the trained FastAI model (.pkl file)
        """
        self.model = None
        self.classes = []
        self.is_loaded = False
        logger.debug(f"Initializing DeviceClassifier with model_path: {model_path}")
        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: Union[str, Path]) -> bool:
        """
        Load the trained FastAI model.

        Args:
            model_path: Path to the model file

        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            model_path = Path(model_path)

            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")

            logger.info(f"Loading model from {model_path}")
            self.model = load_learner(model_path)
            self.classes = self.model.dls.vocab
            self.is_loaded = True

            logger.info(f"Model loaded successfully. Classes: {self.classes}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.is_loaded = False
            return False

    def _preprocess_image(
        self, image: Union[str, Path, Image.Image, bytes]
    ) -> PILImage:
        """
        Preprocess image for inference.

        Args:
            image: Image as file path, PIL Image, or bytes

        Returns:
            PILImage: Preprocessed image ready for FastAI model
        """
        try:
            # Handle different input types
            if isinstance(image, (str, Path)):
                pil_image = Image.open(image)
            elif isinstance(image, bytes):
                from io import BytesIO

                pil_image = Image.open(BytesIO(image))
            elif isinstance(image, Image.Image):
                pil_image = image
            else:
                raise ValueError(f"Unsupported image type: {type(image)}")

            # Convert to RGB (same as training preprocessing)
            if pil_image.mode == "P":
                pil_image = (
                    pil_image.convert("RGBA")
                    if "transparency" in pil_image.info
                    else pil_image.convert("RGB")
                )
            elif pil_image.mode in ("RGBA", "LA"):
                pil_image = pil_image.convert("RGB")

            # Convert to FastAI PILImage
            return PILImage.create(pil_image)

        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise

    def predict(self, image: Union[str, Path, Image.Image, bytes]) -> Dict:
        """
        Predict gadget class for an image.

        Args:
            image: Image as file path, PIL Image, or bytes

        Returns:
            Dict containing prediction results:
            {
                'predicted_class': str,
                'confidence': float,
                'all_predictions': List[Dict[str, float]]
            }
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            # Preprocess image
            processed_image = self._preprocess_image(image)
            # Make prediction
            pred_class, pred_idx, probs = self.model.predict(processed_image)

            # Convert tensors to Python types
            confidence = float(probs[pred_idx])
            predicted_class = str(pred_class)

            # Create detailed predictions
            all_predictions = []
            for i, (class_name, prob) in enumerate(zip(self.classes, probs)):
                all_predictions.append(
                    {"class": str(class_name), "confidence": float(prob), "rank": i + 1}
                )

            # Sort by confidence (descending)
            all_predictions.sort(key=lambda x: x["confidence"], reverse=True)

            # Update ranks after sorting
            for i, pred in enumerate(all_predictions):
                pred["rank"] = i + 1

            result = {
                "predicted_class": predicted_class,
                "confidence": confidence,
                "all_predictions": all_predictions,
                "success": True,
                "error": None,
            }

            logger.info(f"Prediction: {predicted_class} ({confidence:.3f})")
            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                "predicted_class": None,
                "confidence": 0.0,
                "all_predictions": [],
                "success": False,
                "error": str(e),
            }

    def predict_batch(
        self, images: List[Union[str, Path, Image.Image, bytes]]
    ) -> List[Dict]:
        """
        Predict gadget classes for multiple images.

        Args:
            images: List of images

        Returns:
            List of prediction dictionaries
        """
        results = []
        for image in images:
            result = self.predict(image)
            results.append(result)
        return results

    def get_model_info(self) -> Dict:
        """
        Get information about the loaded model.

        Returns:
            Dict with model information
        """
        if not self.is_loaded:
            return {"loaded": False, "error": "Model not loaded"}

        return {
            "loaded": True,
            "classes": self.classes,
            "num_classes": len(self.classes),
            "model_type": "FastAI Vision Learner",
            "architecture": "ResNet18",
        }
