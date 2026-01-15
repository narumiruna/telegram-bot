# Improvements (Repo Review)

このドキュメントは、この repo を読んで見つかった「改善できそうな点」を、優先度つきで列挙するためのメモです（実装は含みません）。

## P0（早めに手を入れると効く）

1) README のリンク切れを解消
- 現状: `README.md:81` が `CLAUDE.md` を参照しているが、repo 直下に `CLAUDE.md` が存在しない。
- 提案: 参照先を `AGENTS.md` 等の実在ドキュメントに変更、または `CLAUDE.md` を追加して README が期待する情報を移す。

2) MCP 設定ロードの重複とスキーマ不整合を整理
- 現状:
  - `src/bot/callbacks/agent.py:71` に `load_mcp_config()` があり、JSON を「サーバー名 → stdio params」の map として読む。
  - 一方 `src/bot/config.py:13` の `AgentConfig` は `mcp_servers` フィールドを持つモデルで、`config/default.json` の形（map直下）と整合しない。
- 提案:
  - 「サーバーmapスキーマ」を正式スキーマとして `src/bot/config.py` に寄せる（or 逆に default.json を `{"mcp_servers": {...}}` へ寄せる）。

3) Agent の出力送信を `MessageResponse` に統一
- 現状: `src/bot/callbacks/agent.py:330` は `message.reply_text(result.final_output)` を直接呼ぶため、長文で Telegram の制限に当たりやすい（他コールバックは `MessageResponse` を使う）。
- 提案: Agent も `MessageResponse(content=..., parse_mode=...)` 経由で返し、長文は Telegraph に逃がす。

4) URL 内容の埋め込みに上限を設ける（コスト/安定性）
- 現状: `src/bot/callbacks/agent.py:273-277` で URL の本文をそのまま入力に注入しており、巨大ページでプロンプト肥大・遅延・失敗が起きやすい。
- 提案: 文字数/トークン数上限を設けて切り詰める、または「URL→要約→要約を投入」の 2 段階にする。

5) ホワイトリストのパースを一箇所に寄せ、壊れ方を改善
- 現状:
  - `src/bot/bot.py:26-33` が `BOT_WHITELIST` を `int(...)` で直接パースする（不正値で起動時に例外になりうる）。
  - `src/bot/env.py:28-33` に同種ロジックが既にある。
- 提案: `env.get_chat_ids()` を唯一の実装にし、例外時は「無効な ID を無視/ログ」などの挙動を決める。

## P1（中期：品質/運用を底上げ）

6) CI で pre-commit/prek を回す
- 現状: `ruff` / `pytest` / `ty` は走っているが（`.github/workflows/python.yml`）、pre-commit フック一式は CI で検証されていない。
- 提案: CI に `uv run prek run -a` を追加し、ローカルと同じチェックを担保する。

7) GitHub Actions のランナー構成を見直し
- 現状: テスト CI が `macos-latest` 固定（`.github/workflows/python.yml:14`）。一方 publish は `ubuntu-latest`。
- 提案: 主要チェックは `ubuntu-latest` を基準にしつつ、OS 依存箇所があるなら matrix で補う（コスト/速度/再現性のバランス）。

8) エラーレポートの情報量と秘匿を調整
- 現状: `src/bot/callbacks/error.py` は `update` / `chat_data` / `user_data` を Telegraph へ送る。
- 提案: 機微情報（トークン、URL のクエリ、個人情報）が混ざりうる前提で、キーの redact・サイズ上限・送信条件（例: 本番のみ）を明示的にする。

## P2（長期：設計をより強くする）

9) 会話メモリのキー設計を再検討
- 現状: `src/bot/callbacks/agent.py:299-340` は「返信チェーンの message_id」をキーにして履歴を引くため、返信しない通常会話では継続文脈が持ちにくい。
- 提案: chat/thread 単位の “latest state” を別キーで持つ、または「返信時は強い紐付け・通常は chat の直近 N 件」を併用する。

10) 依存関係の “重い機能” を optional 化する
- 現状: `pyproject.toml` に Playwright / Whisper / yt-dlp など重量級依存が常時入っている。
- 提案: extras/依存グループへ分離して、軽量運用（例: 文章系のみ）とフル機能運用を選べるようにする。

## 参考（観測したファイル）

- `README.md:81`（存在しない `CLAUDE.md` 参照）
- `src/bot/config.py:13`（`AgentConfig` と JSON 形のズレ）
- `src/bot/callbacks/agent.py:71`（独自 `load_mcp_config`）、`src/bot/callbacks/agent.py:330`（長文送信）
- `.github/workflows/python.yml:14`（macOS ランナー固定）
- `src/bot/bot.py:26` と `src/bot/env.py:28`（ホワイトリストパース重複）
