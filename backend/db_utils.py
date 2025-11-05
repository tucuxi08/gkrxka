"""
Database Utility Functions - 기존 app.py 호환
"""

import sqlite3
from datetime import datetime

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
    
    track_data 형식 (app.py의 formatted_track):
    {
        'id': 'spotify_track_id',
        'title': '곡 제목',
        'artist': '아티스트',
        'album': '앨범명',
        'image': '이미지 URL',
        'preview_url': '미리듣기 URL',
        'spotify_url': 'Spotify URL',
        'uri': 'spotify:track:...',
        'release_date': '2024-01-01'
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO tracks (
                id, title, artist, album, image, 
                preview_url, spotify_url, uri, release_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            track_data.get('id'),
            track_data.get('title'),
            track_data.get('artist'),
            track_data.get('album'),
            track_data.get('image'),
            track_data.get('preview_url'),
            track_data.get('spotify_url'),
            track_data.get('uri'),
            track_data.get('release_date')
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

# ============================================
# Audio Features 관련 함수
# ============================================

def save_audio_features(track_id, features):
    """
    Spotify Audio Features API 응답 저장
    
    features 형식:
    {
        'danceability': 0.825,
        'energy': 0.792,
        'valence': 0.874,
        'tempo': 114.0,
        ...
    }
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO audio_features (
                track_id, danceability, energy, valence, tempo,
                acousticness, instrumentalness, speechiness, liveness
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            track_id,
            features.get('danceability'),
            features.get('energy'),
            features.get('valence'),
            features.get('tempo'),
            features.get('acousticness'),
            features.get('instrumentalness'),
            features.get('speechiness'),
            features.get('liveness')
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

def get_similar_tracks_by_audio(track_id, limit=10):
    """
    Audio features 기반 유사한 곡 찾기
    에너지, 분위기, 템포 유사도
    """
    features = get_audio_features(track_id)
    if not features:
        return []
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t.*, af.*,
        (
            ABS(af.danceability - ?) +
            ABS(af.energy - ?) +
            ABS(af.valence - ?)
        ) as distance
        FROM tracks t
        JOIN audio_features af ON t.id = af.track_id
        WHERE t.id != ?
        ORDER BY distance ASC
        LIMIT ?
    ''', (features['danceability'], features['energy'], 
          features['valence'], track_id, limit))
    
    tracks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return tracks

# ============================================
# Listening History 관련 함수
# ============================================

def add_listening_history(user_id, track_id, listen_duration=None, completed=False):
    """청취 기록 추가"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO listening_history (
            user_id, track_id, listen_duration, completed
        ) VALUES (?, ?, ?, ?)
    ''', (user_id, track_id, listen_duration, completed))
    
    history_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return history_id

def get_listening_history(user_id, limit=50):
    """청취 기록 조회"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t.*, lh.played_at, lh.listen_duration
        FROM tracks t
        JOIN listening_history lh ON t.id = lh.track_id
        WHERE lh.user_id = ?
        ORDER BY lh.played_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return history

# ============================================
# Track Pair Stats 관련 함수 (추천 핵심!)
# ============================================

def update_track_pair_stats(track_a, track_b):
    """
    두 곡의 동시 청취 통계 업데이트
    사용자가 곡을 들을 때마다 호출
    """
    if track_a > track_b:
        track_a, track_b = track_b, track_a
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM track_pair_stats
        WHERE track_a = ? AND track_b = ?
    ''', (track_a, track_b))
    
    pair = cursor.fetchone()
    
    if pair:
        cursor.execute('''
            UPDATE track_pair_stats
            SET co_count = co_count + 1,
                last_computed_at = CURRENT_TIMESTAMP
            WHERE track_a = ? AND track_b = ?
        ''', (track_a, track_b))
    else:
        cursor.execute('''
            INSERT INTO track_pair_stats (track_a, track_b, co_count)
            VALUES (?, ?, 1)
        ''', (track_a, track_b))
    
    conn.commit()
    conn.close()

def get_recommended_tracks_by_pair(track_id, limit=10):
    """
    Track pair stats 기반 추천
    "이 곡을 들은 사람들이 자주 함께 듣는 곡"
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            CASE 
                WHEN tps.track_a = ? THEN tps.track_b
                ELSE tps.track_a
            END as recommended_track_id,
            tps.score_pmi,
            tps.co_count,
            t.*
        FROM track_pair_stats tps
        JOIN tracks t ON (
            CASE 
                WHEN tps.track_a = ? THEN tps.track_b
                ELSE tps.track_a
            END = t.id
        )
        WHERE tps.track_a = ? OR tps.track_b = ?
        ORDER BY tps.score_pmi DESC, tps.co_count DESC
        LIMIT ?
    ''', (track_id, track_id, track_id, track_id, limit))
    
    tracks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return tracks

def compute_pair_scores():
    """
    모든 pair의 PMI, Jaccard 점수 계산
    주기적으로 실행 (예: 하루 1번)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM listening_history')
    result = cursor.fetchone()
    total_users = result[0] if result else 0
    
    if total_users == 0:
        conn.close()
        return
    
    # 각 트랙의 청취 수 계산
    cursor.execute('''
        UPDATE track_pair_stats
        SET a_count = (
            SELECT COUNT(DISTINCT user_id)
            FROM listening_history
            WHERE track_id = track_a
        ),
        b_count = (
            SELECT COUNT(DISTINCT user_id)
            FROM listening_history
            WHERE track_id = track_b
        )
    ''')
    
    # PMI, Jaccard 계산
    cursor.execute(f'''
        UPDATE track_pair_stats
        SET score_pmi = CASE
            WHEN a_count > 0 AND b_count > 0 THEN
                LOG(CAST(co_count * {total_users} AS REAL) / (a_count * b_count))
            ELSE 0
        END,
        score_jaccard = CASE
            WHEN (a_count + b_count - co_count) > 0 THEN
                CAST(co_count AS REAL) / (a_count + b_count - co_count)
            ELSE 0
        END,
        last_computed_at = CURRENT_TIMESTAMP
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Pair scores 계산 완료 (총 {total_users}명)")

# ============================================
# Hybrid 추천 알고리즘
# ============================================

def get_hybrid_recommendations(user_id, limit=10):
    """
    하이브리드 추천
    - 청취 기록 기반 pair stats
    - Audio features 유사도
    """
    recommendations = []
    
    # 1. 최근 들은 곡 기반 pair stats 추천
    recent = get_listening_history(user_id, limit=5)
    for track in recent[:2]:
        paired = get_recommended_tracks_by_pair(track['id'], limit=3)
        recommendations.extend(paired)
    
    # 2. 좋아요한 곡 기반 audio features 추천
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.* FROM tracks t
        JOIN likes l ON t.id = l.track_id
        WHERE l.user_id = ?
        ORDER BY l.created_at DESC
        LIMIT 2
    ''', (user_id,))
    liked = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for track in liked:
        similar = get_similar_tracks_by_audio(track['id'], limit=2)
        recommendations.extend(similar)
    
    # 중복 제거
    unique = {t.get('id', t.get('recommended_track_id')): t for t in recommendations if t}
    return list(unique.values())[:limit]

if __name__ == '__main__':
    print("Database Utility Functions")