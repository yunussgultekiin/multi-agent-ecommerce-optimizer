PLATFORM_SITES = {
    "trendyol": "site:trendyol.com",
    "amazon": "site:amazon.com.tr",
    "hepsiburada": "site:hepsiburada.com",
}

def build_discovery_prompt(platform: str, category: str, product_title: str, brand: str) -> str:
    site_filter = PLATFORM_SITES.get(platform, "")
    return f"""Search for top competitor products on {platform} ({site_filter}) in the "{category}" category similar to "{product_title}".
Do NOT include any products from the brand "{brand}".
Find 3 to 5 competitor products from different brands.

Return ONLY valid JSON in this exact format, nothing else:
{{
    "competitors": [
        {{
            "competitor_name": "Brand Name - Product Name",
            "product_url": "https://...",
            "platform": "{platform}"
        }}
    ]
}}

Rules:
- product_url must be a real, valid URL on {platform} ({site_filter})
- competitor_name must include both brand and product name
- Return between 3 and 5 competitors
- Exclude any product from brand "{brand}"
"""
