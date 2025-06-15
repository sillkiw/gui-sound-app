# similarity.py

import numpy as np
import librosa
from numpy.linalg import norm
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

# Кэш признаков
_mfcc_cache: dict[str, np.ndarray] = {}
_chroma_cache: dict[str, np.ndarray] = {}

def extract_mfcc(path: str, n_mfcc: int = 13) -> np.ndarray:
    """Средний MFCC вектор по всему треку."""
    if path in _mfcc_cache:
        return _mfcc_cache[path]
    y, sr = librosa.load(path, sr=None, mono=True)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    vec = np.mean(mfcc, axis=1)
    _mfcc_cache[path] = vec
    return vec

def extract_chroma(path: str) -> np.ndarray:
    """Средний хрома-вектор по всему треку."""
    if path in _chroma_cache:
        return _chroma_cache[path]
    y, sr = librosa.load(path, sr=None, mono=True)
    c = librosa.feature.chroma_stft(y=y, sr=sr)
    vec = np.mean(c, axis=1)
    _chroma_cache[path] = vec
    return vec

def mfcc_dtw_distance(path1: str, path2: str,
                      n_mfcc: int = 13, blocks: int = 6) -> float:
    """
    Разбивает треки на blocks блоков, строит MFCC+дельты и
    считает DTW расстояние через fastdtw.
    """
    def block_feats(path):
        y, sr = librosa.load(path, sr=None, mono=True)
        L = len(y)
        step = L // blocks
        feats = []
        for i in range(blocks):
            start = i*step
            end   = L if i == blocks-1 else (i+1)*step
            yb = y[start:end]
            mf = librosa.feature.mfcc(y=yb, sr=sr, n_mfcc=n_mfcc)
            d1 = librosa.feature.delta(data=mf)
            d2 = librosa.feature.delta(data=mf, order=2)
            feats.append(np.vstack([mf, d1, d2]))
        # получаем массив shape (T, features)
        return np.hstack(feats).T

    A = block_feats(path1)
    B = block_feats(path2)
    # fastdtw возвращает (distance, path)
    dist, _ = fastdtw(A, B, dist=euclidean)
    return dist

def dtw_similarity(path1: str, path2: str, alpha: float = 0.0005) -> float:
    """
    Переводим DTW-расстояние в [0..1] через экспоненту.
    Чем меньше dist, тем ближе к 1.
    """
    d = mfcc_dtw_distance(path1, path2)
    return float(np.exp(-alpha * d))

def chroma_similarity(path1: str, path2: str) -> float:
    """Косинусное сходство между средними хрома-векторами."""
    v1 = extract_chroma(path1)
    v2 = extract_chroma(path2)
    denom = norm(v1)*norm(v2)
    if denom == 0:
        return 0.0
    return float(np.dot(v1, v2) / denom)

def combined_similarity(path1: str, path2: str,
                        w_mfcc: float = 0.6, w_chroma: float = 0.4) -> float:
    """
    Комбинированная метрика: w_mfcc*DTW_sim + w_chroma*Chroma_sim
    """
    m = dtw_similarity(path1, path2)
    c = chroma_similarity(path1, path2)
    return w_mfcc*m + w_chroma*c

def compute_similarity_indices(playlist, ref_idx: int, comp_idxs: list[int]) -> dict[int, float]:
    """
    В AudioController: сравнивает трек по ref_idx со всеми comp_idxs,
    возвращает {idx: similarity}.
    """
    results: dict[int, float] = {}
    if ref_idx is None or not (0 <= ref_idx < len(playlist)):
        return results
    ref_path = playlist[ref_idx]['path']
    for idx in comp_idxs:
        if idx is None or not (0 <= idx < len(playlist)):
            continue
        path = playlist[idx]['path']
        sim  = combined_similarity(ref_path, path)
        results[idx] = sim
    return results

