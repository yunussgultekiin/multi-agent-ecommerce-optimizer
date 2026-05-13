from dataclasses import dataclass, field

@dataclass
class ToolResult:
    success: bool
    data: dict = field(default_factory=dict)
    fallback_used: bool = False
