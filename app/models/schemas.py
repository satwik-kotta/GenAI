from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    user_input: str = Field(..., description="Natural language planning request")
    city: str | None = Field(default=None, description="City for weather lookup")
    latitude: float | None = Field(default=None, description="Optional latitude for place search")
    longitude: float | None = Field(default=None, description="Optional longitude for place search")
    selected_place_index: int | None = Field(default=None, description="Optional selected place index from place_options")


class PlanReviseRequest(PlanRequest):
    suggestion: str = Field(..., description="User feedback to revise the generated plan")


class IntentRequest(BaseModel):
    user_input: str = Field(..., description="Natural language planning request")


class WeatherRequest(BaseModel):
    city: str = Field(..., description="City name for weather lookup")


class PlacesRequest(BaseModel):
    query: str = Field(..., description="Search keyword for place lookup")
    city: str | None = Field(default=None, description="Optional city used to resolve coordinates when lat/lng are not provided")
    latitude: float | None = Field(default=None, description="Optional latitude for place search")
    longitude: float | None = Field(default=None, description="Optional longitude for place search")


class CalendarEventRequest(BaseModel):
    summary: str = Field(..., description="Event title")
    location: str = Field(..., description="Event location")
    start_time: str = Field(..., description="ISO start datetime")
    end_time: str = Field(..., description="ISO end datetime")
    description: str = Field(default="", description="Optional event description")


class ParsedIntent(BaseModel):
    activity: str
    fallback_activity: str
    weather_condition: str | None = None
    time: str | None = None
    city: str | None = None


class PlaceOption(BaseModel):
    name: str
    address: str | None = None
    rating: float | None = None
    place_type: str | None = None


class ProcessingTraceStep(BaseModel):
    key: str
    label: str
    duration_ms: int


class PlanResponse(BaseModel):
    decision: str
    weather: str
    place: PlaceOption
    calendar_link: str


class PlanPreviewResponse(BaseModel):
    user_input: str
    city: str
    parsed_intent: ParsedIntent
    weather: str
    decision: str
    start_time: str
    end_time: str
    place_options: list[PlaceOption]
    selected_place_index: int = 0
    selected_place: PlaceOption
    trace_steps: list[ProcessingTraceStep] = Field(default_factory=list)


class PlanExecuteResponse(PlanPreviewResponse):
    calendar_link: str


class WeatherResponse(BaseModel):
    city: str
    weather: str


class PlacesResponse(BaseModel):
    query: str
    place_options: list[PlaceOption]


class CalendarEventResponse(BaseModel):
    calendar_link: str


class ApiInfoResponse(BaseModel):
    name: str
    version: str
    endpoints: list[str]


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., description="Google Identity Services ID token")


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture_url: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PlanHistoryItem(BaseModel):
    id: int
    user_input: str
    city: str
    decision: str
    weather: str
    start_time: str
    end_time: str
    selected_place_name: str
    selected_place_address: str | None = None
    selected_place_rating: float | None = None
    calendar_link: str | None = None
    created_at: str


class PlanHistoryResponse(BaseModel):
    total: int
    items: list[PlanHistoryItem]
