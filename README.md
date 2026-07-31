# Mail Filter AI

Gmail のメールをローカル LLM で自動分類・要約し、ダッシュボードで管理するシステム。

## 概要

日常的に大量に届くメールの確認・仕分け・返信作業を自動化するためのシステム。Gmail API でメールを定期取得し、**ローカルで動作する LLM**（LM Studio）が各メールを分類・要約・返信文生成まで一気通貫で処理する。処理結果は SQLite に保存され、Next.js 製のダッシュボードから一覧・統計・個別分析・返信送信を操作できる。

ローカル LLM を採用しているため、**メール本文が外部クラウドに送信されることなくプライバシーを保ったまま AI 処理を実現**できる点が特徴。LM Studio のサーバーさえ起動していれば、インターネット接続なしで分類・要約が完結する。設定画面から OpenAI API への切り替えも可能。

### 主な機能

#### メール処理・分析

- **自動分類** — 受信メールを 8 種類のタグ（業務・緊急・迷惑・返信必要など）に自動分類し、即時返信の要否も判定
- **本文要約** — 長文メールを簡潔に要約し、ダッシュボード上でひと目で内容を把握
- **前処理パイプライン** — HTML 除去・署名カット・URL 匿名化など 7 段階のクリーニングでノイズを排除してから分析（詳細は後述の「本文前処理パイプライン」を参照）

#### 返信作成

- **AI 返信文案生成** — メール内容に応じた返信文を LLM が自動生成し、そのまま送信可能
- **返信テンプレート管理** — クライアント別・用途別に複数のテンプレートを保存し、返信フォームのドロップダウンから選んで本文に挿入
- **返信ステータス管理** — 返信を送信すると「返信必要」タグが「返信済み」に自動更新され、対応漏れを防げる
- **音声入力** — 返信フォームでマイクから音声入力し、文字起こしして返信文に反映

#### メール作成・管理

- **新規メール作成・送信** — `/mails/compose` から作成・送信可能。Google People API と連携した宛先候補のオートコンプリート（連絡先チップ選択）に対応
- **添付ファイル表示・ダウンロード** — 添付ファイルの一覧をメール詳細画面に表示し、認証付きダウンロード・ファイルサイズ表示に対応
- **検索・一括削除** — キーワード・タグ・返信要否・日付での絞り込み検索、チェックボックスによるメールの一括削除

#### TODO・カレンダー連携

- **期限抽出・カレンダー連携** — 本文中に含まれる期限・日時を抽出し、Google Calendar に自動登録
- **TODO 管理** — 対応が必要と判断されたメールを TODO として自動登録。タスクボード（ドラッグ&ドロップでステータス変更）、優先度（高 / 中 / 低）設定、完了タスクの削除に対応

#### 通知・自動化

- **Slack 通知** — 要返信メールを検出すると、設定した Slack チャンネルへ自動で通知（詳細は後述の「Slack 通知」を参照）
- **週次メールサマリーレポート** — 直近 7 日間のメール状況を毎週月曜 9:00 に自分の Gmail 宛へ自動送信（詳細は後述の「週次メールサマリーレポート」を参照）
- **定期パイプライン** — APScheduler によるバックグラウンド自動実行（5 分〜1 時間、または無効から選択）で、手動操作なしにメールが常に最新の状態に保たれる

```
Gmail API
   ↓
GmailParser      - raw レスポンス → Mail スキーマに変換（添付ファイルメタデータも取得）
   ↓
Pretreatment     - HTML除去・URL置換・署名カット etc.
   ↓
MailClassifier   - ローカル LLM でタグ分類・要約・返信文生成
   ↓
SQLite (priority.db)
   ↓
FastAPI          - REST API
   ↓
Next.js ダッシュボード
```

## 技術スタック

| レイヤー | 技術 |
|---|---|
| バックエンド | Python / FastAPI / LangChain / APScheduler |
| LLM | LM Studio (`openai/gpt-oss-20b`) ローカル推論、または OpenAI API（設定で切替可） |
| データベース | SQLite (`priority.db`) / SQLAlchemy 2.0 / WAL モード |
| Gmail / 連絡先 連携 | Google Gmail API v1 / People API / Calendar API / OAuth2 |
| 音声入力 | faster-whisper（ローカル音声認識） |
| 通知 | Slack SDK（要返信メール検出時の通知） |
| フロントエンド | Next.js 16 / React 19 / TypeScript / Tailwind CSS v4 |

## ディレクトリ構成

```
Mail_Filter_AI/
├── backend/
│   ├── core/
│   │   ├── api.py                 # FastAPI エントリーポイント
│   │   ├── api_schemas.py         # Pydantic リクエスト/レスポンススキーマ
│   │   ├── enums.py               # タグ・TODOステータス・優先度などのEnum定義
│   │   ├── pipeline.py            # メール処理フロー全体
│   │   ├── classifier.py          # LLM 分類・要約
│   │   ├── scheduler.py           # パイプライン・週次レポートの定期自動実行
│   │   ├── parser.py              # Gmail レスポンス → Mail スキーマ（添付ファイル含む）
│   │   ├── pretreatment.py        # 本文クリーニング
│   │   ├── draft_generator.py     # 返信文案生成
│   │   ├── todo_service.py        # TODO自動作成
│   │   ├── slack.py               # Slack通知クライアント
│   │   ├── weekly_report.py       # 週次メールサマリーレポート生成・送信
│   │   ├── crypto.py              # Fernet 対称暗号（トークン・APIキー保存用）
│   │   ├── llm_schemas.py         # LLM入出力スキーマ定義
│   │   └── google/
│   │       ├── client.py          # Google OAuth2 認証基底クラス
│   │       ├── oauth.py           # OAuth認可フロー
│   │       ├── mail_client.py     # Gmail API クライアント
│   │       ├── calendar_client.py # Google Calendar API クライアント
│   │       ├── people_client.py   # Google People API クライアント（連絡先）
│   │       ├── repository.py      # Gmail / Calendar / 連絡先 リポジトリ
│   │       └── error.py           # 例外定義
│   ├── db/
│   │   ├── engine.py              # SQLAlchemy モデル・DB 設定・マイグレーション
│   │   └── query.py               # DB クエリ関数
│   ├── speech/
│   │   └── transcriber.py         # ローカル音声認識（faster-whisper）
│   └── Dockerfile
├── frontend/
│   └── app/
│       ├── page.tsx               # ダッシュボード画面（検索・統計・メール一覧）
│       ├── _components/
│       │   ├── AppHeader.tsx
│       │   ├── MailSearchBar.tsx      # キーワード/タグ/返信要否/日付フィルタ
│       │   ├── MailListTable.tsx      # メール一覧テーブル（チェックボックス一括削除）
│       │   ├── TodoBoard.tsx          # TODOボード（D&D・優先度・削除）
│       │   ├── TodoPageClient.tsx
│       │   └── AddTodoButton.tsx
│       ├── mails/
│       │   ├── compose/
│       │   │   └── page.tsx           # 新規メール作成（連絡先オートコンプリート）
│       │   └── [id]/
│       │       ├── page.tsx           # メール詳細
│       │       ├── ReplyForm.tsx      # 返信フォーム（音声入力・テンプレート選択対応）
│       │       ├── AttachmentList.tsx # 添付ファイル一覧・ダウンロード
│       │       ├── AnalyzeButton.tsx
│       │       └── DeleteMailButton.tsx
│       ├── settings/
│       │   └── SettingsClient.tsx     # 設定画面（通知タブ含む）
│       ├── todos/                     # TODO管理（ボード・詳細）
│       └── calendar/                  # Google Calendar
└── docker-compose.yml
```

## セットアップ

### 前提条件

- Python 3.12+
- Node.js 20+
- [LM Studio](https://lmstudio.ai/) でローカルサーバーを起動済み（`http://localhost:1234/v1`）
- Google Cloud Console で Gmail API / Calendar API / People API を有効化し、OAuth 2.0 クライアント ID を取得済み

### 環境変数（`.env`）

プロジェクトルートに `.env` を作成する。

```env
# 必須
JWT_SECRET_KEY=<任意の強力なランダム文字列>
ENCRYPTION_KEY=<Fernet キー（python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" で生成）>
GOOGLE_SECRET_KEY=<Google OAuth クライアント ID>
GOOGLE_CLIENT_SECRET=<Google OAuth クライアントシークレット>

# 本番環境では必ず設定
GOOGLE_REDIRECT_URI=https://your-api.example.com/api/v1/auth/google/callback
FRONTEND_URL=https://your-app.example.com
CORS_ORIGINS=https://your-app.example.com

# オプション
LOG_LEVEL=INFO          # DEBUG / INFO / WARNING / ERROR（デフォルト: INFO）
SQL_ECHO=false          # SQLAlchemy クエリログ（デフォルト: false）
LLM_BASE_URL=http://localhost:1234/v1  # LM Studio のエンドポイント
```

### バックエンド

```bash
cd backend
pip install -r requirements.txt

# API サーバー起動（DB テーブル作成・マイグレーションは起動時に自動実行）
uvicorn core.api:app --reload --host 0.0.0.0 --port 8000
# → http://localhost:8000
```

### フロントエンド

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Docker Compose（本番環境）

```bash
# .env を配置してから起動
docker compose up -d
```

`docker-compose.yml` でバックエンド・フロントエンドが自動ビルドされ、`restart: unless-stopped` により異常終了時も自動再起動する。SQLite DB は `./backend/priority.db` にマウントして永続化される。

## API エンドポイント

### メール

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/health` | ヘルスチェック |
| `GET` | `/api/v1/mails` | メール一覧（`q` / `tag` / `needs_reply` / `date_from` / `date_to` / `limit` / `offset` フィルタ付き） |
| `GET` | `/api/v1/mails/{id}` | メール詳細 + AI 評価結果 + 添付ファイル一覧 |
| `DELETE` | `/api/v1/mails/{id}` | メール削除 |
| `POST` | `/api/v1/mails/{id}/analyze` | 単体メールを AI 分析 |
| `POST` | `/api/v1/mails/{id}/reply` | Gmail 返信送信（送信成功時に `replied_at` を記録） |
| `POST` | `/api/v1/mails/{id}/draft` | 返信文案の再生成 |
| `GET` | `/api/v1/mails/{id}/attachments/{att_id}/download` | 添付ファイルをダウンロード（認証必須） |
| `POST` | `/api/v1/mails/send` | 新規メール作成・送信 |

### パイプライン・統計

| メソッド | パス | 説明 |
|---|---|---|
| `POST` | `/api/v1/pipeline/run` | パイプライン手動実行 |
| `GET` | `/api/v1/stats` | ダッシュボード用統計 |

### 設定

| メソッド | パス | 説明 |
|---|---|---|
| `GET/PUT` | `/api/v1/settings/prompt` | AI 分類への追加指示 |
| `GET/PUT` | `/api/v1/settings/pipeline-schedule` | パイプライン自動実行間隔 |
| `GET/PUT` | `/api/v1/settings/llm` | LLM プロバイダ設定（ローカル LM Studio / OpenAI） |
| `GET/PUT` | `/api/v1/settings/slack` | Slack 通知設定（Bot Token・チャンネル ID） |
| `GET/PUT` | `/api/v1/settings/weekly-report` | 週次メールサマリーレポートの自動送信有効/無効 |
| `POST` | `/api/v1/settings/weekly-report/send-now` | 週次レポートを即時送信（テスト用） |
| `GET/POST` | `/api/v1/settings/reply-templates` | 返信テンプレート一覧取得・新規作成 |
| `PUT/DELETE` | `/api/v1/settings/reply-templates/{id}` | 返信テンプレート更新・削除 |

### 連絡先・TODO・音声

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/api/v1/contacts` | Google People API から連絡先一覧を取得 |
| `GET` | `/api/v1/todos` | TODO 一覧 |
| `GET` | `/api/v1/todos/{id}` | TODO 詳細 |
| `POST` | `/api/v1/todos` | TODO 新規作成 |
| `PUT` | `/api/v1/todos/{id}` | TODO 編集（タイトル・詳細・期限・優先度） |
| `PATCH` | `/api/v1/todos/{id}` | TODO ステータス変更 |
| `DELETE` | `/api/v1/todos/{id}` | TODO 削除 |
| `POST` | `/api/v1/speech/transcribe` | 音声ファイルを文字起こし（最大 25 MB） |

### 認証

| メソッド | パス | 説明 |
|---|---|---|
| `POST` | `/api/v1/auth/register` | ユーザー登録 |
| `POST` | `/api/v1/auth/login` | ログイン |
| `GET` | `/api/v1/auth/me` | 現在のユーザー情報 |
| `PUT` | `/api/v1/auth/password` | パスワード変更 |
| `GET` | `/api/v1/auth/google/authorize` | Google OAuth 開始 |
| `GET` | `/api/v1/auth/google/callback` | Google OAuth コールバック |
| `GET/POST/PUT/DELETE` | `/api/v1/calendar/events` | Google Calendar 操作 |

## メールタグ

LLM が各メールを以下の 8 種類に分類する。

| タグ | 説明 |
|---|---|
| 迷惑メール | スパム・不審なメール |
| 業務メール | 業務上の連絡・依頼 |
| 営業メール | 外部からの営業・提案 |
| 個人メール | 私的なやり取り |
| 緊急メール | 即時対応が必要 |
| 返信必要 | 返信を要するメール |
| 対応待ち | 相手の返信待ち |
| 社内メール | 社内からの連絡 |

## AI 分析結果の内容

分類のほか、以下の情報を LLM が生成してデータベースに保存する。

- `summarized_body` — 本文要約
- `needs_immediate_reply` — 即時返信が必要かどうか
- `extracted_deadline` — 本文中の期限日時（Google Calendar に自動登録）
- `ai_response_message` — AI が生成した返信文案
- `reason` — 判定理由
- `should_create_todo` — TODO 自動作成の要否
- `replied_at` — 返信送信日時（送信前は `null`。送信後は「返信必要」タグが「返信済み」表示に切り替わる）

## 通知機能

### Slack 通知

要返信メール（`needs_immediate_reply`）が検出されると、定期パイプライン実行後に設定済みの Slack チャンネルへ自動通知する。Bot Token は OpenAI API キーと同様に Fernet 暗号化して DB に保存され、設定画面（「通知」タブ）からトークン・チャンネル ID を入力するだけで有効化できる。未設定の場合は通知をスキップする。

### 週次メールサマリーレポート

設定画面で有効化すると、毎週月曜 9:00（Asia/Tokyo）に直近 7 日間のメール状況をまとめて自分の Gmail アドレス宛に自動送信する。Google 連携（OAuth）が必須。

レポートに含まれる内容：
- 受信メール数
- 要返信メール数
- 返信済み数
- TODO 自動生成数
- 優先度別の件数

「今すぐ送信（テスト）」ボタンでスケジュールを待たずに即時送信して内容を確認できる。

## 設定機能

設定画面（`/settings`）から以下をカスタマイズできる。

| 設定項目 | 説明 |
|---|---|
| パスワード変更 | アカウントパスワードの変更 |
| Google 連携 | Gmail / Google Calendar / 連絡先（People API）の OAuth 認証 |
| 返信テンプレート | クライアント別・用途別に複数のテンプレートを作成・編集・削除。返信フォームのドロップダウンから選択して本文に挿入できる |
| AI 分類の追加指示 | LLM プロンプトへの補足ルール（例：特定ドメインを社内メールに分類） |
| LLM プロバイダ | ローカル LM Studio / OpenAI API の切り替え、利用モデル指定 |
| パイプライン自動実行 | 5分 / 10分 / 30分（デフォルト）/ 1時間 / 無効 から選択 |
| Slack 通知 | Bot Token・チャンネル ID を設定し、要返信メール検出時の通知有無を切り替え |
| 週次メールサマリーレポート | 自動送信の有効/無効、即時送信（テスト）ボタン |

## 本文前処理パイプライン

LLM に渡す前に以下の順で本文をクリーニングする。

1. HTML タグ除去
2. HTML エンティティデコード（`&amp;` → `&` など）
3. Unicode 正規化（全角英数 → 半角）
4. 引用行除去（`>` 始まり）
5. URL → `[URL]` 置換
6. 署名・罫線以降を除去
7. 余分な空白・空行を正規化

## 本番運用

### APScheduler の信頼性設定

スケジューラは以下のデフォルト設定で全ジョブを管理する。

| 設定 | 値 | 効果 |
|---|---|---|
| `max_instances` | 1 | LLM 処理中でも同一ユーザーのジョブが重複起動しない |
| `coalesce` | True | サーバー停止中の実行漏れをまとめて 1 回だけ実行 |
| `misfire_grace_time` | 300 秒 | 5 分以内の遅延なら実行を試みる |

ジョブのエラー・実行漏れは `EVENT_JOB_ERROR` / `EVENT_JOB_MISSED` リスナーでログに記録される。

### SQLite WAL モード

起動時に全接続へ以下のプラグマを適用する。

| プラグマ | 効果 |
|---|---|
| `journal_mode=WAL` | 複数スレッドからの同時読み書きを許容 |
| `synchronous=NORMAL` | WAL 時の最適なデュラビリティ設定 |
| `foreign_keys=ON` | 外部キー制約を有効化 |

接続タイムアウトは 30 秒。`busy_timeout` により「database is locked」による即時エラーを防ぐ。

### ログ

起動時に `logging.config.dictConfig` でフォーマットを統一する。

```
2025-01-01 09:00:00 [INFO] api.startup: Mail Filter AI 起動完了
2025-01-01 09:05:00 [INFO] scheduler: user@example.com: 3件処理, エラー0件
```

`LOG_LEVEL` 環境変数で `DEBUG` / `INFO` / `WARNING` / `ERROR` を切り替えられる。

## コマンド

```bash
# バックエンド
uvicorn core.api:app --reload --host 0.0.0.0 --port 8000

# フロントエンド
npm run dev

# Docker（本番）
docker compose up -d

# Fernet キー生成
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 今後の課題

- **ローカルLLM推論の速度** — ローカル推論（LM Studio）は環境によっては 20 件（本文サイズはまちまち）の処理に 15〜20 分程度かかることがあり、また推論エラーが返ることもある。そのため実運用では速度と安定性を優先して OpenAI API 切り替えを使うことが多く、「完全ローカルでのプライバシー保護」は設定上は選択可能だが、現状は速度とのトレードオフになっている。軽量モデルへの切り替えやバッチ処理の最適化が今後の課題。
