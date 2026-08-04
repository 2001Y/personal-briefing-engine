# STATE: pulse-visual-newspaper
updated: 2026-08-04T18:26:25+09:00

## 目的
既存のHermes Pulse 08:00/14:00/22:00配信を維持し、前日3runを01:10 JSTに日本語の魔法新聞へまとめ、PDFを正本として表紙GIFと本文画像をSlack DM直下へ1メッセージで投稿する。

## 確定事実
- repo: /Users/akitani/.hermes/hermes-pulse
- branch: local/runtime-restore-20260721; worktreeは今回と無関係な既存変更でdirty。
- 現行Pulse job: ea94df458af3 / 0 8,14,22 * * * / hermes_cron_pulse_morning.py / deliver slack:D0AT8A3RB9A。
- 現行Launcher: /Users/akitani/Library/LaunchAgents/run-hermes-pulse-digest-direct-delivery.sh。
- 既存Slack uploader: /Users/akitani/.hermes/scripts/slack_direct.py の upload_files は files.completeUploadExternal を1回呼び、複数ファイルをbatch可能。
- 日本語フォント: macOS /System/Library/Fonts/ヒラギノ明朝 ProN.ttc など。Chromeは /Applications/Google Chrome.app に存在。Hermes venvにPillowとPyMuPDFがある。
- 2026-08-04 morningの実アーカイブを `/Users/akitani/Pulse/HermesPulseMorningSlots/2026-08-04/morning` へsnapshotし、manifestのcompletion_status=completed/source_errors={}をreadbackした。
- fixtureでChrome PDF 2ページ、ordered PNG、8-frame cover.gifを生成し、visual inspectionで日本語欠字・段組み崩れなしを確認した。
- newspaper scriptのpositive dry-runはHTML/PDF/PNG/cover.gifとupload order（cover.gif + page-02.png）を返した。
- 2026-08-03の実データは3slotが揃っていないため、live newspaperはfail-closedで投稿しなかった。
- Cron job `86a175fdf20f` を `10 1 * * *`、script-only、`slack:D0AT8A3RB9A`、`no_agent=true`で作成し、next_run `2026-08-05T01:10:00+09:00`をreadbackした。
- 全suiteは479 passed / 1 failed。失敗は既存dirty変更に関係する `tests/test_state_runtime.py::test_review_trigger_quality_surfaces_stale_inputs_from_runtime_state` で、今回のfocused新聞テストは13 passed。
- 独立reviewのfinding（path confinement、completed snapshot上書き、stale PDF、Slack file数、atomic receipt、Chrome sandbox）を修正し、no-sandbox実renderもPDF 2ページ/GIF生成でreadbackした。

## 決定事項
- 決定: Pulseの通常収集・要約・既存DM投稿は変更せず、各成功run後にslot snapshotを追加する。
- 決定: 前日morning/afternoon/eveningの全3slotがvalidated completedでなければ新聞を投稿しない。
- 決定: HTML/CSSを編集可能なsource、Chrome生成PDFをcanonical artifact、PDFからordered PNGを生成する。
- 決定: Slack rootは表紙GIF（page 1）+本文PNGの画像のみ。thread_tsとinitial_commentは渡さない。
- 決定: ハリー・ポッター固有素材は使わず、オリジナルの魔法新聞風装飾にする。

## Files touched
- src/hermes_pulse/visual_newspaper.py
- scripts/pulse_newspaper_snapshot.py
- scripts/pulse_visual_newspaper.py
- tests/test_visual_newspaper.py
- .hermes/plans/pulse-visual-newspaper/state.md
- host-local wrappers: /Users/akitani/.hermes/scripts/pulse_newspaper_snapshot.py and pulse_visual_newspaper.py
- /Users/akitani/Library/LaunchAgents/run-hermes-pulse-digest-direct-delivery.sh
- Hermes cron job `86a175fdf20f` for the newspaper

## 未解決 / リスク
- Slackのlive GIF表示はworkspace/clientの自動再生設定に依存し、live E2E投稿までは未検証。
- current repoの既存dirty変更は今回のcommitに絶対に含めない。
- pre-push hookのgrepathy補助CLIはdist-test/src/cli.js欠落でNode errorを出したが、git push自体はexit 0でremote SHAをreadback済み。

## 次の一手
1. 2026-08-05 01:10 JSTに、前日3slotが揃う実データでscript-only cronのlive E2E（PDF/GIF生成、Slack DM root batch、receipt）をreadbackする。
2. Slack clientの自動再生設定によるGIF表示差異は、必要なら1回のlive投稿で確認する。
