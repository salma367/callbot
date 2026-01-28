from pydantic import BaseModel


class CallProcessRequest(BaseModel):
    call_id: str
    text: str
