STRICT_JSON_SYNTAX_RULES = """
JSON syntax (mandatory — invalid output is rejected):
- Use standard JSON (RFC 8259). Every key and every string value MUST use double quotes (").
- NEVER use single quotes (') as JSON delimiters for keys or string values.
  Wrong: {'competitor_name': 'X'}
  Correct: {"competitor_name": "X"}
- NEVER use unquoted property names. Wrong: {key: "val"}. Correct: {"key": "val"}.
- Apostrophe in Turkish text is allowed inside a double-quoted string (e.g. "ürünün kalitesi").
- To include a double quote inside a string, escape it: \\"
- No Python dict syntax, no JavaScript-style trailing commas, no comments.
- Return exactly one JSON object; no markdown fences; no text before or after the JSON.

String safety (mandatory):
- Every string must start and end on the same line. Never put a raw newline inside a string value.
- Avoid double quote characters inside Turkish text. Prefer apostrophes or plain text instead.
- If a double quote is unavoidable inside a string, escape it as \\\".
- Do not leave any string unfinished. Every opening " must have a matching closing ".
- Keep each natural-language string concise: max 140 characters for array items, max 280 characters for summary fields.
- Do not use bullets, numbered lists, markdown markers, or multi-paragraph text inside string values.

Comma safety (mandatory):
- In arrays, put a comma between every item and no comma after the final item.
- In objects, put a comma between every property and no comma after the final property.
- Before returning, mentally validate with json.loads: if it would fail, rewrite the whole JSON.

Numeric values (mandatory):
- Use only valid JSON numbers or null for missing/unavailable numeric fields.
- NEVER output NaN, -NaN, Infinity, or -Infinity — they are not valid JSON.
  Wrong: {"price": NaN} or {"price": Infinity}
  Correct: {"price": null}
- Use null when price, rating, review_count, price_delta, or any numeric field is unknown or not found.
- Do not use 0.0 as a placeholder for unknown prices unless the task explicitly requires a numeric estimate.
"""

JSON_SELF_CORRECTION_SYNTAX = """
- Use double quotes (") for every JSON key and string value — never single quotes (').
- If the error mentions "property name enclosed in double quotes", quote every key like "key": not 'key': or key:
- If the error mentions "Expecting ',' delimiter", add the missing comma between adjacent array items or object properties.
- If the error mentions "Unterminated string", close the string, remove raw newlines from it, and escape any internal double quotes as \\\".
- Replace any NaN or Infinity numeric literals with null (or a real finite number if the value is known).
"""
