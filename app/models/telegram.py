from pydantic import BaseModel


class TelegramUser(BaseModel):
    """The `user` object out of a validated initData payload.

    Only the fields the shop actually uses. Telegram sends more; extra keys are
    ignored rather than rejected, so a new Bot API field cannot break booking.
    """

    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    language_code: str = ""

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p)

    @property
    def handle(self) -> str:
        """@username when the user has one — many Telegram accounts do not."""
        return f"@{self.username}" if self.username else ""
