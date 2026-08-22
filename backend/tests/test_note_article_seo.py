import os
import sys

# backend/ をパスに追加（note_article/ 自体はパスに追加しない。
# 直接追加すると同名の note_article/db パッケージが backend/db（メールDB）と衝突するため）
_backend = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend not in sys.path:
  sys.path.insert(0, _backend)

from note_article.seo_scoring import (score_competitor_overlap, score_keyword_position,
                                       score_title, score_title_length)
from note_article.review import check_heading_keywords, check_intro_hook, check_length
from note_article.schemas import OutlineSection


# ---------------------------------------------------------------------------
# seo_scoring
# ---------------------------------------------------------------------------

def test_score_title_length_within_tolerance_scores_high():
  title = "生成AIで業務効率化する3つの方法【2026年版】"
  assert score_title_length(title, target=len(title), tolerance=6) == 1.0


def test_score_title_length_far_from_target_scores_low():
  short_title = "AI活用術"
  score = score_title_length(short_title, target=32, tolerance=6)
  assert 0.0 <= score < 0.5


def test_score_keyword_position_front_scores_highest():
  assert score_keyword_position("生成AIで業務を効率化する方法", "生成AI") == 1.0


def test_score_keyword_position_absent_scores_zero():
  assert score_keyword_position("業務効率化のコツ", "生成AI") == 0.0


def test_score_keyword_position_late_scores_lower_than_front():
  title = "毎日のルーティンを見直して仕事の生産性を高める生成AI活用法"
  front_score = score_keyword_position("生成AIで仕事の生産性を高める方法", "生成AI")
  late_score = score_keyword_position(title, "生成AI")
  assert late_score < front_score


def test_score_competitor_overlap_no_competitors_scores_full():
  assert score_competitor_overlap("何かのタイトル", []) == 1.0


def test_score_competitor_overlap_identical_title_scores_zero():
  title = "生成AIで業務効率化する方法"
  assert score_competitor_overlap(title, [title]) == 0.0


def test_score_title_combines_all_factors():
  result = score_title(
    "生成AIで業務効率化する3つの方法【2026年版】",
    main_keyword="生成AI",
    competitor_titles=["生成AI活用の基本ガイド"],
    hook_score=0.8,
  )
  assert set(result.keys()) == {
    "length_score", "keyword_score", "overlap_score", "hook_score", "total_score",
  }
  assert 0.0 <= result["total_score"] <= 1.0


def test_score_title_hook_score_is_clamped():
  result = score_title("テストタイトル", main_keyword="テスト", hook_score=1.5)
  assert result["hook_score"] == 1.0


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------

def test_check_length_flags_too_short():
  assert check_length("短い本文") is not None


def test_check_length_flags_too_long():
  assert check_length("あ" * 5000) is not None


def test_check_length_passes_within_range():
  assert check_length("あ" * 3000) is None


def test_check_intro_hook_flags_missing_keyword():
  assert check_intro_hook("この記事では便利な使い方を紹介します", "生成AI") is not None


def test_check_intro_hook_passes_when_keyword_present():
  assert check_intro_hook("生成AIの活用法を紹介します", "生成AI") is None


def test_check_heading_keywords_flags_no_coverage():
  sections = [OutlineSection(heading="はじめに"), OutlineSection(heading="まとめ")]
  assert check_heading_keywords(sections, ["生成AI", "業務効率化"]) is not None


def test_check_heading_keywords_passes_with_coverage():
  sections = [OutlineSection(heading="生成AI導入のステップ"), OutlineSection(heading="まとめ")]
  assert check_heading_keywords(sections, ["生成AI"]) is None


def test_check_heading_keywords_skips_when_no_sub_keywords():
  sections = [OutlineSection(heading="はじめに")]
  assert check_heading_keywords(sections, []) is None
