# Hermes Pulse

日本語版README / [English README](./README.md)

Hermes Pulse は、Hermes-first で、source-rigorous な personal briefing / operating pipeline です。定期配信にも proactive 配信にも対応し、必要なら専門家レベルまで深掘りできることを目指します。

このリポジトリは、次の 4 ステップを中心に構成します。

1. **Trigger** — cron、feed 更新、polling、webhook、manual run などで実行を開始する
2. **Collect** — その trigger に必要な source だけを収集し、可能なら generic web search より先に known-source retrieval を使う
3. **Compose** — 文脈を briefing / warning / reply draft / expert-depth analysis / action prep にまとめる
4. **Deliver** — 選んだチャネルへ配信するか、次の action 準備まで進める

現時点での主対象 runtime は **Hermes Agent** です。将来的には standalone runtime や他の agent 環境へ広げる余地がありますが、このリポジトリはまず Hermes 向けとして最適化します。

## 全体像

![Hermes Pulse 全体像](./assets/overview-architecture.ja.svg)

## このリポジトリがやること

これは AI ニュース専用のプロダクトではありません。
汎用的な operating briefing engine だが、分野・緊急度・ユーザー理解度に応じて浅くも深くも動ける構造を目指します。
答えるべき問いは次です。

- 今、何が重要か？
- このあと今日の中で何が重要か？
- どの外部変化が、単なる観測ではなく action を要するか？
- 忘れていたもののうち、今 resurfacing すべきものは何か？
- どの source が authoritative で trust できるか？
- ユーザーが指示する前に、どの瞬間なら proactive に動く価値があるか？
- 簡潔な報告で十分なのか、専門家レベルの深い synthesis に上げるべきか？

## コアフロー

runtime としての見え方は、意図的にシンプルです。

### 1. Trigger
定期トリガーも proactive トリガーも、同じパイプラインへ入ります。

例:
- `digest.morning`
- `digest.evening`
- `feed.update`
- `calendar.leave_now`
- `mail.operational`
- `location.arrival`
- `shopping.replenishment`
- `review.trigger_quality`

### 2. Collect
その trigger profile に必要な source だけを取りに行きます。

source family:
- Calendar / Gmail / email
- Notes / docs / local knowledge
- Maps / saved places / location history
- Hermes Agent 会話履歴
- ChatGPT / Grok の履歴（local / export / share / manual で取れる範囲）
- X bookmarks / likes / reverse chronological home timeline（公式X API path として `xurl` を使う）
- 公式ブログ、press room、changelog、research lab、分野特化メディア、専門家ブログなどの RSS / Atom feed
- generic web search より固い探索基盤として使う known-source registry

収集ポリシー:
- primary source first
- 可能なら generic search より前に known-source retrieval
- secondary / tertiary source は discovery 補助には使うが、できるだけ primary evidence まで解決する
- すべての collected item に provenance と citation chain を残す

### 3. Compose
証拠を束ねて relevance を順位付けし、ノイズを抑え、適切な出力を作ります。

出力例:
- digest
- mini_digest
- warning
- nudge
- action_prep
- deep_brief
- source_audit
- reply_draft

優先順位は原則として:
- 未来 relevance
- people overlap
- open loops
- explicit user intent
- source authority と primary confirmation
- その後に external deltas や passive signals

X の内部では:
- `bookmark > like > reverse chronological home timeline`
- `For You` は recommendation 定義で SSOT-grade な acquisition surface ではないため v1 対象外

### 4. Deliver
選んだ runtime / channel へ配信するか、次の action 準備まで進めます。

初期の配信先:
- Hermes Agent の cron 実行
- Hermes の delivery path を通した Slack / Telegram / local files / email summary

## なぜ Hermes-first なのか

この repo は以前、抽象的な briefing pipeline を前面に出していました。
portability 自体は残しますが、入口の主語はそこではありません。

現時点の実用上の主対象は:
- **runtime:** Hermes Agent
- **scheduler:** cron ベース + event trigger
- **形:** trigger → collect → compose → deliver
- **目的:** ユーザーの次の瞬間に実際に役立つ briefing / proactive 通知

## 設計原則

- **Hermes-first runtime target**
- **ドメイン非依存だが expert-depth 可能**
- **primary-source-first retrieval**
- **可能なら generic search より先に known-source retrieval**
- **最小レイヤー**: microservice zoo にしない
- **現実に成立する範囲では live retrieval first**
- **単純な canonical data model**
- **import / 非live source に対する強い provenance と citation chain**
- **user-intent signal は passive signal より強く扱う**
- **depth はユーザー理解度と task に応じて調整する**
- **LLM は圧縮と説明を担うが、source truth の代替ではない**

## docs 一覧

- [`_docs/README.md`](./_docs/README.md)
- [`_docs/01-product-thesis.md`](./_docs/01-product-thesis.md)
- [`_docs/02-system-architecture.md`](./_docs/02-system-architecture.md)
- [`_docs/03-trigger-model.md`](./_docs/03-trigger-model.md)
- [`_docs/04-collection-and-connectors.md`](./_docs/04-collection-and-connectors.md)
- [`_docs/05-synthesis-ranking-and-suppression.md`](./_docs/05-synthesis-ranking-and-suppression.md)
- [`_docs/06-output-delivery-and-actions.md`](./_docs/06-output-delivery-and-actions.md)
- [`_docs/07-state-memory-and-audit.md`](./_docs/07-state-memory-and-audit.md)
- [`_docs/08-roadmap.md`](./_docs/08-roadmap.md)
- [`_docs/09-migration-from-legacy.md`](./_docs/09-migration-from-legacy.md)
- [`_docs/10-appendix-legacy-research.md`](./_docs/10-appendix-legacy-research.md)
- [`_docs/source-notes/conversation-history.md`](./_docs/source-notes/conversation-history.md)
- [`_docs/source-notes/feeds-and-source-registry.md`](./_docs/source-notes/feeds-and-source-registry.md)
- [`_docs/source-notes/x.md`](./_docs/source-notes/x.md)

## 現在の状態

このリポジトリには現在、**scheduled morning / evening digest 用の最小実行 runtime** が入っています。

現時点で実装済み:
- `hermes-pulse morning-digest` CLI エントリポイント
- `hermes-pulse evening-digest` CLI エントリポイント
- `digest.morning.default` の trigger registry
- `digest.evening.default` の trigger registry
- YAML ベースの source registry fixture
- curated connector を束ねる collection orchestrator
- feed registry connector
- known-source-search connector
- Google Calendar connector
- Gmail connector
- `leave-now-warning` event trigger CLI
- `mail-operational` event trigger CLI
- `shopping-replenishment` event trigger CLI
- `feed-update` event trigger CLI
- `location-arrival` event trigger CLI
- `location-walk` event trigger CLI
- `review-trigger-quality` audit CLI
- `gap-window-mini-digest` event trigger CLI
- `feed-update-deep-brief` event trigger CLI
- `feed-update-source-audit` event trigger CLI
- Hermes history / notes の optional local connector
- 日付単位で raw item と Codex 入力を保存する archive writer
- Codex CLI による summarization 経路
- local markdown delivery adapter
- Markdown link を Slack native link に変換し、長文 digest をスレッド分割する Slack direct delivery
- article page が取得できる場合の feed item body enrichment
- `--state-db` による optional local SQLite state logging（trigger runs / deliveries / X signal connector cursors / basic observed source registry state snapshots）
- launchd / direct-delivery helper
- `xurl` を使う official X API signal connector

現在のスコープと未実装:
- runtime はまだ意図的に小さく fixture-friendly な段階
- optional な SQLite state wiring は trigger runs / deliveries / delivered-item suppression history（dismiss / expire / higher-authority supersede 遷移を含む）/ approval/action logs / audit-derived feedback logs / strict な action/suppression command validation / structured execution-details 永続化 / action execution feedback logging / X signal connector cursors / source registry state snapshots（`last_poll_at` / `last_seen_item_ids` / `last_promoted_item_ids` / `authority_tier`）/ source ごとの `last_error` を含む structured な source-registry notes / digest delivery での same-trigger suppression filtering / minimal な suppression dismiss・expiry transition まで入り、deeper な action execution / feedback loop は今後の対象
- legacy な local DB/schema 互換は意図的に維持せず、runtime は current schema 前提
- canonical な CLI flow は現在 morning digest / evening digest / leave-now-warning / mail-operational / shopping-replenishment / feed-update / feed-update-deep-brief / feed-update-source-audit / location-arrival / location-walk / gap-window-mini-digest / review-trigger-quality
- `calendar.leave_now` / `calendar.gap_window` / `mail.operational` / `shopping.replenishment` / `feed.update` / `feed.update.expert_depth` / `feed.update.source_audit` / `location.arrival` / `location.walk` / `review.trigger_quality` は minimal 実装済みで、より深い trigger family は今後の実装対象
- 高頻度な位置通知は、Dawarich のような local_store を 5分おき程度で narrow に poll する `location.walk` を想定し、cooldown / suppression で過通知を防ぐ
- docs は、現実装だけでなくその先の target architecture も引き続き記述している

検証状況:
- `pytest -q` は pass
- 現在のテスト群は CLI / models / registries / collection / Calendar・Gmail・location・audit connector / deep brief・source audit を含む event-trigger rendering / delivery / launchd integration / `xurl` connector をカバー
