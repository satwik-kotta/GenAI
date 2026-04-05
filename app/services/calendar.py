from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.utils.config import get_settings

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _get_credentials() -> Credentials:
    root = Path(__file__).resolve().parents[2]
    token_path = root / "token.json"
    credentials_path = root / "credentials.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def create_event(summary: str, location: str, start_time: str, end_time: str, description: str = "") -> str:
    settings = get_settings()
    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    event_body = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }

    event = (
        service.events()
        .insert(calendarId=settings.google_calendar_id, body=event_body)
        .execute()
    )
    return event.get("htmlLink", "")
