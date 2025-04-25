from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Player:
    """Represents an ESPN Fantasy Baseball player."""
    id: str
    name: str
    team: str
    position: str
    eligible_positions: List[str]
    stats: Optional[dict] = None
    image_url: str = ""
    bio_data: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert player to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "eligible_positions": self.eligible_positions,
            "stats": self.stats,
            "image_url": self.image_url,
            "bio_data": self.bio_data
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Player':
        """Create a Player instance from dictionary data."""
        return cls(
            id=data["id"],
            name=data["name"],
            team=data["team"],
            position=data["position"],
            eligible_positions=data["eligible_positions"],
            stats=data.get("stats"),
            image_url=data.get("image_url", ""),
            bio_data=data.get("bio_data", {})
        )
