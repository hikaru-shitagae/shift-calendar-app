# Renderデプロイガイド

このアプリケーションをRenderにデプロイする手順

## 前提条件
- GitHubリポジトリにコードが push されていること
- Google Cloud Consoleでの認証情報の準備

## デプロイ手順

### 1. Renderアカウントの作成
1. [Render](https://render.com/) にアクセス
2. GitHubアカウントでサインアップ/ログイン

### 2. 新しいWebサービスの作成
1. Renderのダッシュボードで「New +」をクリック
2. 「Web Service」を選択
3. GitHubリポジトリを選択

### 3. サービス設定
- **Name**: `shift-calendar-app` （任意の名前）
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
- **Plan**: `Free`

### 4. 環境変数の設定
「Environment」タブで以下の環境変数を設定：

#### FLASK_SECRET_KEY
- 任意の長いランダム文字列を設定
- 例: `your-very-secret-key-here-make-it-long-and-random`

#### GOOGLE_CREDENTIALS
- `credentials.json` ファイルの内容をそのままコピー
- JSONファイル全体を1行の文字列として設定

```json
{"web":{"client_id":"...","project_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_secret":"...","redirect_uris":["..."]}}
```

### 5. デプロイ
1. 「Create Web Service」をクリック
2. デプロイが完了するまで待機（通常3-5分）

## Google認証の設定更新

Renderでデプロイが完了したら、Google Cloud Consoleで以下を更新：

1. [Google Cloud Console](https://console.cloud.google.com/) にログイン
2. 該当プロジェクトを選択
3. 「認証情報」→「OAuth 2.0 クライアントID」を選択
4. 「承認済みのリダイレクトURI」に以下を追加：
   - `https://your-app-name.onrender.com/oauth2callback`
   - `https://your-app-name.onrender.com/auth/callback`

## トラブルシューティング

### ビルドエラーが発生した場合
- `requirements.txt` の依存関係を確認
- Pythonバージョンの互換性をチェック

### 認証エラーが発生した場合
- `GOOGLE_CREDENTIALS` 環境変数が正しく設定されているか確認
- Google Cloud ConsoleのリダイレクトURIが正しく設定されているか確認

### ログの確認
- Renderのダッシュボードの「Logs」タブでアプリケーションログを確認

## 注意事項
- Renderの無料プランでは、15分間非アクティブ状態が続くとアプリがスリープします
- 初回アクセス時に起動に時間がかかる場合があります
- ファイルアップロード機能は一時的なものです（再起動時にファイルは削除されます）
