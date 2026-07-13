from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RevokedTokenCreate(BaseModel):
    jti: str
    expires_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RevokedTokenUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
