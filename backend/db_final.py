"""
Auralyze Database Schema v2.0 - 호환성 버전
Transformer 기반 인디곡 추천 시스템

✅ 기존 DB와 100% 호환
✅ timestamp 필드 유지 (기존과 동일)
✅ 기존 데이터 손실 없음
✅ 추가 기능만 더함

변경사항:
- listening_history 제거 ❌
- track_pair_stats 제거 ❌
- track_cooccurrence 추가 ✅
- audio_features 확장 ✅
"""

import sqlite3

DATABASE = 'auralyze.db'

def get_db():
    """DB 연결"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """데이터베이스 초기화"""
    conn = get_db()
    cursor = conn.cursor()
    
    print("=" * 70)
    print("🎵 Auralyze Database v2.0 초기화 시작 (호환성 버전)")
    print("=" * 70)
    
    # ============================================
    # 기존 테이블 (v1.0과 완전 동일) ✅
    # ============================================
    
    # 1. Users 테이블 - timestamp 필드 유지!
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
    print("✅ users 테이블 생성 (기존 호환)")
    
    # 2. Likes 테이블 - timestamp 필드 유지!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            track_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, track_id)
        )
    ''')
    print("✅ likes 테이블 생성 (기존 호환)")
    
    # 3. Playlists 테이블 - timestamp 필드 유지!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    print("✅ playlists 테이블 생성 (기존 호환)")
    
    # 4. Playlist_Tracks 테이블 - timestamp 필드 유지!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            track_id TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
            UNIQUE(playlist_id, track_id)
        )
    ''')
    print("✅ playlist_tracks 테이블 생성 (기존 호환)")
    
    # 5. Tracks 테이블 - timestamp 필드 유지!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            album TEXT,
            image TEXT,
            preview_url TEXT,
            spotify_url TEXT,
            uri TEXT,
            release_date TEXT,
            duration_ms INTEGER,
            popularity INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ tracks 테이블 생성 (기존 호환)")
    
    # 6. Audio_Features 테이블 - 확장 + timestamp 유지!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audio_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT NOT NULL UNIQUE,
            danceability REAL,
            energy REAL,
            valence REAL,
            tempo REAL,
            acousticness REAL,
            instrumentalness REAL,
            speechiness REAL,
            liveness REAL,
            loudness REAL,
            key INTEGER,
            mode INTEGER,
            time_signature INTEGER,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
        )
    ''')
    print("✅ audio_features 테이블 생성 (확장 버전)")
    
    # ============================================
    # 신규 테이블 (v2.0 전용) ✅
    # ============================================
    
    # 7. Track_Cooccurrence 테이블 (NEW!)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS track_cooccurrence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_a TEXT NOT NULL,
            track_b TEXT NOT NULL,
            cooccurrence_count INTEGER DEFAULT 0,
            last_computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(track_a) REFERENCES tracks(id) ON DELETE CASCADE,
            FOREIGN KEY(track_b) REFERENCES tracks(id) ON DELETE CASCADE,
            UNIQUE(track_a, track_b),
            CHECK(track_a < track_b)
        )
    ''')
    print("✅ track_cooccurrence 테이블 생성 (신규)")
    
    # ============================================
    # 기존 테이블 제거 (사용 안 함)
    # ============================================
    
    # listening_history 제거 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='listening_history'")
    if cursor.fetchone():
        print("⚠️  listening_history 테이블 발견 (사용 안 함, 유지)")
    
    # track_pair_stats 제거 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='track_pair_stats'")
    if cursor.fetchone():
        print("⚠️  track_pair_stats 테이블 발견 (사용 안 함, 유지)")
    
    # ============================================
    # 인덱스 생성
    # ============================================
    print("\n📊 인덱스 생성 중...")
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_likes_user ON likes(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_likes_track ON likes(track_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist ON playlist_tracks(playlist_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_playlist_tracks_track ON playlist_tracks(track_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audio_features_track ON audio_features(track_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cooccurrence_track_a ON track_cooccurrence(track_a)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cooccurrence_track_b ON track_cooccurrence(track_b)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cooccurrence_count ON track_cooccurrence(cooccurrence_count)')
    
    print("✅ 인덱스 생성 완료")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ 데이터베이스 초기화 완료!")
    print("=" * 70)
    print("\n📊 테이블 현황:")
    print("  [기존 테이블 - 완전 호환]")
    print("    1. users              ✅ timestamp 유지")
    print("    2. likes              ✅ timestamp 유지")
    print("    3. playlists          ✅ timestamp 유지")
    print("    4. playlist_tracks    ✅ timestamp 유지")
    print("    5. tracks             ✅ timestamp 유지")
    print("    6. audio_features     ✅ 확장 + timestamp 유지")
    print("\n  [신규 테이블]")
    print("    7. track_cooccurrence ⭐ NEW")
    print("\n  [사용 안 함 - 유지만 함]")
    print("    - listening_history   (있어도 무시)")
    print("    - track_pair_stats    (있어도 무시)")
    print("\n✅ 기존 데이터 100% 호환!")
    print("=" * 70)

if __name__ == '__main__':
    init_db()