from datetime import datetime

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


def _build_plan_context(payload: PlanRequest) -> dict:
    settings = get_settings()

    parsed = llm.parse_input(payload.user_input)
    city = payload.city or parsed.city or settings.default_city
    weather_status = weather.get_weather(city)

    final_activity = logic.decide_activity(
        weather_status,
        parsed.activity,
        parsed.fallback_activity,
    )

    options = places.get_places(
        final_activity,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    if not options:
        raise HTTPException(status_code=404, detail="No places found for the selected activity")

    selected = options[0]
    start_time, end_time = logic.resolve_time_window(parsed.time)

    return {
        "user_input": payload.user_input,
        "city": city,
        "parsed_intent": parsed,
        "weather": weather_status,
        "decision": final_activity,
        "start_time": start_time,
        "end_time": end_time,
        "place_options": options,
        "selected_place": selected,
    }


@router.get("", response_model=ApiInfoResponse)
def api_info() -> ApiInfoResponse:
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
            "POST /api/v1/plan/execute",
            "POST /api/v1/calendar/events",
            "POST /api/v1/auth/google",
            "GET /api/v1/auth/me",
            "GET /api/v1/plans/history",
        ],
    )


@router.post("/auth/google", response_model=AuthResponse)
def google_login(payload: GoogleAuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
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


@router.get("/auth/me", response_model=UserResponse)
def auth_me(current_user: User = Depends(auth_service.get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture_url=current_user.picture_url,
    )


@router.post("/intent/parse", response_model=ParsedIntent)
def parse_intent(payload: IntentRequest) -> ParsedIntent:
    try:
        return llm.parse_input(payload.user_input)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/weather/current", response_model=WeatherResponse)
def current_weather(payload: WeatherRequest) -> WeatherResponse:
    try:
        return WeatherResponse(city=payload.city, weather=weather.get_weather(payload.city))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/places/search", response_model=PlacesResponse)
def search_places(payload: PlacesRequest) -> PlacesResponse:
    try:
        return PlacesResponse(
            query=payload.query,
            place_options=places.get_places(
                payload.query,
                latitude=payload.latitude,
                longitude=payload.longitude,
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/plan/preview", response_model=PlanPreviewResponse)
def preview_plan(payload: PlanRequest) -> PlanPreviewResponse:
    try:
        context = _build_plan_context(payload)
        return PlanPreviewResponse(**context)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/plan/execute", response_model=PlanExecuteResponse)
@router.post("/plan", response_model=PlanExecuteResponse)
def execute_plan(
    payload: PlanRequest,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
) -> PlanExecuteResponse:
    try:
        context = _build_plan_context(payload)
        event_link = calendar.create_event(
            summary=context["decision"],
            location=context["selected_place"].name,
            start_time=context["start_time"],
            end_time=context["end_time"],
            description=f"Planned by AI agent. Weather in {context['city']}: {context['weather']}",
        )

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


@router.post("/calendar/events", response_model=CalendarEventResponse)
def create_calendar_event(
    payload: CalendarEventRequest,
    current_user: User = Depends(auth_service.get_current_user),
) -> CalendarEventResponse:
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


@router.get("/plans/history", response_model=PlanHistoryResponse)
def plan_history(
    limit: int = 20,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
) -> PlanHistoryResponse:
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