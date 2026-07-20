from pydantic import BaseModel, Field


class VehicleGuess(BaseModel):
    """Structured result of the vehicle-recognition seam.

    This is also the schema handed to Claude as ``output_format`` in the real
    implementation, so any change here changes the model contract.
    """

    make: str = Field(description="Марка автомобиля, например Chevrolet")
    model: str = Field(description="Модель автомобиля, например Malibu")
    year: int = Field(description="Примерный год выпуска, например 2023")
    confidence: float = Field(
        default=0.0, description="Уверенность распознавания от 0 до 1"
    )


class RecognizeRequest(BaseModel):
    photo_id: str


class CarCorrection(BaseModel):
    make: str
    model: str
    year: int


class VehicleResponse(BaseModel):
    make: str
    model: str
    year: int
    confidence: float
    label: str
    compatible_categories: list[str]
