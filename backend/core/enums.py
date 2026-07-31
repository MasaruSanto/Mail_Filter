from enum import Enum

class TagType(Enum):
  spam = "迷惑メール"
  business = "業務メール"
  sales = "営業メール"
  personal = "個人メール"
  urgent = "緊急メール"
  reply_needed = "返信必要"
  pending = "対応待ち" 
  internal = "社内メール"

class TodoStatus(Enum):
  NOT_STARTED = "未対応"
  IN_PROGRESS = "処理中"
  DONE = "処理済み"
  COMPLETED = "完了"

class TodoPriority(Enum):
  HIGH = "高"
  MEDIUM = "中"
  LOW = "低"