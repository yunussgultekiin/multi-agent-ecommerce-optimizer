from pydantic import BaseModel

class ImageGenerationInput(BaseModel):
    user_product: dict
    target_platform: str
    rival_json: dict = {}

class ImageOutput(BaseModel):
    generated_image_url: str | None
    selected_variant: dict | None
    fallback_used: bool
