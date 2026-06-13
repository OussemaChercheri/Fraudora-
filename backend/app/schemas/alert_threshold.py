from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertThresholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    threshold_key: str
    threshold_value: float
    description: str
    updated_at: datetime


class AlertThresholdUpdate(BaseModel):
    threshold_value: float
