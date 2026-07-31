from core.google.client import GoogleApiClient

from googleapiclient.discovery import build

class GoogleCalendarClient(GoogleApiClient):
  SCOPES = ["https://www.googleapis.com/auth/calendar"]

  def __init__(self, refresh_token: str | None = None, **kwargs):
    super().__init__(self.SCOPES, refresh_token=refresh_token, **kwargs)

  def connect(self) -> "GoogleApiClient":
    creds = self._load_credentials()
    if not creds or not creds.valid:
      creds = self._refresh_credentials(creds)
    self._service = build("calendar", "v3", credentials=creds)
    return self
