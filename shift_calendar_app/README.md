# 青山がらりシフトカレンダー登録アプリ

Excel ファイルからシフト情報を抽出し、Google カレンダーに自動登録する Flask アプリケーションです。

## 機能

- Excel ファイルからシフト情報を抽出
- Google カレンダーへの自動登録
- 1 日前のリマインダー通知

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Google API 認証設定

1. Google Cloud Console でプロジェクトを作成
2. Google Calendar API を有効化
3. OAuth 2.0 クライアント ID を作成
4. `credentials.json`ファイルをダウンロードしてプロジェクトルートに配置

### 3. 環境変数の設定

```bash
export FLASK_SECRET_KEY='your_secret_key'
```

### 4. アプリケーションの実行

```bash
python app.py
```

## デプロイ

### Render（推奨・無料）

詳細なデプロイ手順は [RENDER_DEPLOY.md](RENDER_DEPLOY.md) を参照してください。

#### 概要

1. [Render](https://render.com/) でアカウント作成
2. GitHub リポジトリを接続
3. 環境変数を設定（`FLASK_SECRET_KEY`, `GOOGLE_CREDENTIALS`）
4. デプロイ実行

### Heroku（有料）

### 1. Heroku CLI のインストール

```bash
# macOS
brew install heroku/brew/heroku

# Windows
# Heroku公式サイトからダウンロード
```

### 2. Heroku にログイン

```bash
heroku login
```

### 3. Heroku アプリの作成

```bash
heroku create your-app-name
```

### 4. 環境変数の設定

```bash
heroku config:set FLASK_SECRET_KEY='your_secret_key'
```

### 5. Google 認証情報の設定

```bash
heroku config:set GOOGLE_CREDENTIALS='$(cat credentials.json)'
```

### 6. デプロイ

```bash
git add .
git commit -m "Initial deployment"
git push heroku main
```

## 使用方法

1. ブラウザでアプリケーションにアクセス
2. 名前を入力
3. Excel ファイルを選択
4. 「Google カレンダーに登録」ボタンをクリック
5. Google 認証を完了
6. シフトがカレンダーに登録されます

## 注意事項

- `credentials.json`ファイルは Git にコミットしないでください
- 本番環境では適切なセキュリティ設定を行ってください
- Google API の利用制限にご注意ください
