import base64
import re
import httpx

MAX_IMAGE_BYTES = 8 * 1024 * 1024

def normalize_image_url(url: str) -> str | None:
    if not isinstance(url, str): return None

    normalized = url.strip()
    if not normalized: return None

    if not normalized.startswith(("http://", "https://")): return None
    
    return normalized


async def fetch_image_as_base64(url: str, client: httpx.AsyncClient) -> dict:
    normalized_url = normalize_image_url(url)

    if not normalized_url:
        raise ValueError("Image URL must be a valid http or https URL")

    response = await client.get(
        normalized_url,
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "image/jpeg").split(";")[0]

    if not content_type.startswith("image/"):
        raise ValueError(f"URL did not return an image. content-type={content_type}")

    if len(response.content) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image is too large. Max allowed size is {MAX_IMAGE_BYTES} bytes"
        )

    return {
        "mime_type": content_type,
        "data": base64.b64encode(response.content).decode("utf-8"),
    }


def clean_json_response(raw_text: str) -> str:
    text = (raw_text or "").strip()

    fenced_json = re.search(
        r"```(?:json)?\s*(.*?)```",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if fenced_json:
        return fenced_json.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1].strip()

    return text