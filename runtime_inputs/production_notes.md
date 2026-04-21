# Production Notes

- 朝刊本線は launchd + direct delivery + Codex CLI。Hermes cron は削除済み。
- X は official path を xurl に統一済みだが、live auth 未成立。~/.xurl の client/access token 群は空で、本番朝刊には未接続。
- Grok は Chrome Profile 4 履歴由来の fallback artifact はあるが、会話 JSON の live export は未成立。
- ChatGPT は official export 優先。privacy.openai.com の export request を使う方針。
- 今日の朝刊では local context として、この notes と Hermes 履歴要約を優先して混ぜる。
