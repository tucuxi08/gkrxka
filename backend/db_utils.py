"""
Database Utility Functions v2.0 - 호환성 버전
Transformer 기반 인디곡 추천 시스템

✅ 기존 DB와 100% 호환
✅ timestamp 필드 처리
✅ 기존 함수 모두 유지
"""

import sqlite3
import requests
from itertools import combinations

DATABASE = 'auralyze.db'

def get_db():
    """DB 연결"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================
# Track 관련 함수
# ============================================

def save_track_from_spotify(track_data):
    """
    Spotify 검색 결과를 tracks 테이블에 저장
    
    ✅ 기존 함수와 완전 동일
    ✅ created_at은 자동 생성됨
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO tracks (
                id, title, artist, album, image, 
                preview_url, spotify_url, uri, release_date,
                duration_ms, popularity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            track_data.get('id'),
            track_data.get('title'),
            track_data.get('artist'),
            track_data.get('album'),
            track_data.get('image'),
            track_data.get('preview_url'),
            track_data.get('spotify_url'),
            track_data.get('uri'),
            track_data.get('release_date'),
            track_data.get('duration_ms'),
            track_data.get('popularity')
        ))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Track 저장 실패: {e}")
        return False
    finally:
        conn.close()

def get_track(track_id):
    """트랙 조회"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tracks WHERE id = ?', (track_id,))
    track = cursor.fetchone()
    conn.close()
    
    return dict(track) if track else None

def get_tracks_by_ids(track_ids):
    """여러 트랙 한번에 조회"""
    if not track_ids:
        return []
    
    conn = get_db()
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(track_ids))
    cursor.execute(f'SELECT * FROM tracks WHERE id IN ({placeholders})', track_ids)
    tracks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return tracks

# ============================================
# Audio Features 관련 함수
# ============================================

def save_audio_features(track_id, features):
    """
    Spotify Audio Features API 응답 저장
    
    ✅ 확장된 필드 지원 (loudness, key, mode, time_signature)
    ✅ fetched_at은 자동 생성됨
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO audio_features (
                track_id, danceability, energy, valence, tempo,
                acousticness, instrumentalness, speechiness, liveness,
                loudness, key, mode, time_signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            track_id,
            features.get('danceability'),
            features.get('energy'),
            features.get('valence'),
            features.get('tempo'),
            features.get('acousticness'),
            features.get('instrumentalness'),
            features.get('speechiness'),
            features.get('liveness'),
            features.get('loudness'),
            features.get('key'),
            features.get('mode'),
            features.get('time_signature')
        ))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Audio features 저장 실패: {e}")
        return False
    finally:
        conn.close()

def get_audio_features(track_id):
    """Audio features 조회"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM audio_features WHERE track_id = ?', (track_id,))
    features = cursor.fetchone()
    conn.close()
    
    return dict(features) if features else None

def get_audio_features_batch(track_ids):
    """여러 곡의 Audio Features 한번에 조회"""
    if not track_ids:
        return []
    
    conn = get_db()
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(track_ids))
    cursor.execute(f'SELECT * FROM audio_features WHERE track_id IN ({placeholders})', track_ids)
    features = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return features

# ============================================
# Track Cooccurrence 관련 함수 (NEW!)
# ============================================

def compute_track_cooccurrence():
    """
    모든 플레이리스트를 분석하여 track_cooccurrence 계산
    
    ✅ last_computed_at은 자동 업데이트됨
    """
    conn = get_db()
    cursor = conn.cursor()
    
    print("🔄 Track Cooccurrence 계산 시작...")
    
    # 1. 기존 데이터 초기화
    cursor.execute('DELETE FROM track_cooccurrence')
    
    # 2. 모든 플레이리스트 조회
    cursor.execute('SELECT id FROM playlists')
    playlists = cursor.fetchall()
    
    cooccurrence_dict = {}
    
    # 3. 각 플레이리스트에서 곡 쌍 추출
    for playlist in playlists:
        playlist_id = playlist['id']
        
        cursor.execute('''
            SELECT track_id FROM playlist_tracks 
            WHERE playlist_id = ?
        ''', (playlist_id,))
        
        tracks = [row['track_id'] for row in cursor.fetchall()]
        
        if len(tracks) < 2:
            continue
        
        # 모든 가능한 쌍 생성
        for track_a, track_b in combinations(sorted(tracks), 2):
            if track_a > track_b:
                track_a, track_b = track_b, track_a
            
            pair_key = (track_a, track_b)
            cooccurrence_dict[pair_key] = cooccurrence_dict.get(pair_key, 0) + 1
    
    # 4. DB에 저장
    for (track_a, track_b), count in cooccurrence_dict.items():
        cursor.execute('''
            INSERT INTO track_cooccurrence (track_a, track_b, cooccurrence_count)
            VALUES (?, ?, ?)
        ''', (track_a, track_b, count))
    
    conn.commit()
    total_pairs = len(cooccurrence_dict)
    conn.close()
    
    print(f"✅ Track Cooccurrence 계산 완료: {total_pairs}개 쌍")
    return total_pairs

def get_cooccurring_tracks(track_id, limit=20):
    """
    특정 곡과 함께 등장하는 곡들 조회
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            CASE 
                WHEN track_a = ? THEN track_b
                ELSE track_a
            END as related_track_id,
            cooccurrence_count
        FROM track_cooccurrence
        WHERE track_a = ? OR track_b = ?
        ORDER BY cooccurrence_count DESC
        LIMIT ?
    ''', (track_id, track_id, track_id, limit))
    
    results = [(row['related_track_id'], row['cooccurrence_count']) 
               for row in cursor.fetchall()]
    conn.close()
    
    return results

# ============================================
# 모델 입력 데이터 준비 함수
# ============================================

def get_user_training_data(user_id):
    """
    특정 사용자의 모델 학습용 데이터 준비
    
    Returns:
    {
        'user_id': 1,
        'onboarding_genres': ['K-POP', 'Hip-Hop', 'R&B', 'Pop'],
        'liked_tracks': ['track_id_1', 'track_id_2', ...],
        'liked_audio_features': [{...}, {...}, ...],
        'playlist_cooccurrence': {
            'track_id_1': [('related_track_1', 5), ...]
        }
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. 사용자 정보 조회
    cursor.execute('SELECT preferred_genre FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return None
    
    # 2. 온보딩 장르 (JSON 파싱)
    import json
    onboarding_genres = []
    try:
        onboarding_genres = json.loads(user['preferred_genre']) if user['preferred_genre'] else []
    except:
        onboarding_genres = []
    
    # 3. 좋아요 곡 리스트
    cursor.execute('''
        SELECT track_id FROM likes WHERE user_id = ?
    ''', (user_id,))
    liked_tracks = [row['track_id'] for row in cursor.fetchall()]
    
    # 4. 좋아요 곡들의 Audio Features
    liked_audio_features = get_audio_features_batch(liked_tracks) if liked_tracks else []
    
    # 5. 각 좋아요 곡의 공출현 정보
    playlist_cooccurrence = {}
    for track_id in liked_tracks:
        cooccurring = get_cooccurring_tracks(track_id, limit=10)
        if cooccurring:
            playlist_cooccurrence[track_id] = cooccurring
    
    conn.close()
    
    return {
        'user_id': user_id,
        'onboarding_genres': onboarding_genres,
        'liked_tracks': liked_tracks,
        'liked_audio_features': liked_audio_features,
        'playlist_cooccurrence': playlist_cooccurrence
    }

def get_all_training_data():
    """모든 사용자의 학습 데이터 수집"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users')
    user_ids = [row['id'] for row in cursor.fetchall()]
    conn.close()
    
    training_data = []
    for user_id in user_ids:
        user_data = get_user_training_data(user_id)
        if user_data:
            training_data.append(user_data)
    
    return training_data

# ============================================
# 유틸리티 함수
# ============================================

def get_tracks_without_audio_features():
    """Audio Features가 없는 곡 리스트"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t.id, t.title, t.artist
        FROM tracks t
        LEFT JOIN audio_features af ON t.id = af.track_id
        WHERE af.track_id IS NULL
    ''')
    
    tracks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return tracks

def get_database_stats():
    """데이터베이스 통계"""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    tables = ['users', 'likes', 'playlists', 'playlist_tracks', 
              'tracks', 'audio_features', 'track_cooccurrence']
    
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
            stats[table] = cursor.fetchone()['count']
        except:
            stats[table] = 0
    
    # 사용 안 하는 테이블도 표시 (있으면)
    try:
        cursor.execute('SELECT COUNT(*) as count FROM listening_history')
        stats['listening_history (사용안함)'] = cursor.fetchone()['count']
    except:
        pass
    
    try:
        cursor.execute('SELECT COUNT(*) as count FROM track_pair_stats')
        stats['track_pair_stats (사용안함)'] = cursor.fetchone()['count']
    except:
        pass
    
    conn.close()
    
    return stats

# ============================================
# 기존 DB 마이그레이션 헬퍼 함수
# ============================================

def migrate_audio_features():
    """
    기존 audio_features 테이블에 새 필드 추가
    (loudness, key, mode, time_signature)
    
    ✅ 기존 데이터 보존하면서 확장
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 기존 테이블 구조 확인
    cursor.execute("PRAGMA table_info(audio_features)")
    columns = [row[1] for row in cursor.fetchall()]
    
    needs_migration = False
    
    # 새 필드가 없으면 추가
    if 'loudness' not in columns:
        cursor.execute('ALTER TABLE audio_features ADD COLUMN loudness REAL')
        print("✅ loudness 필드 추가")
        needs_migration = True
    
    if 'key' not in columns:
        cursor.execute('ALTER TABLE audio_features ADD COLUMN key INTEGER')
        print("✅ key 필드 추가")
        needs_migration = True
    
    if 'mode' not in columns:
        cursor.execute('ALTER TABLE audio_features ADD COLUMN mode INTEGER')
        print("✅ mode 필드 추가")
        needs_migration = True
    
    if 'time_signature' not in columns:
        cursor.execute('ALTER TABLE audio_features ADD COLUMN time_signature INTEGER')
        print("✅ time_signature 필드 추가")
        needs_migration = True
    
    if needs_migration:
        conn.commit()
        print("✅ audio_features 마이그레이션 완료")
    else:
        print("✅ audio_features 이미 최신 버전")
    
    conn.close()

if __name__ == '__main__':
    print("Database Utility Functions v2.0 (호환성 버전)")
    print("\n📊 데이터베이스 통계:")
    stats = get_database_stats()
    for table, count in stats.items():
        print(f"  {table}: {count}개")