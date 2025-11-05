"""
Auralyze Database Schema - 기존 app.py 완벽 호환
이 파일을 app.py와 같은 폴더에 넣으세요
"""

import sqlite3
from datetime import datetime

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
    print("🎵 Auralyze Database 초기화 시작")
    print("=" * 70)
    
    # ============================================
    # 기존 테이블 (app.py와 동일)
    # ============================================
    
    # 1. Users 테이블
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
    print("✅ users 테이블 생성")
    
    # 2. Likes 테이블
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
    print("✅ likes 테이블 생성")
    
    # 3. Playlists 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    print("✅ playlists 테이블 생성")
    
    # 4. Playlist_Tracks 테이블
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
    print("✅ playlist_tracks 테이블 생성")
    
    # ============================================
    # 신규 테이블 (추천 시스템용)
    # ============================================
    
    # 5. Tracks 테이블 - Spotify 검색 결과 저장
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
    print("✅ tracks 테이블 생성")
    
    # 6. Audio_Features 테이블
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
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
        )
    ''')
    print("✅ audio_features 테이블 생성")
    
    # 7. Listening_History 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listening_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            track_id TEXT NOT NULL,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            listen_duration INTEGER,
            completed BOOLEAN DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
        )
    ''')
    print("✅ listening_history 테이블 생성")
    
    # 8. Track_Pair_Stats 테이블 - 추천 핵심!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS track_pair_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_a TEXT NOT NULL,
            track_b TEXT NOT NULL,
            co_count INTEGER DEFAULT 0,
            a_count INTEGER DEFAULT 0,
            b_count INTEGER DEFAULT 0,
            score_pmi REAL DEFAULT 0.0,
            score_jaccard REAL DEFAULT 0.0,
            last_computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(track_a) REFERENCES tracks(id) ON DELETE CASCADE,
            FOREIGN KEY(track_b) REFERENCES tracks(id) ON DELETE CASCADE,
            UNIQUE(track_a, track_b),
            CHECK(track_a < track_b)
        )
    ''')
    print("✅ track_pair_stats 테이블 생성 (추천 알고리즘 핵심)")
    
    # 인덱스 생성
    print("\n📊 인덱스 생성 중...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_likes_user ON likes(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_user ON listening_history(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pair_pmi ON track_pair_stats(score_pmi)')
    print("✅ 인덱스 생성 완료")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ 데이터베이스 초기화 완료!")
    print("=" * 70)
    print("\n📊 생성된 테이블 (8개):")
    print("  [기존] users, likes, playlists, playlist_tracks")
    print("  [신규] tracks, audio_features, listening_history, track_pair_stats")
    print("=" * 70)

if __name__ == '__main__':
    init_db()