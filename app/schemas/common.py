from pydantic import BaseModel
from typing import List, Optional, Any

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    data: Any
    meta: Optional[dict] = None
