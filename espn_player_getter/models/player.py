from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Player:
    """Represents an ESPN Fantasy Baseball player."""
    id: str
    name: str
    team: str
    position: str
    eligible_positions: List[str]
    is_starter: bool = False
    player_type: str = ""  # 'batter' or 'pitcher'
    stats: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Convert player to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "eligible_positions": self.eligible_positions,
            "is_starter": self.is_starter,
            "player_type": self.player_type,
            "stats": self.stats
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
            is_starter=data.get("is_starter", False),
            player_type=data.get("player_type", ""),
            stats=data.get("stats")
        )
