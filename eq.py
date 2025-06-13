# apply_equalizer.py

import math
import numpy as np
import scipy.signal as signal

def design_peaking_eq(f0: float, gain_db: float, Q: float, fs: float):
    """
    Рассчитывает коэффициенты бикуадного пикового фильтра.
    
    Параметры:
        f0      — центральная частота (Гц)
        gain_db — усиление (дБ), положительное для подъёма, отрицательное для режекции
        Q       — добротность (безразмерная)
        fs      — частота дискретизации (Гц)
    
    Возвращает:
        (b, a) — числитель и знаменатель фильтра в виде numpy-массивов длины 3.
    """
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2 * Q)
    cos_w0 = math.cos(w0)

    b0 = 1 + alpha * A
    b1 = -2 * cos_w0
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * cos_w0
    a2 = 1 - alpha / A

    # Приводим к стандартному виду: y[n] = (b0/a0)*x[n] + ... - (a1/a0)*y[n-1] - ...
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])

    return b, a

def apply_equalizer(audio: np.ndarray,
                    gains: list[float],
                    fs: float,
                    bands: list[float],
                    Q: float = 1.0) -> np.ndarray:
    """
    Применяет пиковые фильтры к аудиосигналу последовательно для каждой полосы.

    Параметры:
        audio  — одномерный numpy-массив с аудиоданными (тип float, диапазон [-1..1])
        gains  — список значений усиления в дБ для каждой полосы (длина == len(bands))
        fs     — частота дискретизации аудио (Гц)
        bands  — список центральных частот полос (Гц)
        Q      — добротность фильтров (по умолчанию 1.0)

    Возвращает:
        numpy-массив той же длины, что и входной, с отфильтрованным сигналом.
    """
    y = audio.copy()
    for gain_db, f0 in zip(gains, bands):
        if gain_db == 0:
            continue
        b, a = design_peaking_eq(f0, gain_db, Q, fs)
        # Проходим через фильтр
        y = signal.lfilter(b, a, y)
    return y
