"""
Spotify Search + Signup Backend - Flask
XAI 기반 음악 추천 웹사이트 백엔드
기능: 검색 + 회원가입 + 로그인 + 정적 파일 서빙(HTML, 이미지)
완벽한 CORS 설정
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import sqlite3
import hashlib
import re

load_dotenv()

# ===== Flask 앱 설정 (정적 파일 서빙) =====
app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(__file__), 'frontend'),
            static_url_path='')

# ===== CORS 설정 (완벽하게) =====
CORS(app, 
     origins="*",
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=False)

# ===== SQLite 설정 =====
DATABASE = 'auralyze.db'

def get_db():
    """DB 연결"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """DB 초기화 (테이블 생성)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nickname TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            preferred_genre TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Likes 테이블 (좋아요)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            track_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            UNIQUE(user_id, track_id)
        )
    ''')
    
    # Playlists 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Playlist_Tracks 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            track_id TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(playlist_id) REFERENCES playlists(id),
            UNIQUE(playlist_id, track_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 데이터베이스 초기화 완료")

# 비밀번호 해싱
def hash_password(password):
    """비밀번호 SHA256으로 해싱"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """비밀번호 검증"""
    return hash_password(password) == hashed

# ===== Spotify 설정 =====
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', 'YOUR_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', 'YOUR_CLIENT_SECRET')
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1'

# 토큰 캐시
spotify_token = None
token_expiry = None

# ===== Spotify 인증 =====
def get_spotify_token():
    """Spotify API 토큰 획득 (캐시 사용)"""
    global spotify_token, token_expiry
    
    # 토큰이 있고 아직 유효하면 재사용
    if spotify_token and token_expiry and datetime.now() < token_expiry:
        return spotify_token
    
    # 새 토큰 발급
    auth = (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    data = {'grant_type': 'client_credentials'}
    
    try:
        response = requests.post(SPOTIFY_AUTH_URL, auth=auth, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        spotify_token = token_data['access_token']
        
        # 토큰 유효시간: 3600초 (1시간), 안전하게 55분으로 설정
        expires_in = token_data.get('expires_in', 3600)
        token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
        
        print(f"✅ Spotify 토큰 획득 성공")
        return spotify_token
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Spotify 인증 실패: {e}")
        return None

# ===== 정적 파일 서빙 =====
# HTML 파일 서빙
@app.route('/')
def index():
    """로그인 페이지"""
    return app.send_static_file('login.html')

@app.route('/onboarding.html')
def onboarding():
    """온보딩 페이지 (장르 선택)"""
    return app.send_static_file('onboarding.html')

@app.route('/main.html')
def main():
    """메인 페이지"""
    return app.send_static_file('main.html')

# 이미지 서빙
@app.route('/images/<filename>')
def serve_image(filename):
    """frontend/images 폴더에서 이미지 파일 서빙"""
    images_folder = os.path.join(os.path.dirname(__file__), 'frontend', 'images')
    return send_from_directory(images_folder, filename)

# CSS, JS 등 기타 정적 파일
@app.route('/css/<filename>')
def serve_css(filename):
    """CSS 파일 서빙"""
    css_folder = os.path.join(os.path.dirname(__file__), 'frontend', 'css')
    return send_from_directory(css_folder, filename)

@app.route('/js/<filename>')
def serve_js(filename):
    """JavaScript 파일 서빙"""
    js_folder = os.path.join(os.path.dirname(__file__), 'frontend', 'js')
    return send_from_directory(js_folder, filename)

# ===== 회원가입 API =====
@app.route('/api/signup', methods=['POST', 'OPTIONS'])
def signup():
    """
    회원가입 처리
    
    Request:
    {
        "username": "user123",
        "password": "password123",
        "nickname": "닉네임",
        "age": 25,
        "gender": "male",
        "preferred_genre": "pop"  (선택사항)
    }
    
    Response:
    {
        "success": true,
        "message": "회원가입 성공",
        "user_id": 1
    }
    """
    
    try:
        data = request.get_json()
        
        # 필수 필드 확인
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        nickname = data.get('nickname', '').strip()
        age = data.get('age')
        gender = data.get('gender')
        preferred_genre = data.get('preferred_genre', '')
        
        # 검증
        if not username or not password or not nickname:
            return jsonify({"success": False, "message": "필수 정보가 부족합니다"}), 400
        
        if len(username) < 3:
            return jsonify({"success": False, "message": "아이디는 3자 이상이어야 합니다"}), 400
        
        if len(password) < 4:
            return jsonify({"success": False, "message": "비밀번호는 4자 이상이어야 합니다"}), 400
        
        # 아이디 중복 확인
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "이미 사용 중인 아이디입니다"}), 400
        
        # 사용자 생성
        hashed_password = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, password, nickname, age, gender, preferred_genre)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, hashed_password, nickname, age, gender, preferred_genre))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        print(f"✅ 회원가입: {username} (ID: {user_id})")
        
        return jsonify({
            "success": True,
            "message": "회원가입 성공",
            "user_id": user_id
        }), 201
    
    except Exception as e:
        print(f"❌ 회원가입 오류: {e}")
        return jsonify({"success": False, "message": "회원가입 처리 중 오류 발생"}), 500

# ===== 중복확인 API =====
@app.route('/api/check-duplicate', methods=['POST', 'OPTIONS'])
def check_duplicate():
    """
    아이디 중복확인
    
    Request:
    {
        "username": "user123"
    }
    
    Response:
    {
        "available": true,
        "message": "사용 가능한 아이디입니다"
    }
    """
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({"available": False, "message": "아이디를 입력하세요"}), 400
        
        if len(username) < 3:
            return jsonify({"available": False, "message": "아이디는 3자 이상이어야 합니다"}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({
                "available": False,
                "message": "이미 사용 중인 아이디입니다"
            }), 200
        
        conn.close()
        return jsonify({
            "available": True,
            "message": "사용 가능한 아이디입니다"
        }), 200
    
    except Exception as e:
        print(f"❌ 중복확인 오류: {e}")
        return jsonify({"available": False, "message": "오류 발생"}), 500

# ===== 로그인 API =====
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    """
    로그인 처리
    
    Request:
    {
        "username": "user123",
        "password": "password123"
    }
    
    Response:
    {
        "success": true,
        "user_id": 1,
        "nickname": "닉네임",
        "message": "로그인 성공"
    }
    """
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({"success": False, "message": "아이디와 비밀번호를 입력하세요"}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, password, nickname FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"success": False, "message": "아이디가 없습니다"}), 401
        
        if not verify_password(password, user['password']):
            return jsonify({"success": False, "message": "비밀번호가 틀렸습니다"}), 401
        
        print(f"✅ 로그인: {username}")
        
        return jsonify({
            "success": True,
            "user_id": user['id'],
            "nickname": user['nickname'],
            "message": "로그인 성공"
        }), 200
    
    except Exception as e:
        print(f"❌ 로그인 오류: {e}")
        return jsonify({"success": False, "message": "로그인 처리 중 오류 발생"}), 500

# ===== 온보딩 API (장르 선택) =====
@app.route('/api/user/onboarding', methods=['POST', 'OPTIONS'])
def user_onboarding():
    """
    온보딩 완료 (선호 장르 저장)
    
    Request:
    {
        "user_id": 1,
        "favorite_genres": ["K-POP", "Hip-Hop", "R&B", "Pop"]
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        favorite_genres = data.get('favorite_genres', [])
        
        if not user_id:
            return jsonify({"success": False, "message": "user_id 필요"}), 400
        
        # 장르를 JSON 형태로 저장
        genres_json = json.dumps(favorite_genres)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET preferred_genre = ? WHERE id = ?
        ''', (genres_json, user_id))
        conn.commit()
        conn.close()
        
        print(f"✅ 온보딩 완료: user_id={user_id}, genres={favorite_genres}")
        
        return jsonify({
            "success": True,
            "message": "온보딩 완료"
        }), 200
    
    except Exception as e:
        print(f"❌ 온보딩 오류: {e}")
        return jsonify({"success": False, "message": "오류 발생"}), 500

# ===== Spotify 검색 API =====
@app.route('/api/spotify/search', methods=['GET', 'POST', 'OPTIONS'])
def search_spotify():
    """
    Spotify에서 곡 검색
    
    Query Parameters:
    - q: 검색어 (곡 제목 or 아티스트)
    - limit: 결과 개수 (기본값: 10)
    
    Response:
    {
        "success": true,
        "data": [
            {
                "id": "spotify_track_id",
                "title": "곡 제목",
                "artist": "아티스트",
                "album": "앨범명",
                "image": "앨범 이미지 URL",
                "preview_url": "30초 미리듣기 URL",
                "spotify_url": "Spotify 링크",
                "release_date": "2024-01-01"
            }
        ]
    }
    """
    
    # 입력 검증
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not query:
        return jsonify({"success": False, "error": "검색어가 필요합니다"}), 400
    
    if limit > 50:
        limit = 50
    
    # Spotify 토큰 획득
    token = get_spotify_token()
    if not token:
        return jsonify({"success": False, "error": "Spotify 인증 실패"}), 500
    
    # Spotify API 호출
    try:
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'q': query,
            'type': 'track',
            'limit': limit
        }
        
        response = requests.get(
            f'{SPOTIFY_API_URL}/search',
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        spotify_data = response.json()
        tracks = spotify_data.get('tracks', {}).get('items', [])
        
        # 데이터 포맷팅
        formatted_tracks = []
        for track in tracks:
            album_image = None
            if track.get('album', {}).get('images'):
                # 가장 큰 이미지 선택
                album_image = track['album']['images'][0]['url']
            
            formatted_track = {
                'id': track['id'],
                'title': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'image': album_image,
                'preview_url': track.get('preview_url'),  # 30초 미리듣기
                'spotify_url': track['external_urls']['spotify'],
                'release_date': track['album']['release_date'],
                'uri': track['uri'],  # 플레이리스트 추가용
            }
            formatted_tracks.append(formatted_track)
        
        print(f"✅ 검색 성공: '{query}' -> {len(formatted_tracks)}곡")
        
        return jsonify({
            "success": True,
            "count": len(formatted_tracks),
            "data": formatted_tracks
        })
    
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": "요청 시간 초과"}), 504
    except requests.exceptions.RequestException as e:
        print(f"❌ Spotify API 오류: {e}")
        return jsonify({"success": False, "error": "검색 중 오류 발생"}), 500

# ===== 좋아요 API =====
@app.route('/api/likes', methods=['POST', 'OPTIONS'])
def add_like():
    """
    곡을 좋아요 추가
    
    Request:
    {
        "user_id": 1,
        "track_id": "3qm84nBvXo75Y6rAPzlgZl"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        track_id = data.get('track_id')
        
        if not user_id or not track_id:
            return jsonify({"success": False, "message": "필수 정보 부족"}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO likes (user_id, track_id)
                VALUES (?, ?)
            ''', (user_id, track_id))
            conn.commit()
            print(f"✅ 좋아요 추가: user_id={user_id}, track_id={track_id}")
        except sqlite3.IntegrityError:
            # 이미 좋아요 한 경우
            conn.close()
            return jsonify({"success": False, "message": "이미 좋아요 했습니다"}), 400
        
        conn.close()
        return jsonify({"success": True, "message": "좋아요 추가됨"}), 201
    
    except Exception as e:
        print(f"❌ 좋아요 오류: {e}")
        return jsonify({"success": False, "message": "오류 발생"}), 500

@app.route('/api/likes/<int:user_id>', methods=['GET', 'OPTIONS'])
def get_likes(user_id):
    """
    사용자의 좋아요 목록 조회
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT track_id FROM likes WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        likes = [row['track_id'] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            "success": True,
            "likes": likes
        }), 200
    
    except Exception as e:
        print(f"❌ 좋아요 조회 오류: {e}")
        return jsonify({"success": False, "message": "오류 발생"}), 500

@app.route('/api/likes', methods=['DELETE', 'OPTIONS'])
def remove_like():
    """
    좋아요 제거
    
    Request:
    {
        "user_id": 1,
        "track_id": "3qm84nBvXo75Y6rAPzlgZl"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        track_id = data.get('track_id')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM likes WHERE user_id = ? AND track_id = ?
        ''', (user_id, track_id))
        conn.commit()
        conn.close()
        
        print(f"✅ 좋아요 제거: user_id={user_id}, track_id={track_id}")
        
        return jsonify({"success": True, "message": "좋아요 제거됨"}), 200
    
    except Exception as e:
        print(f"❌ 좋아요 제거 오류: {e}")
        return jsonify({"success": False, "message": "오류 발생"}), 500

# ===== 플레이리스트 API =====
@app.route('/api/playlists', methods=['POST', 'OPTIONS'])
def create_playlist():
    """
    플레이리스트 생성
    
    Request:
    {
        "user_id": 1,
        "name": "My Favorites"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name', '').strip()
        
        if not user_id or not name:
            return jsonify({"success": False, "message": "필수 정보 부족"}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO playlists (user_id, name)
            VALUES (?, ?)
        ''', (user_id, name))
        conn.commit()
        playlist_id = cursor.lastrowid
        conn.close()
        
        print(f"✅ 플레이리스트 생성: {name} (ID: {playlist_id})")
        
        return jsonify({
            "success": True,
            "playlist_id": playlist_id,
            "message": f"'{name}' 플레이리스트 생성됨"
        }), 201
    
    except Exception as e:
        print(f"❌ 플레이리스트 생성 오류: {e}")
        return jsonify({"success": False, "message": "오류 발생"}), 500

@app.route('/api/playlists/<int:user_id>', methods=['GET', 'OPTIONS'])
def get_playlists(user_id):
    """
    사용자의 플레이리스트 목록 조회
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, created_at FROM playlists WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        playlists = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            "success": True,
            "playlists": playlists
        }), 200
    
    except Exception as e:
        print(f"❌ 플레이리스트 조회 오류: {e}")
        return jsonify({"success": False, "message": "오류 발생"}), 500

@app.route('/api/playlists/<int:playlist_id>/tracks', methods=['POST', 'OPTIONS'])
def add_track_to_playlist(playlist_id):
    """
    플레이리스트에 곡 추가
    
    Request:
    {
        "track_id": "3qm84nBvXo75Y6rAPzlgZl",
        "track_name": "Dynamite",
        "artist": "BTS"
    }
    """
    try:
        data = request.get_json()
        track_id = data.get('track_id')
        
        if not track_id:
            return jsonify({"success": False, "message": "track_id 필요"}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO playlist_tracks (playlist_id, track_id)
                VALUES (?, ?)
            ''', (playlist_id, track_id))
            conn.commit()
            print(f"✅ 곡 추가: playlist_id={playlist_id}, track_id={track_id}")
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"success": False, "message": "이미 추가된 곡입니다"}), 400
        
        conn.close()
        return jsonify({"success": True, "message": "곡이 추가되었습니다"}), 201
    
    except Exception as e:
        print(f"❌ 곡 추가 오류: {e}")
        return jsonify({"success": False, "message": "오류 발생"}), 500

@app.route('/api/playlists/<int:playlist_id>/tracks', methods=['GET', 'OPTIONS'])
def get_playlist_tracks(playlist_id):
    """
    플레이리스트의 곡 목록 조회
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT track_id FROM playlist_tracks WHERE playlist_id = ?
            ORDER BY added_at DESC
        ''', (playlist_id,))
        
        tracks = [row['track_id'] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            "success": True,
            "tracks": tracks
        }), 200
    
    except Exception as e:
        print(f"❌ 곡 목록 조회 오류: {e}")
        return jsonify({"success": False, "message": "오류 발생"}), 500

# ===== 헬스 체크 =====
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        "status": "OK",
        "message": "서버가 정상 작동 중입니다",
        "timestamp": datetime.now().isoformat()
    })

# ===== 에러 핸들러 =====
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "엔드포인트를 찾을 수 없습니다"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "서버 내부 오류"}), 500

# ===== 메인 =====
if __name__ == '__main__':
    # DB 초기화
    init_db()
    
    print("=" * 60)
    print("🎵 Spotify + Signup + 정적 파일 서빙 시작")
    print("=" * 60)
    print(f"Flask 서버: http://localhost:5000")
    print(f"\n📍 API 엔드포인트:")
    print(f"  - 검색: GET http://localhost:5000/api/spotify/search?q=Dynamite")
    print(f"  - 회원가입: POST http://localhost:5000/api/signup")
    print(f"  - 중복확인: POST http://localhost:5000/api/check-duplicate")
    print(f"  - 로그인: POST http://localhost:5000/api/login")
    print(f"  - 온보딩: POST http://localhost:5000/api/user/onboarding")
    print(f"  - 헬스 체크: GET http://localhost:5000/api/health")
    print(f"\n📁 정적 파일 서빙:")
    print(f"  - HTML: http://localhost:5000/onboarding.html")
    print(f"  - 이미지: http://localhost:5000/images/image.kpop.png")
    print("=" * 60)
    
    # 개발 환경에서 실행 (프로덕션에서는 gunicorn 사용)
    app.run(debug=True, host='0.0.0.0', port=5000)