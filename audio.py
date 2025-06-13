# audio.py

import os
import tempfile

from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore       import QUrl

import librosa
import numpy as np
import scipy.io.wavfile as wavfile



from eq import apply_equalizer  # ваш модуль эквалайзера

class AudioController:
    def __init__(self):
        # Основной Qt-плеер
        self.player        = QMediaPlayer()
        # Плейлист: список словарей {"path", "title", "duration", "original_data", "original_fs"}
        self.playlist      = []
        self.current_index = None
        # Данные текущего трека
        self.data          = None
        self.fs            = None
        self.duration      = 0  # в миллисекундах

        

    def open_file(self, path):
        """
        Загружает аудио-файл через librosa и начинает воспроизведение.
        При этом:
        - Сохраняет оригинальные данные в плейлисте (если файл новый)
        - Обновляет current_index на указанный трек
        - Устанавливает QMediaPlayer на воспроизведение
        """
        import os, librosa

        # 1) Проверяем, что файл существует
        if not os.path.exists(path):
            return

        # 2) Загружаем сигнал и частоту дискретизации
        y, sr = librosa.load(path, sr=None, mono=True)
        self.data, self.fs = y, sr

        # 3) Проверяем, есть ли уже такой трек в плейлисте
        found = False
        for idx, tr in enumerate(self.playlist):
            if tr['path'] == path:
                self.current_index = idx
                found = True
                break

        # 4) Если не найден — добавляем новый трек с оригинальными данными
        if not found:
            duration = librosa.get_duration(y=y, sr=sr)
            track = {
                'path': path,
                'title': os.path.basename(path),
                'duration': duration,
                'original_data': y.copy(),
                'original_fs': sr
            }
            self.playlist.append(track)
            self.current_index = len(self.playlist) - 1

        # 5) Устанавливаем media и запускаем воспроизведение
        self._set_media(path)
        self.player.play()
        
    def add_files(self, paths):
        """
        Добавляет в плейлист контроллера все файлы из списка paths,
        не прерывая текущее воспроизведение.

        Для каждого нового файла:
        – загружает сигнал через librosa
        – вычисляет длительность
        – сохраняет копию «чистого» сигнала и fs
        – добавляет запись в self.playlist
        """
        import os, librosa

        for path in paths:
            # проверяем существование файла и отсутствие дубликатов
            print(self.playlist)
            if not os.path.exists(path) or any(t['path'] == path for t in self.playlist):
                continue

            # загружаем оригинальный сигнал
            y, sr = librosa.load(path, sr=None, mono=True)
            duration = librosa.get_duration(y=y, sr=sr)

            # формируем запись трека
            track = {
                'path': path,
                'title': os.path.basename(path),
                'duration': duration,
                'original_data': y.copy(),
                'original_fs': sr
            }
            self.playlist.append(track)

    def _set_media(self, path):
        """
        Вспомогательный метод для установки нового media в плеер
        и обновления self.duration.
        """
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        # duration будет доступна после загрузки метаданных
        # но мы можем попытаться получить её сразу
        self.duration = self.player.duration()

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def play_next(self):
        """
        Переключает на следующий трек в плейлисте.
        """
        if not self.playlist:
            return
        if self.current_index is None:
            self.current_index = 0
        else:
            self.current_index = (self.current_index + 1) % len(self.playlist)
        path = self.playlist[self.current_index]["path"]
        self.open_file(path)

    def play_prev(self):
        """
        Переключает на предыдущий трек в плейлисте.
        """
        if not self.playlist:
            return
        if self.current_index is None:
            self.current_index = 0
        else:
            self.current_index = (self.current_index - 1) % len(self.playlist)
        path = self.playlist[self.current_index]["path"]
        self.open_file(path)

    def set_position(self, ms):
        """
        Устанавливает позицию воспроизведения (в миллисекундах).
        Вызывается из главного слайдера.
        """
        self.player.setPosition(ms)

    def seek(self, sec):
        """
        Перематывает на заданное время в секундах
        """
        self.player.setPosition(int(sec * 1000))

    def apply_eq(self, gains, eq_bands):
        """
        Применяет эквалайзер к self.data и воспроизводит результат.
        gains     — список усилений дБ для каждой полосы eq_bands.
        eq_bands  — список центральных частот.
        """
        if self.data is None or self.fs is None:
            return

        tr = self.playlist[self.current_index]
        
        # Фильтруем исходный сигнал
        y_orig = tr.get('original_data', self.data)

        # Применяем фильтр
        y_eq = apply_equalizer(y_orig, gains, self.fs, eq_bands)
        self.data = y_eq

        # Нормируем и сохраняем во временный WAV
        y_norm = y_eq / np.max(np.abs(y_eq))
        int_data = np.int16(y_norm * 32767)
        fd, tmp = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        wavfile.write(tmp, self.fs, int_data)
        
        # Очистка предыдущего фильтрованного файла
        if hasattr(self, 'filtered_path') and os.path.exists(self.filtered_path):
            os.remove(self.filtered_path)
        self.filtered_path = tmp
        
        # Ставим новый медиа и играем
        self._set_media(tmp)
        self.player.play()

    def get_segment(self, start_sec, end_sec):
        """
        Возвращает сегмент массива audio между start_sec и end_sec,
        а также sr, start_sec и end_sec.
        """
        if self.data is None or self.fs is None:
            return None, None, None, None
        # Границы внутри допустимого диапазона
        total = len(self.data) / self.fs
        s = max(0.0, min(start_sec, total))
        e = max(0.0, min(end_sec, total))
        if e < s:
            s, e = e, s
        start_idx = int(s * self.fs)
        end_idx   = int(e * self.fs)
        return self.data[start_idx:end_idx], self.fs, s, e
