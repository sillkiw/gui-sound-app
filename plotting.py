# plotting.py

import numpy as np
import librosa
import pyqtgraph as pg
from PyQt5.QtCore import QRectF



def plot_waveform(ui):
    """
    Рисует форму волны и RMS-график громкости.
    """
    y = ui.controller.data
    sr = ui.controller.fs
    if y is None or sr is None:
        return

    # Подготовка данных
    duration = len(y) / sr
    t = np.linspace(0, duration, num=len(y))
    step = max(1, len(y) // 50000)

    # Получаем PlotItem вместо прямого PlotWidget
    plot_item = ui.plot_widget.getPlotItem()
    plot_item.clear()
    plot_item.plot(t[::step], y[::step], pen=pg.mkPen('#0077cc'), downsample=True, clipToView=True)
    plot_item.setLabel('bottom', 'Time', units='s')
    plot_item.setLabel('left', 'Amplitude')
  

    # Линии
    ui.playhead.setPos(0) 
    ui.start_line.setPos(0)
    ui.end_line.setPos(duration)
    ui.playhead.setVisible(True)
    ui.start_line.setVisible(True)
    ui.end_line.setVisible(True)
    ui.plot_widget.addItem(ui.start_line)
    ui.plot_widget.addItem(ui.end_line)
    ui.plot_widget.addItem(ui.playhead)
    # RMS громкости
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=512)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)

    vol_item = ui.vol_plot_widget.getPlotItem()
    vol_item.clear()
    vol_item.plot(times, rms, pen=pg.mkPen('#cc0000'))
    vol_item.setLabel('bottom', 'Time', units='s')
    vol_item.setLabel('left', 'RMS')
  

def plot_spectrum(ui):
    """
    Рисует спектр (усреднённая амплитуда STFT) выбранного сегмента в ui.plot_widget.
    Скрывает график громкости (ui.vol_plot_widget) в UI-коде.
    """
    # Получаем сегмент
    y_seg, sr, start_sec, end_sec = ui.controller.get_segment(ui.start_line.value(),ui.end_line.value())
    if y_seg is None or sr is None:
        return

    # STFT
    n_fft = 2048
    hop_length = 512
    D = librosa.stft(y_seg, n_fft=n_fft, hop_length=hop_length)
    S_mag = np.abs(D)
    mag_mean = np.mean(S_mag, axis=1)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Отрисовка
    widget = ui.plot_widget
    widget.clear()
    widget.plot(freqs, mag_mean, pen=pg.mkPen('#0077cc'))
    widget.setLabel('bottom', 'Frequency', units='Hz')
    widget.setLabel('left', 'Magnitude')
    widget.setTitle('Спектр')
   


# def plot_spectrogram(ui):
#     """
#     Рисует спектрограмму (STFT -> dB) выбранного сегмента в ui.plot_widget
#     с цветовой картой 'inferno'.
#     Скрывает график громкости (ui.vol_plot_widget) в UI-коде.
#     """
#     # Получаем сегмент
#     y_seg, sr, start_sec, end_sec = ui.controller.get_segment(ui.start_line.value(),ui.end_line.value())
#     if y_seg is None or sr is None:
#         return

#     # STFT и перевод в dB
#     n_fft = 2048
#     hop_length = 512
#     D = librosa.stft(y_seg, n_fft=n_fft, hop_length=hop_length)
#     S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

#     # Оси
#     freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
#     times = librosa.frames_to_time(np.arange(S_db.shape[1]),
#                                    sr=sr, hop_length=hop_length)

#     # Переворачиваем по вертикали, чтобы нижние частоты были внизу
#     S_db_flip = np.flipud(S_db)

#     img = pg.ImageItem(S_db_flip)
#     cmap = pg.colormap.get('inferno')
#     lut = cmap.getLookupTable(0.0, 1.0, 256)
#     img.setLookupTable(lut)

#     t0, t1 = times[0], times[-1]
#     f0, f1 = freqs[0], freqs[-1]
#     img.setRect(QRectF(t0, f0, t1 - t0, f1 - f0))

#     plot_item = ui.plot_widget.getPlotItem()
#     plot_item.clear()
#     plot_item.addItem(img)
#     plot_item.setLabel('bottom', 'Time', units='s')
#     plot_item.setLabel('left', 'Frequency', units='Hz')
#     plot_item.setTitle('Spectrogram')
#     plot_item.getViewBox().enableAutoRange(False)
def plot_spectrogram(ui):
    ui.spec_ax.clear()
    y_seg, sr, start_sec, end_sec = ui.controller.get_segment(ui.start_line.value(),ui.end_line.value())
    if y_seg is None: 
        return
    D = librosa.stft(y_seg, n_fft=2048, hop_length=512)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
    librosa.display.specshow(
        S_db,
        sr=sr,
        hop_length=512,
        x_axis='time',
        y_axis='hz',
        cmap='inferno',
        ax=ui.spec_ax
    )
    ui.spec_ax.set_ylim(0, sr/2)
    ui.spec_canvas.draw()
