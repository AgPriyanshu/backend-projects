import logging

from fastai.vision.all import PILImage
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .classifier import DeviceClassifier
from .constants import ARTIFACTS_PATH
from .serializers import DeviceClassifierSerializer

logger = logging.getLogger(__name__)


class DeviceClassifierViewSet(ViewSet):
    @action(detail=False, methods=["post"])
    def classify(self, request):
        try:
            serializer = DeviceClassifierSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Get the uploaded image file
            if "device" not in request.FILES:
                return Response(
                    {
                        "success": False,
                        "error": 'No image file provided. Please upload an image with field name "device".',
                        "predicted_class": None,
                        "confidence": 0.0,
                        "all_predictions": [],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            img_file = request.FILES["device"]
            logger.info(
                f"Processing image: {img_file.name}, size: {img_file.size} bytes"
            )

            # Create PILImage from uploaded file
            img = PILImage.create(img_file)

            # Initialize classifier and make prediction
            classifier = DeviceClassifier(
                ARTIFACTS_PATH / "gadget_classifier_model.pkl"
            )
            result = classifier.predict(img)

            # Log the prediction result
            if result.get("success"):
                logger.info(
                    f"Prediction successful: {result['predicted_class']} ({result['confidence']:.3f})"
                )
            else:
                logger.error(f"Prediction failed: {result.get('error')}")

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Classification request failed: {str(e)}")
            error_response = {
                "success": False,
                "error": f"Internal server error: {str(e)}",
                "predicted_class": None,
                "confidence": 0.0,
                "all_predictions": [],
            }
            return Response(
                error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
