# 執筆後の推敲チェック（機械的に判定できるものだけを扱う純粋関数）

_MIN_CHARS = 2000
_MAX_CHARS = 4000


def check_length(body: str, min_chars: int = _MIN_CHARS, max_chars: int = _MAX_CHARS) -> str | None:
  n = len(body)
  if n < min_chars:
    return f"文字数が少なめです（{n}字、目安{min_chars}〜{max_chars}字）"
  if n > max_chars:
    return f"文字数が多めです（{n}字、目安{min_chars}〜{max_chars}字）"
  return None


def check_intro_hook(intro: str, main_keyword: str) -> str | None:
  if main_keyword and main_keyword not in intro:
    return "導入文にメインキーワードが含まれていません"
  return None


def check_heading_keywords(sections, sub_keywords: list[str]) -> str | None:
  if not sub_keywords:
    return None
  covered = sum(1 for kw in sub_keywords if any(kw in s.heading for s in sections))
  if covered == 0:
    return "見出しにサブキーワードが一つも含まれていません"
  return None
