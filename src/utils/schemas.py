from pydantic import BaseModel, Field


## Context Understanding Pydantic Classes
class GPSData(BaseModel):
    latitude: float = Field(..., description="Latitude of the restaurant")
    longitude: float = Field(..., description="Longitude of the restaurant")
    description: str = Field(..., description="District of the restaurant location")


class UserBlockInput(BaseModel):
    current_gps: GPSData = Field(..., description="GPS data of the user in car")
    date: str = Field(..., description="Current date in the user situtation in car")
    time: str = Field(..., description="Current time in the user situation in car")
    user_utterance: str = Field(..., description="User utterance for in car navigation")


class OpeningHours(BaseModel):
    monday: str = Field(..., description="Monday opening hours")
    tuesday: str = Field(..., description="Tuesday opening hours")
    wednesday: str = Field(..., description="Wednesday opening hours")
    thursday: str = Field(..., description="Thursday opening hours")
    friday: str = Field(..., description="Friday opening hours")
    saturday: str = Field(..., description="Saturday opening hours")
    sunday: str = Field(..., description="Sunday opening hours")


class SystemBlockInput(BaseModel):
    name: str = Field(..., description="This is the name of the restaurant")
    current_gps: GPSData = Field(..., description="GPS data of the restaurant")
    cost: str = Field(
        ..., description="Cost level of the restaurant (low / medium / high)"
    )
    opening_hours: OpeningHours = Field(
        ..., description="Opening hours for each day of the week"
    )
    cuisine_type: str = Field(
        ...,
        description="The type of cuisine offered by the restaurant, e.g., Italian, French etc.",
    )
    menu: str = Field(
        ...,
        description="Menu information of the restaurant, e.g. Tiramisu, Pizza, Steak etc.",
    )
    rating: float = Field(
        ..., description="Rating of the restaurant from 0 (worst) to 5 (best)"
    )
    distance_km: float = Field(..., description="Kilometers to destination")
    duration_min: int = Field(..., description="Duration in minutes to destination")


class ContextOutput(BaseModel):
    decision: str = Field(
        ...,
        description="Assess whether user block aligns with system block 'true' or whether it does not align 'false'",
    )
    reasoning: str = Field(
        ...,
        description="Give a short reason and explanation why it aligns or why it not aligns",
    )
    error_category: str = Field(
        ...,
        description="Give the category from the following: 'positive', 'location_error', 'time_error', 'cuisine_error', 'cost_error', 'rating_error'",
    )


class ContextOutputRoundtable(BaseModel):
    decision: str = Field(
        ...,
        description="Assess whether user block aligns with system block 'true' or whether it does not align 'false'",
    )
    reasoning: str = Field(
        ...,
        description="Give a short reason and explanation why it aligns or why it not aligns",
    )
    confidence: float = Field(
        ...,
        description="Evaluate your confidence level (between 0.0 and 1.0) to indicate the possibility of your answer being right",
    )
