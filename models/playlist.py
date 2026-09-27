"""Плейлист на основе двусвязного списка."""

from models.composition import Composition
from models.linked_list import LinkedList, LinkedListItem


class PlayList(LinkedList):
    """Плейлист."""

    def __init__(self, name: str, items=None) -> None:
        super().__init__(items)
        self.name = name
        self._current: LinkedListItem | None = None

    @property
    def current(self) -> Composition | None:
        """Текущий трек."""
        if self._current is None:
            return None
        return self._current.data

    def play_all(self, item) -> None:
        """Начать проигрывание."""
        if len(self) == 0:
            raise ValueError("Плейлист пуст")

        self._current = self._find(item)

    def next_track(self) -> None:
        """Перейти к следующему треку."""
        if self._current is None:
            self._current = self.first_item
        else:
            self._current = self._current.next_item

    def previous_track(self) -> None:
        """Перейти к предыдущему треку."""
        if self._current is None:
            self._current = self.last()
        else:
            self._current = self._current.previous_item
