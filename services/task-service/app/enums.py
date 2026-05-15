from enum import Enum

class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class SeoTone(str, Enum):
    samimi = "samimi"
    profesyonel = "profesyonel"
    premium = "premium"
