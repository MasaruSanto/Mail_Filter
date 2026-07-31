#メール本文の前処理を管理するクラス。

import re
import unicodedata
from html.parser import HTMLParser

_SKIP_TAGS = frozenset({"style", "script", "head"})
# 開始タグで改行を挿入するブロック要素
_BLOCK_TAGS = frozenset({"p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"})

class _HTMLStripper(HTMLParser):
  def __init__(self):
    super().__init__()
    self._parts: list[str] = []
    self._skip = False

  def handle_starttag(self, tag: str, attrs) -> None:
    if tag in _SKIP_TAGS:
      self._skip = True
    elif tag == "br" or tag in _BLOCK_TAGS:
      self._parts.append("\n")

  def handle_endtag(self, tag: str) -> None:
    if tag in _SKIP_TAGS:
      self._skip = False
    elif tag in _BLOCK_TAGS:
      self._parts.append("\n")

  def handle_data(self, data: str) -> None:
    if not self._skip:
      self._parts.append(data)

  def get_text(self) -> str:
    return "".join(self._parts)

class Pretreatment:

  def process(self, body: str | None) -> str:
    if not body:
      return ""
    text = self._strip_html(body)
    text = self._decode_entities(text)
    text = self._normalize_unicode(text)
    text = self._remove_quoted_lines(text)
    text = self._remove_urls(text)
    text = self._remove_signature(text)
    text = self._normalize_whitespace(text)
    return text

  # --- private helpers ---

  def _strip_html(self, text: str) -> str:
    F = re.DOTALL | re.IGNORECASE
    # style/script/head ブロックを除去
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=F)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=F)
    text = re.sub(r"<head[^>]*>.*?</head>", "", text, flags=F)
    # HTMLコメント（<!--[if mso]>...など条件付きコメントも含む）を除去
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # HTMLパーサーでテキストノードを抽出
    stripper = _HTMLStripper()
    stripper.feed(text)
    result = stripper.get_text()
    # パーサーで取り切れなかったタグをフォールバック除去
    result = re.sub(r"<[^>]+>", " ", result)
    # @media/@keyframes などCSSアットルール（ネスト1段階まで）
    result = re.sub(r"@[\w-]+[^{]*\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}", " ", result, flags=re.DOTALL)
    # 残ったCSSブロック { ... }（複数行対応）
    result = re.sub(r"\{[^{}]*\}", " ", result, flags=re.DOTALL)
    # CSS プロパティ行（例: color: red; / font-size: 14px;）
    result = re.sub(r"^\s*[\w-]+\s*:\s*[^;\n]{1,200};\s*$", "", result, flags=re.MULTILINE)
    return result

  def _decode_entities(self, text: str) -> str:
    # &amp; &nbsp; などのHTMLエンティティを通常文字に戻す
    """
    _HTMLStripper の役割は「HTMLの構造（タグ）を取り除いてテキストを取り出す」ことだけです。
     エンティティのデコードはHTMLの構造解析とは別の処理なので、Pretreatment 側のパイプラインに置きました。
     2. HTML以外の入力にも対応するため
    process() のパイプラインはどんな入力にも順番に適用されます。
    もし body がHTMLではなくプレーンテキストで &amp; が含まれていた場合、_strip_html を通ってもエンティティは残ります。
    _decode_entities を独立したステップにしておくことで、HTML・非HTML問わず確実にデコードできます。
    """
    import html
    return html.unescape(text)

  def _normalize_unicode(self, text: str) -> str:
    # 全角英数字・記号を半角に統一（NFKC正規化）
    return unicodedata.normalize("NFKC", text)

  def _remove_quoted_lines(self, text: str) -> str:
    # 返信時の引用行（> で始まる行）を除去
    lines = text.splitlines()
    filtered = [l for l in lines if not re.match(r"^\s*>", l)]
    return "\n".join(filtered)

  def _remove_urls(self, text: str) -> str:
    # URLをプレースホルダーに置換してノイズを減らす
    return re.sub(r"https?://\S+", "[URL]", text)

  def _remove_signature(self, text: str) -> str:
    # -- / 以上 / 罫線などの署名区切り以降を除去
    pattern = r"(\n[ \t]*--[ \t]*\n|\n以上\n|\n[-ーｰ─━]{3,})"
    match = re.search(pattern, text)
    if match:
      text = text[: match.start()]
    return text

  def _normalize_whitespace(self, text: str) -> str:
    # 行頭・行末のスペース除去 → 空白のみの行を空行に統一
    lines = [l.strip() for l in text.splitlines()]
    # 連続する空行をすべて1行に潰す
    result: list[str] = []
    prev_blank = False
    for line in lines:
      if line == "":
        if not prev_blank:
          result.append("")
        prev_blank = True
      else:
        result.append(line)
        prev_blank = False
    return "\n".join(result).strip()


if __name__ == "__main__":
  sample = """
  <html><body>
  <p>お世話になっております。<br>山田と申します。</p>
  <p>詳細はこちら: https://example.com/detail?id=123</p>
  <p>&amp;nbsp; ＡＢＣ１２３</p>
  </body></html>
  > 2024/01/01 に 鈴木さんが書きました:
  > よろしくお願いします。
  以上
  山田 太郎
  株式会社サンプル
  """

  p = Pretreatment()
  result = p.process(sample)
  print("=== 前処理結果 ===")
  print(result)
