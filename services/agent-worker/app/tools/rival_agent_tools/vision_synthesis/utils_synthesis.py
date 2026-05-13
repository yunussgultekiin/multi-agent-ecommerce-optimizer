import base64
import httpx
    
async def fetch_image_as_base64(url: str, client: httpx.AsyncClient) -> dict:
    response = await client.get(url, timeout = 30)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "image/jpeg")

    return {
        "mime_type": content_type.split(";")[0],
        "data": base64.b64encode(response.content).decode()
    }

def clean_json_response(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    
    return text.strip()
