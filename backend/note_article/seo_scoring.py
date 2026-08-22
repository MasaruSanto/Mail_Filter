# タイトルのSEOスコアリング（機械採点部分のみ。純粋関数でテスト容易にしてある）


def score_title_length(title: str, target: int = 32, tolerance: int = 6) -> float:
  """noteの検索結果・プレビューで切れない文字数目安からの乖離が小さいほど高スコア(0-1)"""
  diff = abs(len(title) - target)
  if diff <= tolerance:
    return round(1.0 - (diff / tolerance) * 0.3, 3)
  over = diff - tolerance
  return max(0.0, round(0.7 - over * 0.05, 3))


def score_keyword_position(title: str, main_keyword: str) -> float:
  """メインキーワードがタイトル前方にあるほど高スコア(0-1)。含まれない場合は0"""
  if not main_keyword:
    return 0.0
  idx = title.find(main_keyword)
  if idx == -1:
    return 0.0
  if idx <= 15:
    return 1.0
  if idx <= len(title) // 2:
    return 0.6
  return 0.3


def score_competitor_overlap(title: str, competitor_titles: list[str]) -> float:
  """競合タイトルと文字が被っていないほど高スコア(0-1)。競合情報がなければ1.0"""
  if not competitor_titles:
    return 1.0
  title_chars = set(title)
  if not title_chars:
    return 1.0
  best_overlap = 0.0
  for comp in competitor_titles:
    comp_chars = set(comp)
    if not comp_chars:
      continue
    union = title_chars | comp_chars
    if not union:
      continue
    overlap = len(title_chars & comp_chars) / len(union)
    best_overlap = max(best_overlap, overlap)
  return round(1.0 - best_overlap, 3)


def score_title(title: str, main_keyword: str, competitor_titles: list[str] | None = None,
                 hook_score: float = 0.5) -> dict:
  """タイトル1本を機械採点+LLM採点(hook_score)を合成して総合スコアを出す

  重み: 文字数25% / キーワード位置35% / 競合被り15% / クリック誘引度25%
  （キーワード含有をSEO上最重要視し、次いでクリック誘引度を重視）
  """
  length_s = score_title_length(title)
  keyword_s = score_keyword_position(title, main_keyword)
  overlap_s = score_competitor_overlap(title, competitor_titles or [])
  hook_s = max(0.0, min(1.0, hook_score))
  total = round(length_s * 0.25 + keyword_s * 0.35 + overlap_s * 0.15 + hook_s * 0.25, 3)
  return {
    "length_score": length_s,
    "keyword_score": keyword_s,
    "overlap_score": overlap_s,
    "hook_score": hook_s,
    "total_score": total,
  }
