from typing import List, Dict
from datetime import datetime


class MessageEntry:
    def __init__(self, sender: str, message: str, ai_name: str = None, model: str = None,
                 is_partial: bool = False, is_divider: bool = False, timestamp: str = None):
        self.sender = sender
        self.message = message
        self.ai_name = ai_name
        self.model = model
        self.is_partial = is_partial
        self.is_divider = is_divider
        self.timestamp = timestamp or datetime.now().isoformat()

    def __eq__(self, other):
        if isinstance(other, MessageEntry):
            return (self.sender == other.sender and
                    self.message == other.message and
                    self.ai_name == other.ai_name and
                    self.model == other.model)
        return False

    def to_dict(self):
        return {
            "sender": self.sender,
            "message": self.message,
            "ai_name": self.ai_name,
            "model": self.model,
            "is_partial": self.is_partial,
            "is_divider": self.is_divider,
            "timestamp": self.timestamp
        }


class ConversationThread:
    def __init__(self, date: str, topic: str, messages: List[MessageEntry]):
        self.date = date
        self.topic = topic
        self.messages = messages

    def to_dict(self):
        return {
            'date': self.date,
            'topic': self.topic,
            'messages': [msg.to_dict() for msg in self.messages]
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            date=data['date'],
            topic=data['topic'],
            messages=[MessageEntry(**msg) for msg in data['messages']]
        )


ConversationHistory = Dict[str, ConversationThread]
