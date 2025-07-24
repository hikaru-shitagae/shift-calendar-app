# ベースイメージとしてPython 3.9を使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY requirements.txt /app/
COPY app.py /app/
COPY templates /app/templates
COPY public /app/public

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# ポートを公開
EXPOSE 5000

# アプリケーションを起動
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
