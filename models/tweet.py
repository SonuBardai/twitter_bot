from typing import List, Optional
from pydantic import BaseModel, Field


class Tweet(BaseModel):
    """Represents a single tweet with its content and character count."""

    content: str = Field(..., description="The actual tweet content")
    char_count: int = Field(..., description="Number of characters in the tweet")

    class Config:
        extra = "ignore"  # Ignore extra fields


class Tweets(BaseModel):
    """Represents a collection of tweets that can form a thread."""

    items: List[Tweet] = Field(default_factory=list, description="List of tweets in the thread")
    is_thread: bool = Field(False, description="Whether this is a thread (multiple tweets)")

    def validate_items_not_empty(cls, v: List[Tweet]) -> List[Tweet]:
        if not v:
            raise ValueError("At least one tweet is required")
        return v

    @property
    def first_tweet(self) -> Optional[Tweet]:
        """Get the first tweet in the thread."""
        return self.items[0] if self.items else None

    @property
    def is_valid(self) -> bool:
        """Check if the tweets are valid (all tweets are valid and within length limits)."""
        try:
            self.validate_self()
            return all(tweet.char_count <= 280 for tweet in self.items)
        except Exception:
            return False

    def to_dict(self) -> dict:
        """Convert the tweets to a dictionary representation."""
        return {"items": [tweet.model_dump() for tweet in self.items], "is_thread": self.is_thread}

    @classmethod
    def from_dict(cls, data: dict) -> "Tweets":
        """Create a Tweets instance from a dictionary."""
        return cls(items=[Tweet(**tweet_data) for tweet_data in data.get("items", [])], is_thread=data.get("is_thread", False))
