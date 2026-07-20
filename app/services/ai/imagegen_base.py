from abc import ABC, abstractmethod

from app.models.generation import GenerationJob, GenerationResult


class ImageGenerator(ABC):
    """Seam 2: masked inpainting of ONE region of the user's own photo.

    Claude cannot do this — it is not an image-generation model. This seam is
    deliberately provider-agnostic: a diffusion inpainting API takes the source
    photo plus a region mask and returns the edited image. Nothing above this
    interface knows or cares which vendor is behind it.

    Implementations should change only the region named by ``job.region_label``
    and leave the rest of the photo untouched.
    """

    @abstractmethod
    async def generate(self, job: GenerationJob) -> GenerationResult:
        ...
