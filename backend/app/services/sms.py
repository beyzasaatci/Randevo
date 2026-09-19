import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class SmsService(Protocol):
    async def send_otp(self, phone_number: str, code: str) -> None: ...


class MockSmsService:
    async def send_otp(self, phone_number: str, code: str) -> None:
        logger.info("Mock SMS OTP generated for phone ending %s: %s", phone_number[-2:], code)


sms_service: SmsService = MockSmsService()