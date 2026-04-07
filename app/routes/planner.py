from datetime import datetime
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import PlanHistory, User
from app.models.schemas import (
    ApiInfoResponse,
    AuthResponse,
    CalendarEventRequest,
    CalendarEventResponse,
    GoogleAuthRequest,
    IntentRequest,
    ParsedIntent,
    PlanExecuteResponse,
    PlanHistoryItem,
    PlanHistoryResponse,
    PlanPreviewResponse,
    PlanRequest,
    PlanReviseRequest,
    PlacesRequest,
    PlacesResponse,
    UserResponse,
    WeatherRequest,
    WeatherResponse,
)
from app.services import auth as auth_service
from app.services import calendar, llm, logic, places, weather
from app.utils.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["planner"])


def _raise_stage_error(stage: str, message: str, status_code: int = 500) -> None:
    raise HTTPException(status_code=status_code, detail={"stage": stage, "message": message})


def _build_plan_context(payload: PlanRequest, user_input_override: str | None = None) -> dict:
    settings = get_settings()
    trace_steps: list[dict[str, int | str]] = []

    effective_user_input = user_input_override or payload.user_input

    started_at = perf_counter()
    try:
        parsed = llm.parse_input(effective_user_input)
    except Exception as exc:
        _raise_stage_error("intent", str(exc))
    trace_steps.append(
        {
            "key": "intent",
            "label": "Understanding your request",
            "duration_ms": int((perf_counter() - started_at) * 1000),
        }
    )

    city = payload.city or parsed.city or settings.default_city

    started_at = perf_counter()
    try:
        weather_status = weather.get_weather(city)
    except Exception as exc:
        _raise_stage_error("weather", str(exc))
    trace_steps.append(
        {
            "key": "weather",
            "label": "Checking weather context",
            "duration_ms": int((perf_counter() - started_at) * 1000),
        }
    )

    started_at = perf_counter()
    try:
        final_activity = logic.decide_activity(
            weather_status,
            parsed.activity,
            parsed.fallback_activity,
        )
        start_time, end_time = logic.resolve_time_window(parsed.time)
    except Exception as exc:
        _raise_stage_error("decision", str(exc))
    trace_steps.append(
        {
            "key": "decision",
            "label": "Building recommendation",
            "duration_ms": int((perf_counter() - started_at) * 1000),
        }
    )

    started_at = perf_counter()
    try:
        options = places.get_places(
            final_activity,
            latitude=payload.latitude,
            longitude=payload.longitude,
            city=city,
        )
    except Exception as exc:
        _raise_stage_error("places", str(exc))
    trace_steps.append(
        {
            "key": "places",
            "label": "Finding nearby options",
            "duration_ms": int((perf_counter() - started_at) * 1000),
        }
    )

    if not options:
        _raise_stage_error("places", "No places found for the selected activity", status_code=404)

    requested_index = payload.selected_place_index or 0
    selected_index = requested_index if 0 <= requested_index < len(options) else 0
    selected = options[selected_index]

    return {
        "user_input": payload.user_input,
        "city": city,
        "parsed_intent": parsed,
        "weather": weather_status,
        "decision": final_activity,
        "start_time": start_time,
        "end_time": end_time,
        "place_options": options,
        "selected_place_index": selected_index,
        "selected_place": selected,
        "trace_steps": trace_steps,
    }


@router.get(
    "",
    response_model=ApiInfoResponse,
    summary="API information",
    description="Returns the API name, version, and the list of available endpoints.",
)
def api_info() -> ApiInfoResponse:
    """Describe the public API surface exposed by this backend."""
    return ApiInfoResponse(
        name="AI Day Planner Agent API",
        version="0.1.0",
        endpoints=[
            "GET /health",
            "GET /api/v1",
            "POST /api/v1/intent/parse",
            "POST /api/v1/weather/current",
            "POST /api/v1/places/search",
            "POST /api/v1/plan/preview",
            "POST /api/v1/plan/revise",
            "POST /api/v1/plan/execute",
            "POST /api/v1/calendar/events",
            "POST /api/v1/auth/google",
            "GET /api/v1/auth/me",
            "GET /api/v1/plans/history",
        ],
    )


@router.post(
    "/auth/google",
    response_model=AuthResponse,
    summary="Sign in with Google",
    description=(
        "Verifies a Google Identity Services ID token, creates or updates the user record, "
        "and returns a bearer token for authenticated endpoints."
    ),
)
def google_login(payload: GoogleAuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate a user with Google and issue an application session token."""
    try:
        token_payload = auth_service.verify_google_id_token(payload.id_token)
        user = auth_service.create_or_update_user(db, token_payload)
        session = auth_service.create_session_token(db, user)
        return AuthResponse(
            access_token=session.token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                picture_url=user.picture_url,
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Google authentication failed: {exc}") from exc


@router.get(
    "/auth/me",
    response_model=UserResponse,
    summary="Current user",
    description="Returns the authenticated user's profile using the bearer token from /auth/google.",
)
def auth_me(current_user: User = Depends(auth_service.get_current_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture_url=current_user.picture_url,
    )


@router.post(
    "/intent/parse",
    response_model=ParsedIntent,
    summary="Parse user intent",
    description="Converts free-form user text into structured planning intent using the LLM parser.",
)
def parse_intent(payload: IntentRequest) -> ParsedIntent:
    """Extract activity, fallback activity, city, and time hints from a user's text."""
    try:
        return llm.parse_input(payload.user_input)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/weather/current",
    response_model=WeatherResponse,
    summary="Get current weather",
    description="Fetches the current weather summary for a city using the configured weather provider.",
)
def current_weather(payload: WeatherRequest) -> WeatherResponse:
    """Return the latest weather status for the requested city."""
    try:
        return WeatherResponse(city=payload.city, weather=weather.get_weather(payload.city))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/places/search",
    response_model=PlacesResponse,
    summary="Search nearby places",
    description=(
        "Finds nearby venues for a query using Google Places, ranked and returned as a short list "
        "for the planner UI."
    ),
)
def search_places(payload: PlacesRequest) -> PlacesResponse:
    """Search for nearby place options that match the query and location."""
    try:
        return PlacesResponse(
            query=payload.query,
            place_options=places.get_places(
                payload.query,
                latitude=payload.latitude,
                longitude=payload.longitude,
                city=payload.city,
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/plan/preview",
    response_model=PlanPreviewResponse,
    summary="Preview a plan",
    description=(
        "Runs the full planning pipeline without creating a calendar event. The response includes "
        "parsed intent, weather, recommendation, place options, selection index, and timing traces."
    ),
)
def preview_plan(payload: PlanRequest) -> PlanPreviewResponse:
    """Generate a complete plan preview without saving anything to the calendar."""
    try:
        context = _build_plan_context(payload)
        return PlanPreviewResponse(**context)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/plan/revise",
    response_model=PlanPreviewResponse,
    summary="Revise a plan",
    description=(
        "Regenerates the plan after applying user feedback. Useful when the initial recommendation "
        "needs to be cheaper, quieter, more indoor, or otherwise adjusted."
    ),
)
def revise_plan(payload: PlanReviseRequest) -> PlanPreviewResponse:
    """Regenerate the plan using the original request plus user feedback."""
    try:
        revised_prompt = (
            f"Original request: {payload.user_input}\n"
            f"User feedback: {payload.suggestion}\n"
            "Update the plan using this feedback while keeping it practical and weather-aware."
        )
        context = _build_plan_context(payload, user_input_override=revised_prompt)
        return PlanPreviewResponse(**context)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/plan/execute",
    response_model=PlanExecuteResponse,
    summary="Execute a plan",
    description=(
        "Runs the full planning pipeline, creates a Google Calendar event for the selected place, "
        "and stores the confirmed plan in history. Requires authentication."
    ),
)
@router.post(
    "/plan",
    response_model=PlanExecuteResponse,
    summary="Execute a plan",
    description="Alias for /plan/execute for backward compatibility.",
)
def execute_plan(
    payload: PlanRequest,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
) -> PlanExecuteResponse:
    """Finalize the plan by creating a calendar event and storing a history record."""
    try:
        context = _build_plan_context(payload)
        try:
            event_link = calendar.create_event(
                summary=context["decision"],
                location=context["selected_place"].name,
                start_time=context["start_time"],
                end_time=context["end_time"],
                description=f"Planned by AI agent. Weather in {context['city']}: {context['weather']}",
            )
        except Exception as exc:
            _raise_stage_error("calendar", str(exc))

        db_item = PlanHistory(
            user_id=current_user.id,
            user_input=context["user_input"],
            city=context["city"],
            decision=context["decision"],
            weather=context["weather"],
            start_time=context["start_time"],
            end_time=context["end_time"],
            selected_place_name=context["selected_place"].name,
            selected_place_address=context["selected_place"].address,
            selected_place_rating=context["selected_place"].rating,
            calendar_link=event_link,
        )
        db.add(db_item)
        db.commit()

        return PlanExecuteResponse(**context, calendar_link=event_link)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/calendar/events",
    response_model=CalendarEventResponse,
    summary="Create calendar event",
    description="Creates a Google Calendar event directly from the provided event details.",
)
def create_calendar_event(
    payload: CalendarEventRequest,
    current_user: User = Depends(auth_service.get_current_user),
) -> CalendarEventResponse:
    """Create a single calendar event without running the planner pipeline."""
    _ = current_user
    try:
        return CalendarEventResponse(
            calendar_link=calendar.create_event(
                summary=payload.summary,
                location=payload.location,
                start_time=payload.start_time,
                end_time=payload.end_time,
                description=payload.description,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/plans/history",
    response_model=PlanHistoryResponse,
    summary="Plan history",
    description="Returns the most recent confirmed plans for the authenticated user.",
)
def plan_history(
    limit: int = 20,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
) -> PlanHistoryResponse:
    """Return the authenticated user's saved plan history."""
    safe_limit = max(1, min(limit, 100))
    query = (
        db.query(PlanHistory)
        .filter(PlanHistory.user_id == current_user.id)
        .order_by(PlanHistory.created_at.desc())
    )
    items = query.limit(safe_limit).all()
    total = query.count()

    return PlanHistoryResponse(
        total=total,
        items=[
            PlanHistoryItem(
                id=item.id,
                user_input=item.user_input,
                city=item.city,
                decision=item.decision,
                weather=item.weather,
                start_time=item.start_time,
                end_time=item.end_time,
                selected_place_name=item.selected_place_name,
                selected_place_address=item.selected_place_address,
                selected_place_rating=item.selected_place_rating,
                calendar_link=item.calendar_link,
                created_at=item.created_at.isoformat() if isinstance(item.created_at, datetime) else str(item.created_at),
            )
            for item in items
        ],
    )