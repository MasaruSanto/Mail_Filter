# note記事自動生成パイプライン（プロトタイプ）

Web検索によるマルチソースリサーチ → SEO設計（タイトル・ハッシュタグ・見出しへのキーワード配分）→ 構成案 → 執筆 → 推敲チェック、をLangGraphで一気通貫に行うパイプライン。画像生成・note本番投稿は対象外（下書き作成までがスコープ）。

## 全体フロー

```
research      Tavily検索でトピックを複数ソースから調査し、LLMが情報源ごとに
              信頼度・要約・主張(key_claims)を抽出する
   ↓
seo_design    リサーチ結果からメインキーワード・サブキーワード・検索意図・
              想定読者・ハッシュタグ・タイトル候補を設計。
              タイトル候補は文字数/キーワード位置/競合タイトルとの被り具合を
              機械採点し、LLMのクリック誘引度自己採点と合成してスコアリング
   ↓
outline       導入文(冒頭2〜3行のフック)・見出し構成・末尾CTAを生成。
              見出しにサブキーワードを分散配置する
   ↓
draft         構成案に沿って本文をMarkdownで執筆。リサーチノートの主張のみを
              根拠として使うよう指示し、ハルシネーションを抑える
   ↓
review        文字数・導入文のキーワード含有・見出しのキーワード分散を
              機械的にチェックし、warningsとして記録する
```

## セットアップ

```bash
cd backend
pip install -r requirements.txt
```

環境変数（`.env` または直接指定）:

```env
ANTHROPIC_API_KEY=<Claude APIキー>   # provider=claude で使用
TAVILY_API_KEY=<Tavily APIキー>      # リサーチのWeb検索に必須。https://tavily.com/ で取得
```

## 実行

```bash
cd backend/note_article
python main.py "生成AIの業務活用" --provider claude
```

`--provider` は `claude`（デフォルト） / `openai` / `local`（LM Studio）から選択可能。既存のMail Filter AIと同じプロバイダ切り替え方式。

## DB

`note_article.db`（SQLite、本体とは別ファイル）に以下を保存する。

| テーブル | 内容 |
|---|---|
| `topics` | トピック・確定キーワード・検索意図 |
| `research_notes` | 情報源URL・信頼度・要約・主張 |
| `articles` | タイトル・スコア・構成案・本文・ハッシュタグ |
| `article_sources` | 本文中の主張と`research_notes`の紐付け（出典追跡用） |
| `performance` | 投稿後のPV・スキ数など。次回のタイトル・構成生成へのフィードバックに使う想定 |

初回のみテーブル作成:

```bash
python -c "from db.engine import create_tables; create_tables()"
```

## 既知の制約

- **note公式投稿APIは存在しない。** このパイプラインは下書き（`ArticleDraft`）の生成までを担い、実際のnote投稿は手動、または別途ブラウザ自動化を組む前提。事実誤認や著作権侵害のまま自動公開されるリスクを避けるため、投稿前の人間レビューを挟むことを推奨する。
- `performance`テーブルへの実績投入は現状手動（noteに公式APIがないため）。
