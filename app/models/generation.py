from enum import Enum

from pydantic import BaseModel, Field

from app.models.pricing import Selection


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class GenerationRequest(BaseModel):
    photo_id: str
    product_id: str
    selections: list[Selection] = Field(default_factory=list)


class GenerationJob(BaseModel):
    """Input to the image-generation seam.

    ``region_label`` carries the accusative zone name for the
    "Мы изменим только {region}" copy, and doubles as the mask target hint.
    """

    job_id: str
    source_photo_id: str
    product_id: str
    category_id: str
    region_label: str
    selections: list[Selection] = Field(default_factory=list)


class GenerationResult(BaseModel):
    before_url: str
    after_url: str
    # The stored id behind after_url. Sharing resolves job_id -> this, so the
    # client never names a file: a client-supplied path would let any caller
    # have the bot send them somebody else's photo out of media/.
    after_photo_id: str


class JobState(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.pending
    progress: int = 0
    step_index: int = 0
    steps: list[str] = Field(default_factory=list)
    sub: str = ""
    before_url: str | None = None
    after_url: str | None = None
    after_photo_id: str | None = None
    error: str | None = None
