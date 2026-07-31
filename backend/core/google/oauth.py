import os
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow

load_dotenv(Path(__file__).parents[3] / ".env")

SCOPES = [
  "https://mail.google.com/",
  "https://www.googleapis.com/auth/calendar",
  "https://www.googleapis.com/auth/contacts.readonly",
]

REDIRECT_URI = os.environ.get(
  "GOOGLE_REDIRECT_URI",
  "http://localhost:8000/api/v1/auth/google/callback",
)

def _client_config() -> dict:
  return {
    "web": {
      "client_id": os.environ["GOOGLE_SECRET_KEY"],
      "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "redirect_uris": [REDIRECT_URI],
    }
  }

def get_authorization_url(user_id: str) -> str:
  flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
  flow.redirect_uri = REDIRECT_URI
  url, _ = flow.authorization_url(
      access_type="offline",
      state=user_id,
      prompt="consent",
  )
  return url

def exchange_code(code: str, user_id: str) -> tuple[str | None, str]:
  """認証コードをトークンに交換し (refresh_token, scopes_str) を返す"""
  flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=user_id)
  flow.redirect_uri = REDIRECT_URI
  flow.fetch_token(code=code)
  creds = flow.credentials
  scopes_str = " ".join(creds.scopes) if creds.scopes else " ".join(SCOPES)
  return creds.refresh_token, scopes_str
