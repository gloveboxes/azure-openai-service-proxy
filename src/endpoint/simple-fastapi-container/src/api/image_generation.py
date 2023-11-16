""" Images Generations API """

from enum import Enum
import json
import logging
from typing import Tuple
import asyncio
import httpx
import openai
from pydantic import BaseModel

from .config import OpenAIConfig
from .openai_async import OpenAIAsyncManager

OPENAI_IMAGES_GENERATIONS_API_VERSION = "2023-06-01-preview"

logging.basicConfig(level=logging.WARNING)


class ResponseFormat(Enum):
    """Response Format"""

    URL = "url"
    BASE64 = "b64_json"


class ImageSize(Enum):
    """Image Size"""

    IS_256X256 = "256x256"
    IS_512X512 = "512x512"
    IS_1024X1024 = "1024x1024"


class DalleTimeoutError(Exception):
    """Raised when the Dalle request times out"""


class ImagesGenerationsRequst(BaseModel):
    """OpenAI Images Generations Request"""

    prompt: str
    response_format: ResponseFormat = ResponseFormat.URL
    n: int = 1
    size: ImageSize = ImageSize.IS_1024X1024
    user: str = None
    api_version: str = OPENAI_IMAGES_GENERATIONS_API_VERSION


class ImagesGenerations:
    """OpenAI Images Generations Manager"""

    def __init__(self, openai_config: OpenAIConfig):
        """init in memory session manager"""
        self.openai_config = openai_config
        self.logger = logging.getLogger(__name__)

    def validate_input(self, images: ImagesGenerationsRequst):
        """validate input"""
        # do some basic input validation
        if not images.prompt:
            return self.report_exception("Oops, no prompt.", 400)

        if len(images.prompt) > 1000:
            return self.report_exception(
                "Oops, prompt is too long. The maximum length is 1000 characters.", 400
            )

        # check the image_count is between 1 and 5
        if images.n and not 1 <= images.n <= 5:
            return self.report_exception(
                "Oops, image_count must be between 1 and 5 inclusive.", 400
            )

        # check the image_size is between 256x256, 512x512, 1024x1024
        if images.size and images.size not in ImageSize:
            return self.report_exception(
                "Oops, image_size must be 256x256, 512x512, 1024x1024.", 400
            )

        # check the response_format is url or base64
        if images.response_format and images.response_format not in ResponseFormat:
            return self.report_exception(
                "Oops, response_format must be url or b64_json.", 400
            )

        return None, None

    def report_exception(
        self, message: str, http_status_code: int
    ) -> Tuple[openai.openai_object.OpenAIObject, int]:
        """report exception"""

        self.logger.warning(msg=f"{message}")

        return message, http_status_code

    async def call_openai_images_generations(
        self, images: ImagesGenerationsRequst
    ) -> Tuple[openai.openai_object.OpenAIObject, int]:
        """call openai with retry"""

        retry_count = 0

        completion, http_status_code = self.validate_input(images)

        if completion or http_status_code:
            return completion, http_status_code

        try:
            deployment = await self.openai_config.get_deployment()

            openai_request = {
                "prompt": images.prompt,
                "n": images.n,
                "size": images.size.value,
                "response_format": images.response_format.value,
            }

            url = (
                f"https://{deployment.resource_name}.openai.azure.com"
                "/openai/images/generations:submit"
                f"?api-version={images.api_version}"
            )

            async_mgr = OpenAIAsyncManager(deployment)
            response = await async_mgr.async_post(openai_request, url)

            operation_location = response.headers["operation-location"]
            status = ""

            while status != "succeeded" and status != "failed":
                # retry 20 times which is 20 * 3 second sleep = 60 seconds max wait
                if retry_count >= 20:
                    raise DalleTimeoutError

                await asyncio.sleep(3)

                async_mgr = OpenAIAsyncManager(deployment)
                response = await async_mgr.async_get(operation_location)

                response = response.json()

                status = response["status"]
                retry_count += 1

            return response, response.get("http_status_code", 200)

        except DalleTimeoutError:
            return self.report_exception(
                "OpenAI Dalle request retry exceeded",
                408,
            )

        except httpx.ConnectError:
            return self.report_exception(
                "Service connection error.",
                504,
            )

        except httpx.ConnectTimeout:
            return self.report_exception(
                "Service connection timeout error.",
                504,
            )

        except httpx.HTTPStatusError as http_status_error:
            return self.report_exception(
                json.loads(http_status_error.response.text).get("error").get("message"),
                http_status_error.response.status_code,
            )

        except Exception as exception:
            self.logger.warning(msg=f"Global exception caught: {exception}")
            raise exception