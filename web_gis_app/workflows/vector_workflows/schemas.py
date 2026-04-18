from shared.schemas import StrictPayload


class BasePayload(StrictPayload):
    job_id: str
    input_dataset_id: str


class BufferOpPayload(BasePayload):
    distance: float
    units: str = "meters"
    segments: int = 8
