# personal-briefing-engine

日本語版README / [English README](./README.md)

agent 非依存の personal operating briefing engine です。

このリポジトリは、本来別々に設計すべきではない 2 つを統合して定義します。

1. **朝刊・夕刊のような定期ブリーフィング**
2. **位置変化・leave-now・運用メール・補充購入などのイベント駆動トリガー**

このプロジェクトは **Hermes 専用ではありません**。Hermes Agent は強力な runtime 例のひとつですが、コア設計は standalone daemon / CLI や他の agent runtime でも成立することを前提にしています。

## 全体像

![personal-briefing-engine 全体像](./assets/overview-architecture.ja.svg)

## プロダクト仮説

これは単なる AI ニュース要約アプリではありません。
このプロジェクトが目指しているのは、**個人向けの operating system for attention and action** です。

答えるべき問いは次です。

- 今、何が重要か？
- このあと今日の中で何が重要か？
- 次に会う人について、何を思い出すべきか？
- 外部で何が変わったか、そのうち本当に relevant なのは何か？
- 忘れていたもののうち、今 resurfacing すべきものは何か？
- ユーザーが指示する前に、どの瞬間なら proactive に動く価値があるか？

## トップレベルの構造

システム全体は 1 本の A-F パイプラインで動きます。

1. **Trigger events** — 定期またはイベント駆動の trigger が `TriggerEvent` を作る
2. **Collection** — その trigger profile に必要な source だけを取りに行く
3. **Synthesis / ranking / suppression** — 情報を束ね、順位付けし、ノイズを抑える
4. **Output generation** — digest / warning / nudge / action-prep に整形する
5. **Delivery / action execution** — 送る、または副作用を伴う行動の直前まで進める
6. **State / memory / audit** — cursor, delivery history, approval, feedback を保持する

つまり、朝刊夕刊は**別エンジンではなく scheduled trigger profile** です。

## Trigger family

### 定期トリガー
- `digest.morning`
- `digest.evening`
- `review.trigger_quality`

### イベント駆動トリガー
- `location.arrival`
- `location.dwell`
- `location.area_change`
- `calendar.leave_now`
- `calendar.gap_window`
- `mail.operational`
- `shopping.replenishment`
- 将来的には `interest.watch`, `price.drop`, `reservation.change`

## Source family

### 運用コンテキスト
- Calendar
- Gmail / email
- Notes / docs
- Maps / saved places
- Location history（たとえば Dawarich）

### agent 会話履歴
- Hermes Agent
- ChatGPT
- Grok

### social / memory source
- X home timeline diff
- X bookmarks
- X likes
- 将来的には Google Photos, Instagram, blog/RSS, commerce/order history

## 設計原則

- **agent-agnostic core**
- **最小レイヤー**: microservice zoo にしない
- **live retrieval first**
- **単純な canonical data model**
- **import / 非live source に対する強い provenance**
- **user-intent signal は passive signal より強く扱う**
- **LLM は圧縮と説明を担うが、source truth の代替ではない**

## X / Twitter の位置づけ

X は重要ですが、このプロジェクト全体そのものではありません。

優先順位は原則として次のままです。

- 未来 relevance
- people overlap
- open loops
- saved intent
- その後に external deltas

X の内部では:
- `bookmark > like > home timeline diff`

home timeline diff は **価値は高いがノイジーな novelty source** として扱い、relevance と quota を通った時だけ出力へ入れます。

## docs 一覧

- [`_docs/README.md`](./_docs/README.md)
- [`_docs/01-product-thesis.md`](./_docs/01-product-thesis.md)
- [`_docs/02-system-architecture.md`](./_docs/02-system-architecture.md)
- [`_docs/03-trigger-model.md`](./_docs/03-trigger-model.md)
- [`_docs/04-collection-and-connectors.md`](./_docs/04-collection-and-connectors.md)
- [`_docs/05-synthesis-ranking-and-suppression.md`](./_docs/05-synthesis-ranking-and-suppression.md)
- [`_docs/06-output-delivery-and-actions.md`](./_docs/06-output-delivery-and-actions.md)
- [`_docs/07-state-memory-and-audit.md`](./_docs/07-state-memory-and-audit.md)
- [`_docs/source-notes/x.md`](./_docs/source-notes/x.md)
- [`_docs/source-notes/conversation-history.md`](./_docs/source-notes/conversation-history.md)
- [`_docs/08-roadmap.md`](./_docs/08-roadmap.md)
- [`_docs/09-migration-from-legacy.md`](./_docs/09-migration-from-legacy.md)
- [`_docs/10-appendix-legacy-research.md`](./_docs/10-appendix-legacy-research.md)

## 現在の状態

このリポジトリは現在、**planning / architecture repository** です。
主に記述しているのは:
- 統合された system model
- source acquisition の制約
- ranking / suppression policy
- state / audit 要件
- 将来の実装ロードマップ

まだ production implementation を主張するものではありません。
