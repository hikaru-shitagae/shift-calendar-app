from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
import os
from werkzeug.utils import secure_filename
import datetime
import re
import unicodedata
from datetime import datetime, timedelta

# Google API関連
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key')  # セッション用

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
CREDENTIALS_FILE = 'credentials.json'

# 環境変数から認証情報を取得する関数
def get_credentials_file():
    google_credentials = os.environ.get('GOOGLE_CREDENTIALS')
    if google_credentials:
        # 環境変数から認証情報を取得
        import tempfile
        import json
        credentials_data = json.loads(google_credentials)
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(credentials_data, temp_file)
        temp_file.close()
        return temp_file.name
    else:
        # credentials.jsonが見つからない場合のエラーハンドリング
        raise FileNotFoundError("Environment variable 'GOOGLE_CREDENTIALS' is not set.")

# ファイル拡張子チェック
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_hour(shift_str):
    # Lは23時とする
    if 'L' in shift_str:
        return '23'
    m = re.match(r'(\d+)', shift_str)
    return m.group(1) if m else None

def extract_hour_and_minute(shift_str):
    # Lは23:00
    if 'L' in shift_str:
        return '23', '00'
    m = re.match(r'(\d+)(?:\.(\d+))?', shift_str)
    if not m:
        return None, None
    hour = m.group(1)
    minute = '00'
    if m.group(2):
        # 小数点以下を分に変換
        if m.group(2) == '5':
            minute = '30'
        elif m.group(2) == '25':
            minute = '15'
        elif m.group(2) == '75':
            minute = '45'
        else:
            # 例外的な値は0分扱い
            minute = '00'
    return hour, minute

def normalize_shift_string(shift_str):
    import re
    # 全角ハイフンやチルダを半角ハイフンに統一
    shift_str = shift_str.replace('ー', '-').replace('−', '-').replace('―', '-').replace('〜', '-').replace('～', '-').replace('~', '-')
    shift_str = shift_str.replace('‐', '-')  # その他のハイフン類
    # 17:00- → 17-L
    m = re.match(r'^(\d{1,2}):?0{0,2}-$', shift_str)
    if m:
        return f"{m.group(1)}-L"
    # 17:-L → 17-L
    m = re.match(r'^(\d{1,2}):?-L$', shift_str)
    if m:
        return f"{m.group(1)}-L"
    # 17:00-23:L → 17-L
    m = re.match(r'^(\d{1,2}):?0{0,2}-23:?L$', shift_str)
    if m:
        return f"{m.group(1)}-L"
    # 17:00-23:00 → 17-L
    m = re.match(r'^(\d{1,2}):?0{0,2}-23:00$', shift_str)
    if m:
        return f"{m.group(1)}-L"
    # 17:00-22:00 → 17-22
    m = re.match(r'^(\d{1,2}):?0{0,2}-(\d{1,2}):?0{0,2}$', shift_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    # 既に正しい場合
    return shift_str

# Excelのシリアル日付をdatetimeに変換
def excel_date_to_datetime(serial_date):
    """Excelのシリアル日付をdatetimeに変換"""
    base_date = datetime(1899, 12, 30)  # Excelの基準日
    return base_date + timedelta(days=serial_date)

# Google認証フロー開始
@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        get_credentials_file(),
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

# Google認証コールバック
@app.route('/oauth2callback')
def oauth2callback():
    state = session.get('state')
    if not state:
        flash('セッションが切れました。最初からやり直してください。', 'error')
        return redirect(url_for('index'))
    flow = Flow.from_client_secrets_file(
        get_credentials_file(),
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    # refresh_tokenがNoneの場合は古いセッションから引き継ぐ
    refresh_token = credentials.refresh_token
    if not refresh_token and 'credentials' in session:
        refresh_token = session['credentials'].get('refresh_token')
    if not refresh_token:
        flash('Google認証情報が不完全です。アカウント選択画面で必ず「アカウントを選択」し直してください。', 'error')
        return redirect(url_for('index'))
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': refresh_token,
        'token_uri': str(getattr(credentials, 'token_uri', '')),
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    return redirect(url_for('index'))

# Googleカレンダーにイベント登録
def add_shift_to_calendar(credentials_dict, shifts, name):
    creds = Credentials(**credentials_dict)
    service = build('calendar', 'v3', credentials=creds)
    results = []
    print(f"[DEBUG] 登録するシフト一覧: {shifts}")
    for shift in shifts:
        try:
            print(f"[DEBUG] イベント登録開始: {shift}")
            date = shift['date']
            shift_str = shift['shift']
            if '-' in shift_str:
                start_raw, end_raw = shift_str.split('-')
                start_hour, start_minute = extract_hour_and_minute(start_raw)
                end_hour, end_minute = extract_hour_and_minute(end_raw)
                if not start_hour or not end_hour:
                    print(f"[DEBUG] 時間抽出失敗: {shift_str}")
                    continue
                start_time = f"{start_hour}:{start_minute}"
                end_time = f"{end_hour}:{end_minute}"
            else:
                print(f"[DEBUG] スキップ: shift_str={shift_str}")
                continue
            start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            event = {
                'summary': f'青山がらりアルバイト',
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'description': '自動登録されたシフト',
                'colorId': '6',  # タンジェリン（ミカン）色
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {
                            'method': 'popup',
                            'minutes': 1440  # 24時間 = 1440分（1日前）
                        }
                    ]
                }
            }
            print(f"[DEBUG] Google API呼び出し: {event}")
            service.events().insert(calendarId='primary', body=event).execute()
            print(f"[DEBUG] イベント登録成功: {date} {shift_str}")
            results.append({'date': date, 'shift': shift_str, 'status': 'OK'})
        except Exception as e:
            print(f"[DEBUG] イベント登録失敗: {shift}, エラー: {e}")
            flash(f"Googleカレンダー登録エラー: {e}", 'error')
            results.append({'date': shift['date'], 'shift': shift['shift'], 'status': f'エラー: {e}'})
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    shifts = None
    name = ''
    if request.method == 'POST':
        name = request.form.get('name')
        file = request.files.get('shiftfile')
        if not name:
            flash('名前を入力してください', 'error')
        elif not file or file.filename == '':
            flash('Excelファイルを選択してください', 'error')
        elif not allowed_file(file.filename):
            flash('許可されていないファイル形式です', 'error')
        else:
            filename = secure_filename(file.filename or "")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            try:
                df = pd.read_excel(filepath)
                print("[DEBUG] df.columns:", df.columns)
                print("[DEBUG] df.head():\n", df.head())
                print("[DEBUG] 入力された名前:", name)
                # 3列目以降かつ末尾のUnnamed列を除外
                date_columns = df.columns[2:-3]
                print("[DEBUG] date_columns:", date_columns)
                row = df[df[df.columns[1]] == name]
                print("[DEBUG] row:", row)
                if row.empty:
                    flash(f'「{name}」さんのシフトが見つかりません', 'error')
                else:
                    row = row.iloc[0]
                    shifts = []
                    for col in date_columns:
                        shift_value = row[col]
                        if pd.notna(shift_value):
                            shift_str = str(shift_value)
                            shift_str = normalize_shift_string(shift_str)
                            shifts.append({
                                'date': col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col),
                                'shift': shift_str
                            })
                    print(f"[DEBUG] フォームから受け取ったシフト: {shifts}")
                    if 'credentials' not in session:
                        session['pending_shifts'] = shifts
                        session['pending_name'] = name
                        # flash('Google認証が必要です。認証画面に進みます。', 'info')
                        return redirect(url_for('authorize'))
                    results = add_shift_to_calendar(session['credentials'], shifts, name)
                    # 成功したシフトの数をカウント
                    success_count = sum(1 for r in results if r['status'] == 'OK')
                    error_count = len(results) - success_count
                    
                    if success_count > 0:
                        flash('シフトをカレンダーに登録しました！', 'success')
                    if error_count > 0:
                        flash(f'{error_count}件のシフトで登録エラーが発生しました', 'error')
            except Exception as e:
                print(f"[DEBUG] シフト抽出・登録処理で例外: {e}")
                flash(f'エラー: {e}', 'error')
            finally:
                os.remove(filepath)
    if 'pending_shifts' in session and 'credentials' in session:
        shifts = session.pop('pending_shifts')
        name = session.pop('pending_name')
        print(f"[DEBUG] 認証後のpendingシフト登録: {shifts}")
        results = add_shift_to_calendar(session['credentials'], shifts, name)
        # 成功したシフトの数をカウント
        success_count = sum(1 for r in results if r['status'] == 'OK')
        error_count = len(results) - success_count
        
        if success_count > 0:
            flash('シフトをカレンダーに登録しました！', 'success')
        if error_count > 0:
            flash(f'{error_count}件のシフトで登録エラーが発生しました', 'error')
    return render_template('index.html', shifts=shifts, name=name)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)