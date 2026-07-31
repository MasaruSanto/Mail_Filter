from googleapiclient.errors import HttpError

class GoogleApiError(Exception):
  """Google API 共通エラー"""
  def __init__(self, message: str, cause: HttpError):
    detail = str(cause)
    super().__init__(f"{message}: {detail}")
    self.status_code = int(cause.resp.status)
    self.cause = cause

class MailFetchError(GoogleApiError):
  def __init__(self, cause: HttpError):
    super().__init__("メール取得失敗", cause)

class CalendarError(GoogleApiError):
  def __init__(self, cause: HttpError, operation: str = "操作"):
    super().__init__(f"イベント{operation}失敗", cause)

class MailSendError(GoogleApiError):
  def __init__(self, cause: HttpError):
    super().__init__("メール送信失敗", cause)
