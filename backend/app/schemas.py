from pydantic import BaseModel, Field


class OtpRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)


class OtpRequestResponse(BaseModel):
    message: str
    retry_after_seconds: int


class OtpVerify(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)
    code: str = Field(pattern=r"^\d{6}$")


class OtpVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_id: str
    requires_name: bool


class CustomerProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)