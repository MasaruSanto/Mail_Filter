import os
from pathlib import Path
from typing import Optional, Any
from abc import ABC, abstractmethod

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


load_dotenv(Path(__file__).parents[3] / ".env")


class GoogleApiClient(ABC):
  """Google API 共通の認証・接続基底クラス (Web OAuth フロー専用)"""

  def __init__(self, scopes, refresh_token: str):
    self._scopes = scopes
    self._refresh_token = refresh_token
    self._service = None
    self.connect()

  @abstractmethod
  def connect(self) -> "GoogleApiClient":
    pass

  def _load_credentials(self) -> Credentials:
    return self._credentials_from_refresh_token(self._refresh_token)

  def _credentials_from_refresh_token(self, refresh_token: str) -> Credentials:
    """DBに保存されたrefresh_tokenからCredentialsを生成してアクセストークンを取得する"""
    creds = Credentials(
      token=None,
      refresh_token=refresh_token,
      token_uri="https://oauth2.googleapis.com/token",
      client_id=os.environ["GOOGLE_SECRET_KEY"],
      client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
      scopes=self._scopes,
    )
    creds.refresh(Request())
    return creds

  def _refresh_credentials(self, creds: Credentials) -> Credentials:
    """アクセストークンをリフレッシュする。失敗した場合は再認証が必要なエラーを送出する"""
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
      return creds
    raise RuntimeError("トークンが無効です。再認証が必要です。")

  @property
  def service(self) -> Optional[Any]:
    if self._service is None:
      raise RuntimeError("connect() を先に呼んでください")
    return self._service
