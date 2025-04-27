from typing import Optional
from datetime import datetime

class UserRead:
    hp: int
    attack: int
    defense: int
    speed: int
    booster_credits: int
    allow_bot_challenges: bool
    last_seen: datetime
    stats: dict # Or define a more specific Stats schema
    # Add related fields if needed, ensure they are fetched in the endpoint
    # attacks: List[AttackRead] # Example if you want to include all learned attacks
    # selected_attacks: List[AttackRead] # Example for selected

    profile_picture_url: Optional[str] = None # Add the new field
    profile_picture_prompt: Optional[str] = None # Optional: Include prompt if needed

    # Pydantic config to allow ORM mode
    class Config:
        from_attributes = True 