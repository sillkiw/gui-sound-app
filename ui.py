
import os, librosa
from PyQt5.QtWidgets import (QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QSlider, QLabel, QStyle,
    QAction, QListWidget, QListWidgetItem, QSizePolicy    # ← добавили сюда
)
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg

from audio import AudioController
from plotting import plot_waveform, plot_spectrum, plot_spectrogram
from utils import format_time, save_playlist_json, load_playlist_json
from dialogs     import SimilarityTableDialog, SimilarityGraphDialog

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure



class AudioPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Audio Player with Playlist")
        self.setWindowState(Qt.WindowMaximized)

        # Контроллер для логики воспроизведения
        self.controller = AudioController()

        # UI
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # Стилизация
        self.setStyleSheet("""
            QMainWindow { background-color: #f9f9f9; }
            QPushButton { background-color: #e0e0e0; border: none; border-radius: 6px; padding: 10px; }
            QPushButton:hover { background-color: #d0d0d0; }
            QSlider#mainSlider::groove:horizontal { height: 8px; background: #ccc; border: none; border-radius: 4px; }
            QSlider#mainSlider::handle:horizontal { background: #888; width: 16px; margin: -4px 0; border-radius: 8px; }
            QSlider#smallSlider::groove:horizontal { height: 4px; background: #ccc; border: none; border-radius: 2px; }
            QSlider#smallSlider::handle:horizontal { background: #888; width: 10px; margin: -3px 0; border-radius: 5px; }
        """
)
        # Меню
        file_menu = self.menuBar().addMenu("File")
        self.open_action = QAction("Open...", self)
        self.add_action = QAction("Add to Playlist...", self)
        self.save_action = QAction("Save Playlist...", self)
        self.load_action = QAction("Load Playlist...", self)
        file_menu.addActions([self.open_action, self.add_action, self.save_action, self.load_action])

        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Плейлист
        self.playlistWidget = QListWidget()
        self.playlistWidget.setFixedWidth(300)
        main_layout.addWidget(self.playlistWidget, stretch=1)

        # Правая панель
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Метаданные с кнопкой скрытия плейлиста
        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(10)
        self.toggle_playlist_btn = QPushButton("≡")
        self.toggle_playlist_btn.setFixedSize(25, 25)
        self.toggle_playlist_btn.setStyleSheet("padding: 0px; font-size: 16px;")
        self.meta_label = QLabel("No file loaded")
        self.meta_label.setAlignment(Qt.AlignCenter)
        self.meta_label.setStyleSheet("background-color: #e0e0e0; padding: 8px; border-radius: 8px; font-weight: bold; font-size: 14px;")
        meta_layout.addWidget(self.toggle_playlist_btn)
        meta_layout.addWidget(self.meta_label, stretch=1)
        right_layout.addLayout(meta_layout)

        # Waveform и Volume графики
        self.plot_widget = pg.PlotWidget(title="Waveform")
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMinimumHeight(150)
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        right_layout.addWidget(self.plot_widget,stretch=1)

        self.vol_plot_widget = pg.PlotWidget(title="Volume")
        self.vol_plot_widget.setBackground('w')
        self.vol_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.vol_plot_widget.setMinimumHeight(150)
        self.vol_plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)

        right_layout.addWidget(self.vol_plot_widget, stretch=1)


        # ... после создания self.plot_widget и self.vol_plot_widget
        self.spec_fig = Figure(figsize=(5,2))
        self.spec_canvas = FigureCanvas(self.spec_fig)
        self.spec_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.spec_ax = self.spec_fig.add_subplot(111)
        right_layout.addWidget(self.spec_canvas)
        self.spec_canvas.setVisible(False)

       

        # Вертикальные линии: playhead, segment
        self.start_line = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen('g', width=4))
        self.end_line = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen('b', width=4))
        self.playhead = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen('r', width=4))
        self.plot_widget.addItem(self.playhead)
        self.plot_widget.addItem(self.start_line)
        self.plot_widget.addItem(self.end_line)
        self.start_line.setVisible(False)
        self.end_line.setVisible(False)

        # Кнопки управления
        controls = QHBoxLayout()
        style = self.style()
        self.prev_btn = QPushButton(style.standardIcon(QStyle.SP_MediaSkipBackward), "")
        self.play_btn = QPushButton(style.standardIcon(QStyle.SP_MediaPlay), "")
        self.pause_btn = QPushButton(style.standardIcon(QStyle.SP_MediaPause), "")
        self.stop_btn = QPushButton(style.standardIcon(QStyle.SP_MediaStop), "")
        self.next_btn = QPushButton(style.standardIcon(QStyle.SP_MediaSkipForward), "")
        for btn in (self.prev_btn, self.play_btn, self.pause_btn, self.stop_btn, self.next_btn):
            btn.setFixedSize(50, 50)
        controls.addStretch()
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch()
        right_layout.addLayout(controls)

        # Навигационные кнопки
        spec_layout = QHBoxLayout()
        self.waveform_btn = QPushButton("Waveform")
        self.spectrum_btn = QPushButton("Spectrum")
        self.spectrogram_btn = QPushButton("Spectrogram")
        self.eq_toggle_btn = QPushButton("EQ")
        for btn in (self.waveform_btn, self.spectrum_btn, self.spectrogram_btn, self.eq_toggle_btn):
            btn.setFixedHeight(30)
        spec_layout.addStretch()
        spec_layout.addWidget(self.waveform_btn)
        spec_layout.addWidget(self.spectrum_btn)
        spec_layout.addWidget(self.spectrogram_btn)
        spec_layout.addWidget(self.eq_toggle_btn)
        spec_layout.addStretch()
        right_layout.addLayout(spec_layout)

        # Эквалайзер
        self.eq_bands = [60, 250, 1000, 4000, 16000]
        self.eq_panel = QWidget()
        self.eq_panel = QWidget()
        eq_layout = QVBoxLayout(self.eq_panel)
        eq_layout.setContentsMargins(10, 10, 10, 10)
        eq_layout.setSpacing(10)
        eq_label = QLabel("Equalizer")
        eq_label.setAlignment(Qt.AlignCenter)
        eq_layout.addWidget(eq_label)

        self.eq_sliders = []
        freq_layout = QHBoxLayout()
        freq_layout.setSpacing(20)
        for freq in self.eq_bands:
            vbox = QVBoxLayout()
            lbl = QLabel(f"{freq} Hz")
            lbl.setAlignment(Qt.AlignCenter)
            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(0)
            slider.setFixedHeight(150)
            slider.setObjectName("eqSlider")
            self.eq_sliders.append(slider)
            vbox.addWidget(lbl)
            vbox.addWidget(slider)
            freq_layout.addLayout(vbox)
        eq_layout.addLayout(freq_layout)
        
        buttons_layout = QHBoxLayout()
        self.eq_apply_btn = QPushButton("Apply EQ")
        self.eq_reset_btn = QPushButton("Reset EQ")
        buttons_layout.addWidget(self.eq_apply_btn)
        buttons_layout.addWidget(self.eq_reset_btn)
        eq_layout.addLayout(buttons_layout)

        self.eq_panel.setVisible(False)
        right_layout.addWidget(self.eq_panel)
        
        # Секция времени и главный слайдер
        time_layout = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setObjectName("mainSlider")
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.slider)
        right_layout.addLayout(time_layout)

        # Громкость и скорость
        vs_layout = QHBoxLayout()
        vs_layout.setSpacing(40)
        vol_layout = QHBoxLayout()
        vol_label = QLabel("Volume")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setObjectName("smallSlider")
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(50)
        self.vol_slider.setFixedWidth(150)
        self.vol_value = QLabel("50%")
        vol_layout.addWidget(vol_label)
        vol_layout.addWidget(self.vol_slider)
        vol_layout.addWidget(self.vol_value)
        rate_layout = QHBoxLayout()
        rate_label = QLabel("Speed")
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setObjectName("smallSlider")
        self.rate_slider.setRange(50, 200)
        self.rate_slider.setValue(100)
        self.rate_slider.setFixedWidth(150)
        self.rate_value = QLabel("1.00x")
        rate_layout.addWidget(rate_label)
        rate_layout.addWidget(self.rate_slider)
        rate_layout.addWidget(self.rate_value)
        vs_layout.addLayout(vol_layout)
        vs_layout.addLayout(rate_layout)
        right_layout.addLayout(vs_layout)

        main_layout.addWidget(right_panel, stretch=4)

        # Таймер для обновления слайдера
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_slider)

    def connect_signals(self):
        self.controller.player.metaDataChanged.connect(self.update_metadata)
        
        # Меню действий
        self.open_action.triggered .connect(self.on_open)
        self.add_action.triggered  .connect(self.on_add)
        self.save_action.triggered .connect(self.on_save_playlist)
        self.load_action.triggered .connect(self.on_load_playlist)


        # Сигналы QMediaPlayer
        self.controller.player.positionChanged  .connect(self.on_position_changed)
        self.controller.player.durationChanged  .connect(self.on_duration_changed)
        self.controller.player.mediaStatusChanged.connect(self.on_media_status_changed)


        # Плейлист
        self.playlistWidget.itemDoubleClicked.connect(self.on_playlist_item_double_clicked)
        self.toggle_playlist_btn.clicked.connect(self.toggle_playlist_visibility)

        # Кнопки управления
        self.play_btn.clicked .connect(self.controller.play)
        self.pause_btn.clicked.connect(self.controller.pause)
        self.stop_btn.clicked .connect(self.controller.stop)
        self.prev_btn.clicked .connect(self.on_prev)
        self.next_btn.clicked .connect(self.on_next)

        # Перемотка и playhead
        self.slider.sliderMoved                  .connect(self.controller.set_position)

        # Громкость и скорость
        self.vol_slider.valueChanged             .connect(self.on_volume_change)
        self.rate_slider.valueChanged            .connect(self.on_rate_change)

        # Вид графиков
        self.waveform_btn.clicked    .connect(lambda: self.show_view('waveform'))
        self.spectrum_btn.clicked    .connect(lambda: self.show_view('spectrum'))
        self.spectrogram_btn.clicked .connect(lambda: self.show_view('spectrogram'))
        self.eq_toggle_btn.clicked   .connect(lambda: self.eq_panel.setVisible(not self.eq_panel.isVisible()))

        # Эквалайзер
        self.eq_apply_btn.clicked    .connect(self.apply_eq_and_refresh)
        self.eq_reset_btn.clicked    .connect(self.reset_eq)

    
    # --- Слоты ---
    def on_open(self):
        """
        Открывает аудиофайл через контроллер и обновляет весь UI 
        (графики, список треков, метаданные, заголовок окна).
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.wav *.mp3)"
        )
        if not path:
            return

        # Контроллер загрузит и запустит файл, а также добавит его в плейлист
        self.controller.open_file(path)
        
        self.refresh_playlist_widget()
        
        # Перерисовка графиков
        self.update_ui_for_current_track()

    def on_next(self):
        """
        Обрабатывает клик по Next: 
        – переключает трек в контроллере,
        – обновляет UI (графики, список, метаданные, таймер).
        """
        # 1) переключаем в контроллере
        self.controller.play_next()
        # 2) обновляем весь интерфейс под новый трек
        self.update_ui_for_current_track()


    def on_prev(self):
        
        # 1) переключаем в контроллере
        self.controller.play_prev()
        # 2) обновляем весь интерфейс под новый трек
        self.update_ui_for_current_track()


    def on_add(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "", "Audio Files (*.wav *.mp3)"
        )
        if not paths:
            return
        self.controller.add_files(paths)
        self.refresh_playlist_widget()
    
    def on_playlist_item_double_clicked(self, item):
        """
        Воспроизводит трек при двойном клике по элементу плейлиста:
        обновляет controller.current_index, загружает аудио, перерисовывает графики
        и обновляет заголовок окна с названием трека.
        """
        row = self.playlistWidget.currentRow()
        if row < 0 or row >= len(self.controller.playlist):
            return

        # Устанавливаем выбранный индекс и открываем файл
        self.controller.current_index = row
        track = self.controller.playlist[row]
        self.controller.open_file(track['path'])

        self.update_ui_for_current_track()

    def on_save_playlist(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Playlist", "", "JSON Files (*.json)")
        if path:
            save_playlist_json(path, self.controller.playlist)

    def on_load_playlist(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Playlist", "", "JSON Files (*.json)"
        )
        if not path:
            return

        # 1) Считаем только сериализуемые поля
        raw_list = load_playlist_json(path)

        # 2) Восстанавливаем полный плейлист с оригинальными данными
        self.controller.playlist.clear()
        for tr in raw_list:
            y, sr = librosa.load(tr['path'], sr=None, mono=True)
            track = {
                'path':          tr['path'],
                'title':         tr['title'],
                'duration':      tr['duration'],
                'original_data': y.copy(),
                'original_fs':   sr
            }
            self.controller.playlist.append(track)

        # 3) Обновляем виджет плейлиста
        self.refresh_playlist_widget()

        # 4) Сбрасываем текущий индекс на первый трек и обновляем UI
        self.controller.current_index = 0
        self.update_ui_for_current_track()
    
    def on_position_changed(self, pos):
        """
        Слот, вызываемый при каждом изменении позиции плеера.
        Обновляет метку времени, слайдер и красную линию-плейхед на графиках.
        """
        # Переводим позицию из миллисекунд в секунды
        sec = pos / 1000.0
        # Делим на минуты и секунды для отображения MM:SS
        m, s = divmod(int(sec), 60)
        # Обновляем текст метки вида «текущее / общее»
        self.time_label.setText(f"{m:02d}:{s:02d} / {format_time(self.controller.duration)}")
        # Ставим ползунок в нужное положение
        self.slider.setValue(pos)
        # Передвигаем вертикальную линию playhead на графике волны
        self.playhead.setPos(sec)


    def on_duration_changed(self, dur):
        """
        Слот, вызываемый при загрузке трека.
        Устанавливает полный диапазон слайдера и сохраняет длительность.
        """
        # Сохраняем длительность в контроллере
        self.controller.duration = dur
        # Задаём диапазон главного слайдера от 0 до полной длительности
        self.slider.setRange(0, dur)


    def on_media_status_changed(self, status):
        """
        Слот для отслеживания статуса медиа (загрузка, конец трека и т.д.).
        При достижении конца трека перематывает его в начало.
        """
        if status == QMediaPlayer.EndOfMedia:
            # Ставим позицию воспроизведения на начало (0 мс)
            self.controller.player.setPosition(0)


    def on_playhead_moved(self):
        """
        Слот, вызываемый при перетаскивании красной линии-playhead на графике.
        Перематывает плеер на новую позицию.
        """
        # Получаем новое значение playhead в секундах
        sec = self.playhead.value()
        # Устанавливаем позицию плеера и слайдера в миллисекундах
        self.controller.seek(sec)
        self.slider.setValue(int(sec * 1000))


    def on_volume_change(self, v):
        """
        Слот для обработки изменения громкости через слайдер.
        Устанавливает громкость плеера и обновляет метку-значение.
        """
        # Меняем громкость у QMediaPlayer
        self.controller.player.setVolume(v)
        # Отображаем значение громкости рядом со слайдером
        self.vol_value.setText(f"{v}%")


    def on_rate_change(self, v):
        """
        Слот для обработки изменения скорости воспроизведения.
        Устанавливает новую скорость и обновляет метку-значение.
        """
        # Переводим целочисленное значение (50–200) в коэффициент (0.5–2.0)
        rate = v / 100.0
        # Меняем скорость плеера
        self.controller.player.setPlaybackRate(rate)
        # Обновляем текст метки вида «1.25x»
        self.rate_value.setText(f"{rate:.2f}x")
   
    # --Обновление--
    def update_metadata(self):
        """
        Обновляет информацию о текущем треке в метке и в заголовке окна.
        Берёт Title из QMediaPlayer.metaData, а если его нет — из controller.playlist.
        """
        player = self.controller.player

        # Попробуем получить встроенный Title
        title = player.metaData("Title")
        # Если метаданных нет, берём title из плейлиста по текущему индексу
        idx = self.controller.current_index
        if not title and idx is not None and idx < len(self.controller.playlist):
            title = self.controller.playlist[idx].get("title",
                                                    os.path.basename(self.controller.playlist[idx]["path"]))
        # Если и этого нет — показываем заглушку
        if not title:
            title = "No file loaded"

        # Соберём прочую информацию: битрейт, каналы
        info = [f"Title: {title}"]
        bitrate = player.metaData("AudioBitRate")
        channels = player.metaData("ChannelCount")
        if bitrate:
            info.append(f"Bitrate: {bitrate} bps")
        if channels:
            info.append(f"Channels: {channels}")

        text = " | ".join(info)
        # Обновляем метку и заголовок окна
        self.meta_label.setText(text)
        self.setWindowTitle(f"PyQt Audio Player - {title}")

    
    def refresh_playlist_widget(self):
        """
        Перезаполняет QListWidget на основе текущего controller.playlist.
        """
        self.playlistWidget.clear()
        for tr in self.controller.playlist:
            # длительность в миллисекундах
            dur_ms = int(tr['duration'] * 1000)
            text = f"{tr['title']} — {format_time(dur_ms)}"
            self.playlistWidget.addItem(QListWidgetItem(text))

    def update_ui_for_current_track(self):
        """
        Приводит интерфейс в соответствие с текущим треком:
        – рисует формы и графики
        – обновляет заголовок и метку
        – выделяет строку в плейлисте
        – запускает таймер
        """
        idx = self.controller.current_index
        print(idx)
        if idx is None or idx < 0 or idx >= len(self.controller.playlist):
            return

        track = self.controller.playlist[idx]
        title = track.get('title', os.path.basename(track['path']))
        

        # 1. отрисовать звук
        plot_waveform(self)

        # 2. выделить в списке и обновить метку
        self.playlistWidget.setCurrentRow(idx)
        self.update_metadata()
        self.setWindowTitle(f"PyQt Audio Player - {title}")

        # 3. (если надо) перезапустить таймер
        if not self.timer.isActive():
            self.timer.start()

    def update_slider(self):
        self.slider.setValue(self.controller.player.position())
    
    
    # --Контроль показа--
    def show_view(self, view):
        self.plot_widget.setVisible(view in ('waveform', 'spectrum'))
        self.vol_plot_widget.setVisible(view == 'waveform')
        self.spec_canvas.setVisible(view == 'spectrogram')
        if view == 'waveform':
            plot_waveform(self)
        elif view == 'spectrum':
            plot_spectrum(self)
        elif view == 'spectrogram':
            plot_spectrogram(self)

    def toggle_playlist_visibility(self):
        """
        Показывает или прячет панель плейлиста по кнопке «≡».
        """
        is_visible = self.playlistWidget.isVisible()
        self.playlistWidget.setVisible(not is_visible)
    

    # --Эквалайзер--
    def apply_eq_and_refresh(self):
        # 1) Считываем гейны
        gains = [slider.value() for slider in self.eq_sliders]
        # 2) Применяем EQ
        self.controller.apply_eq(gains, self.eq_bands)
        # 3) Обновляем весь UI сразу
        self.update_ui_for_current_track()

    def reset_eq(self):
        # 1) Сбрасываем слайдеры эквалайзера
        for slider in self.eq_sliders:
            slider.setValue(0)
        # 2) Восстанавливаем оригинальный сигнал в контроллере
        idx = self.controller.current_index
        if idx is not None:
            track = self.controller.playlist[idx]
            self.controller.data = track['original_data']
            self.controller.fs   = track['original_fs']
            self.controller._set_media(track['path'])
            self.controller.player.play()
        self.update_ui_for_current_track()