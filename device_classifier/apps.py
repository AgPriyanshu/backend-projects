import logging

import wandb
from django.apps import AppConfig

from .constants import ARTIFACTS_PATH

logger = logging.getLogger(__name__)


class DeviceClassifierConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "device_classifier"

    def ready(self):
        if ARTIFACTS_PATH.exists():
            logger.info(f"Artifact already exists at {ARTIFACTS_PATH}")
            return
        wandb.login()
        run = wandb.init(entity="prinzz-personal", project="gadgets-predictor")
        artifact = run.use_artifact("gadget_classifier_model:latest")
        artifact.download(ARTIFACTS_PATH)
        logger.info(f"Artifact downloaded to {ARTIFACTS_PATH}")
