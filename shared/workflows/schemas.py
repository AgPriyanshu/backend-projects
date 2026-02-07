from pydantic import BaseModel, ConfigDict


class StrictPayload(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
