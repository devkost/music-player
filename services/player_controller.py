"""Контроллер плеера: связывает окно, плейлисты и pygame."""

from functools import lru_cache

import pygame
from PySide6 import QtCore

from models.composition import Composition
from models.playlist import PlayList
from ui.main_window import MainWindow


@lru_cache(maxsize=None)
def track_length_ms(file_path: str) -> int:
    """Длительность аудиофайла в миллисекундах."""
    try:
        return int(pygame.mixer.Sound(file_path).get_length() * 1000)
    except pygame.error:
        return 0


class PlayerController:
    """Принимает сигналы окна, работает с плейлистами и обновляет экран."""

    def __init__(self, window: MainWindow) -> None:
        """Сохранить окно, подготовить состояние и подключить сигналы."""
        pygame.mixer.init()
        self.window = window
        self.playlists: list[PlayList] = []
        self.active: PlayList | None = None
        self.playing: PlayList | None = None

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._check_track_end)
        self._timer.start(500)

        self._progress_timer = QtCore.QTimer()
        self._progress_timer.timeout.connect(self._update_position)
        self._progress_timer.start(200)
        self._start_offset_ms = 0

        self._connect_signals()

    def _connect_signals(self) -> None:
        """Подключить сигналы окна к методам контроллера."""
        window = self.window
        window.playlist_create_requested.connect(self.create_playlist)
        window.playlist_delete_requested.connect(self.delete_playlist)
        window.playlist_selected.connect(self.select_playlist)

        window.tracks_add_requested.connect(self.add_tracks)
        window.track_remove_requested.connect(self.remove_track)
        window.track_move_requested.connect(self.move_track)

        window.play_requested.connect(self.play)
        window.pause_requested.connect(self.pause)
        window.next_requested.connect(self.next_track)
        window.previous_requested.connect(self.previous_track)
        window.seek_requested.connect(self.seek)
        window.volume_changed.connect(self.set_volume)

    # Плейлисты

    def create_playlist(self, name: str) -> None:
        """Создать плейлист с названием name и показать его в окне."""
        self.playlists.append(PlayList(name))
        self.window.set_playlists(
            [p.name for p in self.playlists], len(self.playlists) - 1
        )

    def delete_playlist(self, index: int) -> None:
        """Удалить плейлист с индексом index и обновить окно."""
        playlist = self.playlists.pop(index)
        if playlist is self.playing:
            pygame.mixer.music.stop()
            self.playing = None
            self.window.set_playing(False)
            self.window.set_current_track(-1)
            self.window.set_duration(0)
            self.window.set_position(0)
        if playlist is self.active:
            self.active = None
        self.window.set_playlists([p.name for p in self.playlists])

    def select_playlist(self, index: int) -> None:
        """Сделать плейлист активным и показать его композиции."""
        self.active = self.playlists[index] if index >= 0 else None
        if self.active is None:
            self.window.set_tracks([])
            return
        self.window.set_tracks([str(track) for track in self.active])
        self._highlight_current()

    # Композиции

    def add_tracks(self, paths: list[str]) -> None:
        """Добавить файлы paths в активный плейлист."""
        current_playlist = self.active
        if current_playlist is not None:
            for path in paths:
                current_playlist.append(Composition(path))
            self.window.set_tracks([str(track) for track in self.active])

    def remove_track(self, index: int) -> None:
        """Удалить композицию index из активного плейлиста."""
        if self.active is None:
            return
        track = self.active[index]
        self.active.remove(track)
        self.window.set_tracks([str(t) for t in self.active])

    def move_track(self, src: int, dst: int) -> None:
        """Переставить композицию с позиции src на позицию dst."""
        if self.active is None:
            return
        self.active.move(src, dst)

    # Воспроизведение

    def play(self, index: int) -> None:
        """Играть композицию index или продолжить, если index равен -1."""
        if index == -1 and self.playing is not None:
            self._resume()
            return
        if self.active is None or len(self.active) == 0:
            return
        if index == -1:
            index = 0
        composition = self.active[index]
        if self.active is self.playing and composition is self.playing.current:
            self._resume()
            return
        self.active.play_all(composition)
        self.playing = self.active
        self._start_current()

    def pause(self) -> None:
        """Поставить воспроизведение на паузу."""
        pygame.mixer.music.pause()
        self.window.set_playing(False)

    def next_track(self) -> None:
        """Перейти к следующей композиции и включить её."""
        if self.playing is None or len(self.playing) == 0:
            return
        self.playing.next_track()
        self._start_current()

    def previous_track(self) -> None:
        """Перейти к предыдущей композиции и включить её."""
        if self.playing is None or len(self.playing) == 0:
            return
        self.playing.previous_track()
        self._start_current()

    def _resume(self) -> None:
        """Продолжить воспроизведение после паузы."""
        pygame.mixer.music.unpause()
        self.window.set_playing(True)

    def _start_current(self) -> None:
        """Включить текущую композицию играющего плейлиста и обновить окно."""
        if self.playing is None:
            return
        music = self.playing.current
        if music is None:
            return
        pygame.mixer.music.load(music.file_path)
        pygame.mixer.music.play()
        self._start_offset_ms = 0
        self.window.set_duration(track_length_ms(music.file_path))
        self.window.set_position(0)
        self.window.set_playing(True)
        self._highlight_current()

    def _highlight_current(self) -> None:
        """Показать играющую композицию в окне."""
        if self.playing is None or self.playing.current is None:
            self.window.set_current_track(-1)
            return
        index = self._current_index() if self.playing is self.active else -1
        self.window.set_current_track(index, self.playing.current.title)

    def _current_index(self) -> int:
        """Номер текущей композиции в играющем плейлисте или -1."""
        if self.playing is None:
            return -1
        for index, track in enumerate(self.playing):
            if track is self.playing.current:
                return index
        return -1

    def seek(self, position_ms: int) -> None:
        """Перемотать текущую композицию на position_ms миллисекунд."""
        if self.playing is None or self.playing.current is None:
            return
        was_paused = not pygame.mixer.music.get_busy()
        try:
            pygame.mixer.music.play(start=position_ms / 1000)
        except pygame.error:
            pygame.mixer.music.play()
            position_ms = 0
        self._start_offset_ms = position_ms
        if was_paused:
            pygame.mixer.music.pause()
        self.window.set_position(position_ms)

    def _update_position(self) -> None:
        """Передвинуть полосу воспроизведения, пока играет музыка."""
        if self.playing is None or not pygame.mixer.music.get_busy():
            return
        played_ms = pygame.mixer.music.get_pos()
        if played_ms >= 0:
            self.window.set_position(self._start_offset_ms + played_ms)

    def set_volume(self, value: int) -> None:
        """Установить громкость."""
        pygame.mixer.music.set_volume(value / 100)

    def _check_track_end(self) -> None:
        """Завершение композиции."""
        if self.playing is None:
            return
        if pygame.mixer.music.get_busy() or pygame.mixer.music.get_pos() != -1:
            return

        self.next_track()
