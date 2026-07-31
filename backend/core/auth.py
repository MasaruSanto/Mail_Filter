import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from dotenv import load_dotenv


load_dotenv() # .envファイルから環境変数を読み込みます


SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
  raise RuntimeError("JWT_SECRET_KEY が設定されていません（.env を確認してください）")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24時間
OAUTH_STATE_EXPIRE_MINUTES = 10

def hash_password(password: str) -> str:
  return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
  return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


def create_access_token(user_id: str) -> str:
  expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str:
  """JWTトークンを検証してuser_idを返す。無効な場合はJWTErrorを送出する"""
  payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
  user_id: str | None = payload.get("sub")
  if user_id is None:
    raise JWTError("sub missing")
  return user_id


def create_oauth_state_token(user_id: str) -> str:
  """Google OAuth の state 用に短命の署名付きトークンを発行する（CSRF対策）"""
  expire = datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_EXPIRE_MINUTES)
  return jwt.encode(
    {"sub": user_id, "exp": expire, "purpose": "google_oauth_state"},
    SECRET_KEY,
    algorithm=ALGORITHM,
  )


def decode_oauth_state_token(token: str) -> str:
  """state トークンを検証してuser_idを返す。無効・期限切れはJWTErrorを送出する"""
  payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
  if payload.get("purpose") != "google_oauth_state":
    raise JWTError("invalid state purpose")
  user_id: str | None = payload.get("sub")
  if user_id is None:
    raise JWTError("sub missing")
  return user_id
