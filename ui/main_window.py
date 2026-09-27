"""Главное окно плеера на PySide6."""

from PySide6 import QtCore, QtGui, QtWidgets

AUDIO_FILTER = "Аудио (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;Все файлы (*)"


def format_ms(ms: int) -> str:
    """Перевести миллисекунды в строку вида м:сс."""
    seconds = max(ms, 0) // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


def standard_icon(
    widget: QtWidgets.QWidget, kind: QtWidgets.QStyle.StandardPixmap
) -> QtGui.QIcon:
    """Получить стандартную иконку текущего стиля."""
    return widget.style().standardIcon(kind)


class PlaylistsPanel(QtWidgets.QGroupBox):
    """Панель со списком плейлистов и кнопками создания и удаления."""

    create_requested = QtCore.Signal(str)
    delete_requested = QtCore.Signal(int)
    selected = QtCore.Signal(int)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Создать виджеты панели."""
        super().__init__("Плейлисты", parent)

        self.list_widget = QtWidgets.QListWidget()
        self.btn_create = QtWidgets.QPushButton("Создать")
        self.btn_delete = QtWidgets.QPushButton("Удалить")

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.btn_create)
        buttons.addWidget(self.btn_delete)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addLayout(buttons)

        self.btn_create.clicked.connect(self.ask_create)
        self.btn_delete.clicked.connect(self.ask_delete)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self._update_buttons()

    def current_row(self) -> int:
        """Индекс выбранного плейлиста или -1."""
        return self.list_widget.currentRow()

    def current_name(self) -> str:
        """Название выбранного плейлиста или пустая строка."""
        item = self.list_widget.currentItem()
        return item.text() if item else ""

    def set_playlists(self, names: list[str], current: int = -1) -> None:
        """Показать плейлисты и выделить плейлист с индексом ``current``."""
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self.list_widget.addItems(names)
        self.list_widget.blockSignals(False)
        if current < 0 and names:
            current = 0
        self.list_widget.setCurrentRow(current)
        if current < 0:
            self._on_row_changed(-1)

    def ask_create(self) -> None:
        """Спросить название и запросить создание плейлиста."""
        name, ok = QtWidgets.QInputDialog.getText(self, "Новый плейлист", "Название:")
        name = name.strip()
        if ok and name:
            self.create_requested.emit(name)

    def ask_delete(self) -> None:
        """Подтвердить и запросить удаление выбранного плейлиста."""
        row = self.current_row()
        if row < 0:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            "Удаление плейлиста",
            f"Удалить плейлист «{self.current_name()}»?",
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(row)

    def _on_row_changed(self, row: int) -> None:
        """Сообщить о выборе другого плейлиста."""
        self._update_buttons()
        self.selected.emit(row)

    def _update_buttons(self) -> None:
        """Включить или выключить кнопки по текущему состоянию."""
        self.btn_delete.setEnabled(self.current_row() >= 0)


class TracksPanel(QtWidgets.QGroupBox):
    """Панель с композициями текущего плейлиста."""

    add_requested = QtCore.Signal(list)
    remove_requested = QtCore.Signal(int)
    move_requested = QtCore.Signal(int, int)
    activated = QtCore.Signal(int)
    changed = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Создать виджеты панели."""
        super().__init__("Композиция", parent)
        self._has_playlist = False

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove
        )
        self.list_widget.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.list_widget.setAlternatingRowColors(True)

        self.btn_add = QtWidgets.QPushButton("Добавить")
        self.btn_remove = QtWidgets.QPushButton("Удалить")
        self.btn_up = QtWidgets.QPushButton(
            standard_icon(self, QtWidgets.QStyle.StandardPixmap.SP_ArrowUp), ""
        )
        self.btn_up.setToolTip("Переместить выше")
        self.btn_down = QtWidgets.QPushButton(
            standard_icon(self, QtWidgets.QStyle.StandardPixmap.SP_ArrowDown),
            "",
        )
        self.btn_down.setToolTip("Переместить ниже")

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.btn_add)
        buttons.addWidget(self.btn_remove)
        buttons.addStretch()
        buttons.addWidget(self.btn_up)
        buttons.addWidget(self.btn_down)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addLayout(buttons)

        self._connect()
        self._update_buttons()

    def _connect(self) -> None:
        """Подключить сигналы виджетов панели."""
        self.btn_add.clicked.connect(self.ask_add)
        self.btn_remove.clicked.connect(self.ask_remove)
        self.btn_up.clicked.connect(lambda: self._move_selected(-1))
        self.btn_down.clicked.connect(lambda: self._move_selected(1))
        self.list_widget.itemDoubleClicked.connect(
            lambda item: self.activated.emit(self.list_widget.row(item))
        )
        self.list_widget.currentRowChanged.connect(self._update_buttons)
        self.list_widget.model().rowsMoved.connect(self._on_rows_dragged)

    def current_row(self) -> int:
        """Индекс выбранной композиции или -1."""
        return self.list_widget.currentRow()

    def count(self) -> int:
        """Количество композиций в списке."""
        return self.list_widget.count()

    def set_playlist(self, name: str) -> None:
        """Показать название плейлиста (пустая строка — плейлист не выбран)."""
        self._has_playlist = bool(name)
        self.setTitle(f"Композиции — {name}" if name else "Композиции")
        self._update_buttons()

    def set_tracks(self, titles: list[str], selected: int = -1) -> None:
        """Показать композиции и выделить композицию ``selected``."""
        self.list_widget.clear()
        self.list_widget.addItems(titles)
        if 0 <= selected < len(titles):
            self.list_widget.setCurrentRow(selected)
        self._update_buttons()

    def mark_current(self, index: int) -> str:
        """Подсветить играющую композицию и вернуть её название."""
        play_icon = standard_icon(self, QtWidgets.QStyle.StandardPixmap.SP_MediaPlay)
        for row in range(self.count()):
            item = self.list_widget.item(row)
            font = item.font()
            font.setBold(row == index)
            item.setFont(font)
            item.setIcon(play_icon if row == index else QtGui.QIcon())
        if 0 <= index < self.count():
            self.list_widget.setCurrentRow(index)
            return self.list_widget.item(index).text()
        return ""

    def ask_add(self) -> None:
        """Выбрать аудиофайлы и запросить их добавление."""
        if not self._has_playlist:
            return
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Добавить композиции", "", AUDIO_FILTER
        )
        if paths:
            self.add_requested.emit(paths)

    def ask_remove(self) -> None:
        """Запросить удаление выбранной композиции."""
        row = self.current_row()
        if row >= 0:
            self.remove_requested.emit(row)

    def _move_selected(self, step: int) -> None:
        """Сдвинуть выбранную композицию на ``step`` позиций."""
        src = self.current_row()
        dst = src + step
        if src < 0 or not 0 <= dst < self.count():
            return
        item = self.list_widget.takeItem(src)
        self.list_widget.insertItem(dst, item)
        self.list_widget.setCurrentRow(dst)
        self.move_requested.emit(src, dst)

    def _on_rows_dragged(  # pylint: disable=too-many-arguments
        self,
        _parent: QtCore.QModelIndex,
        start: int,
        _end: int,
        _destination: QtCore.QModelIndex,
        dest_row: int,
    ) -> None:
        """Сообщить о перетаскивании композиции мышью."""
        # dest_row — строка, перед которой вставили, в старой нумерации
        dst = dest_row - 1 if dest_row > start else dest_row
        if dst != start:
            self.move_requested.emit(start, dst)
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Включить или выключить кнопки по текущему состоянию."""
        row = self.current_row()
        self.btn_add.setEnabled(self._has_playlist)
        self.btn_remove.setEnabled(row >= 0)
        self.btn_up.setEnabled(row > 0)
        self.btn_down.setEnabled(0 <= row < self.count() - 1)
        self.changed.emit()


class ProgressBar(QtWidgets.QWidget):
    """Ползунок перемотки с текущим временем и длительностью."""

    seek_requested = QtCore.Signal(int)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Создать виджеты полосы прогресса."""
        super().__init__(parent)
        self._pressed = False

        self.position_label = QtWidgets.QLabel("0:00")
        self.duration_label = QtWidgets.QLabel("0:00")
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.position_label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.duration_label)

        self.slider.sliderPressed.connect(self._on_pressed)
        self.slider.sliderReleased.connect(self._on_released)
        self.slider.sliderMoved.connect(
            lambda value: self.position_label.setText(format_ms(value))
        )

    def set_duration(self, ms: int) -> None:
        """Задать длительность композиции в миллисекундах."""
        self.slider.setRange(0, ms)
        self.duration_label.setText(format_ms(ms))

    def set_position(self, ms: int) -> None:
        """Задать позицию, если пользователь не тянет ползунок."""
        if not self._pressed:
            self.slider.setValue(ms)
            self.position_label.setText(format_ms(ms))

    def _on_pressed(self) -> None:
        """Запомнить, что пользователь взял ползунок."""
        self._pressed = True

    def _on_released(self) -> None:
        """Запросить перемотку в выбранную позицию."""
        self._pressed = False
        self.seek_requested.emit(self.slider.value())


class PlayerPanel(QtWidgets.QFrame):
    """Панель управления воспроизведением."""

    play_clicked = QtCore.Signal()
    previous_clicked = QtCore.Signal()
    next_clicked = QtCore.Signal()
    volume_changed = QtCore.Signal(int)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Создать виджеты панели."""
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._is_playing = False

        self.title_label = QtWidgets.QLabel("Ничего не играет")
        font = self.title_label.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.progress = ProgressBar()
        pixmap = QtWidgets.QStyle.StandardPixmap
        self.btn_prev = self._make_button(
            pixmap.SP_MediaSkipBackward, "Предыдущая", self.previous_clicked
        )
        self.btn_play = self._make_button(
            pixmap.SP_MediaPlay, "Играть", self.play_clicked
        )
        self.btn_next = self._make_button(
            pixmap.SP_MediaSkipForward, "Следующая", self.next_clicked
        )

        volume_icon = QtWidgets.QLabel()
        volume_icon.setPixmap(standard_icon(self, pixmap.SP_MediaVolume).pixmap(18, 18))
        self.volume_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)

        controls = QtWidgets.QHBoxLayout()
        controls.addStretch()
        for button in (self.btn_prev, self.btn_play, self.btn_next):
            controls.addWidget(button)
        controls.addStretch()
        controls.addWidget(volume_icon)
        controls.addWidget(self.volume_slider)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.progress)
        layout.addLayout(controls)

    def _make_button(
        self,
        kind: QtWidgets.QStyle.StandardPixmap,
        tooltip: str,
        signal: QtCore.SignalInstance,
    ) -> QtWidgets.QToolButton:
        """Создать кнопку управления, испускающую ``signal`` по нажатию."""
        button = QtWidgets.QToolButton()
        button.setIcon(standard_icon(self, kind))
        button.setToolTip(tooltip)
        button.setIconSize(QtCore.QSize(32, 32))
        button.setAutoRaise(True)
        button.clicked.connect(signal.emit)
        return button

    @property
    def is_playing(self) -> bool:
        """Играет ли сейчас музыка."""
        return self._is_playing

    def set_playing(self, playing: bool) -> None:
        """Переключить кнопку между «Играть» и «Пауза»."""
        self._is_playing = playing
        pixmap = QtWidgets.QStyle.StandardPixmap
        kind = pixmap.SP_MediaPause if playing else pixmap.SP_MediaPlay
        self.btn_play.setIcon(standard_icon(self, kind))
        self.btn_play.setToolTip("Пауза" if playing else "Играть")

    def set_title(self, title: str) -> None:
        """Показать название играющей композиции."""
        self.title_label.setText(title or "Ничего не играет")

    def set_controls_enabled(self, has_tracks: bool) -> None:
        """Включить кнопки, если в плейлисте есть композиции."""
        self.btn_prev.setEnabled(has_tracks)
        self.btn_next.setEnabled(has_tracks)
        self.btn_play.setEnabled(has_tracks or self._is_playing)


class MainWindow(QtWidgets.QMainWindow):
    """Главное окно плейера.

    Сигналы, которые нужно подключить к логике:

    * ``playlist_create_requested(name)`` — создать плейлист;
    * ``playlist_delete_requested(index)`` — удалить плейлист;
    * ``playlist_selected(index)`` — выбран плейлист (-1 — ни одного);
    * ``tracks_add_requested(paths)`` — добавить файлы в плейлист;
    * ``track_remove_requested(index)`` — удалить композицию;
    * ``track_move_requested(from, to)`` — композиция уже переставлена
      на экране, переставьте её в плейлисте;
    * ``play_requested(index)`` — играть композицию (-1 — продолжить);
    * ``pause_requested``, ``previous_requested``, ``next_requested``;
    * ``seek_requested(ms)``, ``volume_changed(0..100)``.
    """

    playlist_create_requested = QtCore.Signal(str)
    playlist_delete_requested = QtCore.Signal(int)
    playlist_selected = QtCore.Signal(int)

    tracks_add_requested = QtCore.Signal(list)
    track_remove_requested = QtCore.Signal(int)
    track_move_requested = QtCore.Signal(int, int)

    play_requested = QtCore.Signal(int)
    pause_requested = QtCore.Signal()
    previous_requested = QtCore.Signal()
    next_requested = QtCore.Signal()
    seek_requested = QtCore.Signal(int)
    volume_changed = QtCore.Signal(int)

    def __init__(self) -> None:
        """Собрать окно из панелей."""
        super().__init__()
        self.setWindowTitle("Плейер")
        self.resize(900, 560)

        self.playlists = PlaylistsPanel()
        self.tracks = TracksPanel()
        self.player = PlayerPanel()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self.playlists)
        splitter.addWidget(self.tracks)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setChildrenCollapsible(False)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.player)
        self.setCentralWidget(central)
        self.statusBar()

        self._connect_panels()
        self._add_shortcuts()
        self._update_player_controls()

    def _connect_panels(self) -> None:
        """Пробросить сигналы панелей в сигналы окна."""
        self.playlists.create_requested.connect(self.playlist_create_requested.emit)
        self.playlists.delete_requested.connect(self.playlist_delete_requested.emit)
        self.playlists.selected.connect(self._on_playlist_selected)

        self.tracks.add_requested.connect(self.tracks_add_requested.emit)
        self.tracks.remove_requested.connect(self.track_remove_requested.emit)
        self.tracks.move_requested.connect(self.track_move_requested.emit)
        self.tracks.activated.connect(self.play_requested.emit)
        self.tracks.changed.connect(self._update_player_controls)

        self.player.play_clicked.connect(self.toggle_play)
        self.player.previous_clicked.connect(self.previous_requested.emit)
        self.player.next_clicked.connect(self.next_requested.emit)
        self.player.volume_changed.connect(self.volume_changed.emit)
        self.player.progress.seek_requested.connect(self.seek_requested.emit)

    def _add_shortcuts(self) -> None:
        """Назначить горячие клавиши."""
        shortcuts = (
            (QtGui.QKeySequence(QtCore.Qt.Key.Key_Space), self.toggle_play),
            (QtGui.QKeySequence("Ctrl+Right"), self.next_requested.emit),
            (QtGui.QKeySequence("Ctrl+Left"), self.previous_requested.emit),
            (
                QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.New),
                self.playlists.ask_create,
            ),
            (
                QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Open),
                self.tracks.ask_add,
            ),
        )
        for sequence, handler in shortcuts:
            QtGui.QShortcut(sequence, self, handler)
        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Delete),
            self.tracks.list_widget,
            self.tracks.ask_remove,
        )

    def _on_playlist_selected(self, row: int) -> None:
        """Обновить заголовок композиций и сообщить о выборе плейлиста."""
        self.tracks.set_playlist(self.playlists.current_name())
        self.playlist_selected.emit(row)

    def _update_player_controls(self) -> None:
        """Включить кнопки плеера, если есть композиции."""
        self.player.set_controls_enabled(self.tracks.count() > 0)

    def toggle_play(self) -> None:
        """Запросить паузу, если музыка играет, иначе воспроизведение."""
        if self.player.is_playing:
            self.pause_requested.emit()
        else:
            self.play_requested.emit(self.tracks.current_row())

    # Методы для обновления экрана из логики плейера

    def set_playlists(self, names: list[str], current: int = -1) -> None:
        """Показать плейлисты и выделить плейлист с индексом ``current``."""
        self.playlists.set_playlists(names, current)

    def set_tracks(self, titles: list[str], selected: int = -1) -> None:
        """Показать композиции текущего плейлиста."""
        self.tracks.set_tracks(titles, selected)

    def set_current_track(self, index: int, title: str | None = None) -> None:
        """Подсветить играющую композицию (-1 — ничего не играет)."""
        shown = self.tracks.mark_current(index)
        self.player.set_title(title if title is not None else shown)

    def set_playing(self, playing: bool) -> None:
        """Переключить кнопку между «Играть» и «Пауза»."""
        self.player.set_playing(playing)
        self._update_player_controls()

    def set_duration(self, ms: int) -> None:
        """Задать длительность текущей композиции в миллисекундах."""
        self.player.progress.set_duration(ms)

    def set_position(self, ms: int) -> None:
        """Задать текущую позицию воспроизведения в миллисекундах."""
        self.player.progress.set_position(ms)

    def show_message(self, text: str, timeout_ms: int = 3000) -> None:
        """Показать короткое сообщение в строке состояния."""
        self.statusBar().showMessage(text, timeout_ms)

    def show_error(self, text: str) -> None:
        """Показать окно с ошибкой."""
        QtWidgets.QMessageBox.warning(self, "Ошибка", text)
