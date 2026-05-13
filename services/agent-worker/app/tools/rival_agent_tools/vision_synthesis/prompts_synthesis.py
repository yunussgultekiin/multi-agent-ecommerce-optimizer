import json

def build_synthesis_prompt(user_analyses: list[dict], competitor_analyses: list[dict]) -> str:
    return f"""
    Analyze the following visual analyses and produce output in JSON format.

    USER PRODUCT ANALYSES:
    {json.dumps([a['raw_analysis'] for a in user_analyses], ensure_ascii=False)}

    COMPETITOR PRODUCT ANALYSES:
    {json.dumps([a['raw_analysis'] for a in competitor_analyses], ensure_ascii=False)}

    TASK:
    1. Identify successful patterns in competitor visuals
       (high quality, professional composition, effective backgrounds, etc.)
    2. Determine the strong features of the user's product
    3. Combine both to create a detailed prompt for Imagen 3

    generation_prompt RULES:
    - Start with "A professional product photo of [product]"
    - Include successful styles from competitor visuals
    - Specify lighting, composition, and background details
    - Minimum 20, maximum 300 characters
    - Write in English (for Imagen 3)

    RESPOND ONLY in this JSON format and nothing else:
    {{
        "dominant_colors": ["#hex1", "#hex2"],
        "composition_style": "string",
        "background_type": "string",
        "product_focus_score": 0.0,
        "quality_score": 0.0,
        "style_tags": ["tag1", "tag2"],
        "improvement_suggestions": ["suggestion1", "suggestion2"],
        "generation_prompt": "A professional product photo of..."
    }}
    """