from pydantic import BaseModel
from typing import Optional

class DiscoveredCompetitor(BaseModel):
    competitor_name: str
    product_url: str
    platform: str

class DiscoveryResult(BaseModel):
    competitors: list[DiscoveredCompetitor]
    source_urls: list[str] = []

class DiscoveryToolResult(BaseModel):
    success: bool
    data: Optional[DiscoveryResult] = None
    fallback_used: bool = False
    error: Optional[str] = None
