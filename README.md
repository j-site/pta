# PTA経理 レシート自動記帳システム

レシートを紙に貼ってA4用紙に手書き記帳する作業を、LINEで写真を送るだけで
自動仕分け・自動記帳できる仕組みに置き換えるためのプロジェクトです。

## 構成

```
教頭先生（LINEアプリ）
  → レシート写真を送信
  → LINE公式アカウント（Messaging API、応答メッセージは無料無制限）
  → Google Apps Script（doPost Webhookで受信）
  → Gemini API（gemini-2.5-flash、無料枠内）で画像解析
  → Google スプレッドシートに自動記帳
  → 元画像は Google ドライブに保存
  → LINEに「記帳しました」と返信
```

すべて無料枠のみで完結する構成です（LINE返信メッセージ無料、GAS/Sheets/Drive無料、
Gemini API無料枠）。PTA規模の利用量なら課金なしで継続可能ですが、各社の無料枠条件は
将来変更されうるため、定期的な見直しを推奨します。

## ファイル構成

- `src/Code.gs` — Google Apps Script本体（LINE Webhook受信、Gemini解析、記帳、返信）
- `src/appsscript.json` — Apps Scriptのマニフェスト
- `docs/導入ガイド.docx` — 非エンジニア向けの導入手順書

## セットアップ概要

1. Googleスプレッドシート・ドライブフォルダを用意する
2. LINE公式アカウント（Messaging API）を開設し、チャネルアクセストークンを取得する
3. Gemini APIキーを取得する（Google AI Studio）
4. `src/Code.gs` の内容をGoogleスプレッドシートに紐づくApps Scriptエディタへ貼り付ける
5. スクリプトプロパティに `LINE_CHANNEL_ACCESS_TOKEN` / `GEMINI_API_KEY` / `SHEET_ID` / `DRIVE_FOLDER_ID` を設定する
6. `checkSettings()` → `setupSheet()` を手動実行して疎通確認・シート初期化する
7. ウェブアプリとしてデプロイし、発行されたURLをLINEのWebhook URLに設定する

詳細な手順は `docs/導入ガイド.docx` を参照してください。

## セキュリティ上の注意

Google Apps Scriptの `doPost(e)` はHTTPリクエストヘッダーを取得できないため、
LINEの署名検証（X-Line-Signature）は実装できません。Web AppのURLを第三者に
開示しないことに加え、読み取り結果の信頼度が低い場合は `needs_review` フラグを
立ててスプレッドシート上で人が最終確認する運用を前提としています。
