import base64
import sys
import os
from datetime import date

import pytest

# backend/ と backend/core/ をパスに追加
_backend = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_core = os.path.join(_backend, "core")
for _p in (_backend, _core):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.parser import GmailParser
from llm_schemas import Mail

# ---------------------------------------------------------------------------
# テスト用ヘルパー
# ---------------------------------------------------------------------------

def _b64(text: str) -> str:
    """文字列を base64url エンコードして返す（Gmail API 形式）"""
    return base64.urlsafe_b64encode(text.encode()).decode()


def _make_raw(
    headers: list | None = None,
    mime_type: str = "text/plain",
    body_data: str | None = None,
    parts: list | None = None,
) -> dict:
    """Gmail API の messages.get() レスポンスを模したデータを返す"""
    payload: dict = {"mimeType": mime_type}
    if headers is not None:
        payload["headers"] = headers
    else:
        payload["headers"] = []
    if body_data is not None:
        payload["body"] = {"data": body_data}
    else:
        payload["body"] = {}
    if parts is not None:
        payload["parts"] = parts
    return {"payload": payload}


def _header(name: str, value: str) -> dict:
    return {"name": name, "value": value}


def _text_part(mime_type: str, text: str) -> dict:
    return {"mimeType": mime_type, "body": {"data": _b64(text)}}


def _attachment_part(filename: str = "file.pdf") -> dict:
    return {"mimeType": "application/pdf", "filename": filename, "body": {}}


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------

class TestGmailParserParse:

    def setup_method(self):
        self.parser = GmailParser()

    def _standard_headers(self) -> list:
        return [
            _header("From", "山田 太郎 <yamada@example.com>"),
            _header("To", "自分 <me@example.com>"),
            _header("Subject", "テストメール"),
            _header("Date", "Mon, 01 Jan 2024 12:00:00 +0900"),
        ]

    def test_returns_mail_instance(self):
        raw = _make_raw(headers=self._standard_headers(), body_data=_b64("本文"))
        result = self.parser.parse(raw)
        assert isinstance(result, Mail)

    def test_parse_sets_from_name_and_email(self):
        raw = _make_raw(headers=self._standard_headers(), body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.from_name == "山田 太郎"
        assert mail.from_email == "yamada@example.com"

    def test_parse_sets_to_name_and_email(self):
        raw = _make_raw(headers=self._standard_headers(), body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.to_name == "自分"
        assert mail.to_email == "me@example.com"

    def test_parse_sets_title_from_subject(self):
        raw = _make_raw(headers=self._standard_headers(), body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.title == "テストメール"

    def test_parse_sets_day_from_date_header(self):
        raw = _make_raw(headers=self._standard_headers(), body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.day == date(2024, 1, 1)

    def test_parse_sets_has_attachments_false_when_no_attachment(self):
        raw = _make_raw(headers=self._standard_headers(), body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.has_attachments is False

    def test_parse_sets_has_attachments_true_when_attachment_exists(self):
        headers = self._standard_headers()
        raw = _make_raw(
            headers=headers,
            mime_type="multipart/mixed",
            parts=[_text_part("text/plain", "本文"), _attachment_part()],
        )
        mail = self.parser.parse(raw)
        assert mail.has_attachments is True

    def test_parse_from_without_display_name(self):
        """表示名なし・メールアドレスのみの From を正しく処理する"""
        headers = [_header("From", "yamada@example.com")]
        raw = _make_raw(headers=headers, body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.from_email == "yamada@example.com"
        assert mail.from_name is None

    def test_parse_missing_from_header_returns_none(self):
        raw = _make_raw(headers=[], body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.from_name is None
        assert mail.from_email is None

    def test_parse_missing_subject_returns_none(self):
        headers = [_header("From", "yamada@example.com")]
        raw = _make_raw(headers=headers, body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.title is None

    def test_parse_missing_date_returns_none(self):
        headers = [_header("From", "yamada@example.com")]
        raw = _make_raw(headers=headers, body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.day is None

    def test_parse_missing_to_header_returns_none(self):
        headers = [_header("From", "yamada@example.com")]
        raw = _make_raw(headers=headers, body_data=_b64("本文"))
        mail = self.parser.parse(raw)
        assert mail.to_name is None
        assert mail.to_email is None

    def test_parse_multipart_alternative_body(self):
        """multipart メールから本文を正しく抽出する"""
        headers = self._standard_headers()
        raw = _make_raw(
            headers=headers,
            mime_type="multipart/alternative",
            parts=[_text_part("text/plain", "プレーンテキスト本文")],
        )
        mail = self.parser.parse(raw)
        assert mail.body == "プレーンテキスト本文"


# ---------------------------------------------------------------------------
# _extract_headers()
# ---------------------------------------------------------------------------

class TestExtractHeaders:

    def setup_method(self):
        self.parser = GmailParser()

    def test_returns_dict_from_headers_list(self):
        raw = {"payload": {"headers": [
            _header("From", "a@example.com"),
            _header("Subject", "hello"),
        ]}}
        result = self.parser._extract_headers(raw)
        assert result == {"From": "a@example.com", "Subject": "hello"}

    def test_empty_headers_returns_empty_dict(self):
        raw = {"payload": {"headers": []}}
        assert self.parser._extract_headers(raw) == {}

    def test_missing_payload_returns_empty_dict(self):
        assert self.parser._extract_headers({}) == {}

    def test_last_value_wins_for_duplicate_names(self):
        """同名ヘッダーが複数ある場合は後者が優先される"""
        raw = {"payload": {"headers": [
            _header("X-Custom", "first"),
            _header("X-Custom", "second"),
        ]}}
        result = self.parser._extract_headers(raw)
        assert result["X-Custom"] == "second"


# ---------------------------------------------------------------------------
# _extract_body()
# ---------------------------------------------------------------------------

class TestExtractBody:

    def setup_method(self):
        self.parser = GmailParser()

    def test_text_plain_returns_decoded_text(self):
        payload = {"mimeType": "text/plain", "body": {"data": _b64("プレーン本文")}}
        assert self.parser._extract_body(payload) == "プレーン本文"

    def test_text_html_returns_decoded_html(self):
        payload = {"mimeType": "text/html", "body": {"data": _b64("<p>HTML本文</p>")}}
        assert self.parser._extract_body(payload) == "<p>HTML本文</p>"

    def test_multipart_delegates_to_parts(self):
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [_text_part("text/plain", "マルチパート本文")],
        }
        assert self.parser._extract_body(payload) == "マルチパート本文"

    def test_unknown_mime_type_returns_none(self):
        payload = {"mimeType": "application/pdf", "body": {"data": _b64("data")}}
        assert self.parser._extract_body(payload) is None

    def test_empty_body_data_returns_none(self):
        payload = {"mimeType": "text/plain", "body": {}}
        assert self.parser._extract_body(payload) is None

    def test_multipart_with_no_parts_returns_none(self):
        payload = {"mimeType": "multipart/mixed", "parts": []}
        assert self.parser._extract_body(payload) is None


# ---------------------------------------------------------------------------
# _extract_from_parts()
# ---------------------------------------------------------------------------

class TestExtractFromParts:

    def setup_method(self):
        self.parser = GmailParser()

    def test_returns_plain_text_when_available(self):
        parts = [_text_part("text/plain", "プレーン")]
        assert self.parser._extract_from_parts(parts) == "プレーン"

    def test_returns_html_when_no_plain(self):
        parts = [_text_part("text/html", "<b>HTML</b>")]
        assert self.parser._extract_from_parts(parts) == "<b>HTML</b>"

    def test_prefers_plain_over_html(self):
        parts = [
            _text_part("text/html", "<b>HTML</b>"),
            _text_part("text/plain", "プレーン"),
        ]
        assert self.parser._extract_from_parts(parts) == "プレーン"

    def test_plain_with_empty_data_falls_back_to_html(self):
        """text/plain の data が空の場合は text/html を返す"""
        parts = [
            {"mimeType": "text/plain", "body": {}},
            _text_part("text/html", "<p>フォールバック</p>"),
        ]
        assert self.parser._extract_from_parts(parts) == "<p>フォールバック</p>"

    def test_handles_nested_multipart(self):
        nested_parts = [_text_part("text/plain", "ネスト内テキスト")]
        parts = [
            {"mimeType": "multipart/alternative", "parts": nested_parts},
        ]
        assert self.parser._extract_from_parts(parts) == "ネスト内テキスト"

    def test_returns_none_when_no_text_parts(self):
        parts = [_attachment_part()]
        assert self.parser._extract_from_parts(parts) is None

    def test_returns_none_for_empty_parts(self):
        assert self.parser._extract_from_parts([]) is None


# ---------------------------------------------------------------------------
# _decode_data()
# ---------------------------------------------------------------------------

class TestDecodeData:

    def setup_method(self):
        self.parser = GmailParser()

    def test_decodes_ascii_text(self):
        encoded = _b64("hello world")
        assert self.parser._decode_data(encoded) == "hello world"

    def test_decodes_japanese_text(self):
        encoded = _b64("こんにちは！")
        assert self.parser._decode_data(encoded) == "こんにちは！"

    def test_empty_string_returns_none(self):
        assert self.parser._decode_data("") is None

    def test_handles_data_without_padding(self):
        """base64 パディングなしのデータを正しく復号できる"""
        text = "test"
        # パディング文字 = を意図的に除去
        encoded = _b64(text).rstrip("=")
        assert self.parser._decode_data(encoded) == "test"

    def test_decodes_multiline_text(self):
        text = "line1\nline2\nline3"
        encoded = _b64(text)
        assert self.parser._decode_data(encoded) == text


# ---------------------------------------------------------------------------
# _has_attachments()
# ---------------------------------------------------------------------------

class TestHasAttachments:

    def setup_method(self):
        self.parser = GmailParser()

    def test_returns_true_when_part_has_filename(self):
        payload = {"parts": [_attachment_part("report.pdf")]}
        assert self.parser._has_attachments(payload) is True

    def test_returns_false_when_no_filename(self):
        payload = {"parts": [_text_part("text/plain", "本文")]}
        assert self.parser._has_attachments(payload) is False

    def test_returns_false_for_empty_parts(self):
        assert self.parser._has_attachments({}) is False

    def test_detects_nested_attachment(self):
        """ネストした parts 内の添付ファイルも検出する"""
        payload = {
            "parts": [
                {
                    "mimeType": "multipart/mixed",
                    "parts": [_attachment_part("nested.xlsx")],
                }
            ]
        }
        assert self.parser._has_attachments(payload) is True

    def test_returns_false_when_filename_is_empty_string(self):
        """filename が空文字列のパートは添付とみなさない"""
        payload = {"parts": [{"mimeType": "text/plain", "filename": "", "body": {}}]}
        assert self.parser._has_attachments(payload) is False


# ---------------------------------------------------------------------------
# _parse_date()
# ---------------------------------------------------------------------------

class TestParseDate:

    def setup_method(self):
        self.parser = GmailParser()

    def test_parses_rfc2822_date(self):
        result = self.parser._parse_date("Mon, 01 Jan 2024 12:00:00 +0900")
        assert result == date(2024, 1, 1)

    def test_parses_date_with_utc_offset(self):
        result = self.parser._parse_date("Fri, 31 May 2024 09:30:00 +0000")
        assert result == date(2024, 5, 31)

    def test_none_input_returns_none(self):
        assert self.parser._parse_date(None) is None

    def test_invalid_date_string_returns_none(self):
        assert self.parser._parse_date("not-a-date") is None

    def test_empty_string_returns_none(self):
        assert self.parser._parse_date("") is None
