# similarity.py

import numpy as np
import librosa
from numpy.linalg import norm

# Кэш MFCC-дескрипторов, чтобы не пересчитывать каждый раз
_mfcc_cache: dict[str, np.ndarray] = {}


def extract_mfcc(path: str, n_mfcc: int = 13) -> np.ndarray:
    """
    Загружает аудиофайл по пути path, вычисляет MFCC и усредняет их по времени.
    Результатом является вектор длины n_mfcc.
    Используется кэш для ускорения повторных вычислений.
    """
    if path in _mfcc_cache:
        return _mfcc_cache[path]

    # y — сигнал, sr — частота дискретизации
    y, sr = librosa.load(path, sr=None, mono=True)
    # mfcc: shape (n_mfcc, T)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    # усредняем по оси времени → (n_mfcc,)
    mfcc_mean = np.mean(mfcc, axis=1)
    _mfcc_cache[path] = mfcc_mean
    return mfcc_mean


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Косинусное сходство между двумя векторами a и b.
    Возвращает значение в [0..1], или 0, если один из векторов нулевой.
    """
    denom = norm(a) * norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def compute_similarity(ref_path: str, other_paths: list[str]) -> dict[str, float]:
    """
    Сравнивает эталонный файл ref_path со списком other_paths.
    Возвращает словарь { путь_к_файлу: степень_сходства }.
    """
    ref_vec = extract_mfcc(ref_path)
    results: dict[str, float] = {}
    for path in other_paths:
        vec = extract_mfcc(path)
        results[path] = cosine_similarity(ref_vec, vec)
    return results


def compute_similarity_indices(playlist: list[dict], ref_idx: int, comp_idxs: list[int]) -> dict[int, float]:
    """
    Вариант для работы по индексам плейлиста:
      playlist[i]['path'] должен быть валидным путём к файлу.
    Возвращает { индекс_в_playlist: степень_сходства }.
    """
    ref_path = playlist[ref_idx]['path']
    ref_vec = extract_mfcc(ref_path)
    results: dict[int, float] = {}
    for idx in comp_idxs:
        path = playlist[idx]['path']
        vec = extract_mfcc(path)
        results[idx] = cosine_similarity(ref_vec, vec)
    return results
