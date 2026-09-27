"""Кольцевой двусвязный список."""

from __future__ import annotations

from typing import Any, Iterable, Iterator


class LinkedListItem:
    """Узел двусвязного списка."""

    def __init__(self, data):
        self._data = data
        self._next_item: LinkedListItem | None = None
        self._previous_item: LinkedListItem | None = None

    @property
    def data(self) -> Any:
        """Данные узла."""
        return self._data

    @property
    def next_item(self):
        """Следующий узел."""
        return self._next_item

    @next_item.setter
    def next_item(self, value: LinkedListItem | None) -> None:
        self._next_item = value
        if value is not None and value.previous_item is not self:
            value.previous_item = self

    @property
    def previous_item(self):
        """Предыдущий узел."""
        return self._previous_item

    @previous_item.setter
    def previous_item(self, value: LinkedListItem | None) -> None:
        self._previous_item = value
        if value is not None and value.next_item is not self:
            value.next_item = self


class LinkedList:
    """Кольцевой двусвязный список."""

    def __init__(self, items: Iterable[Any] | None = None) -> None:
        self.first_item: LinkedListItem | None = None
        self._length: int = 0
        self._cursor: LinkedListItem | None = None
        self._steps: int = 0
        for item in items or ():
            self.append_right(item)

    @staticmethod
    def _to_item(item: Any) -> LinkedListItem:
        return item if isinstance(item, LinkedListItem) else LinkedListItem(item)

    def _nodes(self) -> Iterator[LinkedListItem]:
        node = self.first_item
        for _ in range(self._length):
            assert node is not None
            yield node
            node = node.next_item

    def _find(self, item: Any) -> LinkedListItem:
        for node in self._nodes():
            if node is item or node.data == item:
                return node
        raise ValueError(f"{item!r} not in list")

    @staticmethod
    def _link_after(previous: LinkedListItem, node: LinkedListItem) -> None:
        following = previous.next_item
        previous.next_item = node
        node.next_item = following

    def append_right(self, item: Any) -> None:
        """Добавление элемента в конец списка."""
        node = self._to_item(item)
        if self.first_item is None:
            node.next_item = node
            self.first_item = node
        else:
            last = self.first_item.previous_item
            assert last is not None
            self._link_after(last, node)
        self._length += 1

    append = append_right

    def append_left(self, item: Any) -> None:
        """Добавление элемента в начало списка."""
        self.append_right(item)
        assert self.first_item is not None
        self.first_item = self.first_item.previous_item

    def insert(self, previous: Any, item: Any) -> None:
        """Вставить item после элемента previous."""
        previous_node = self._find(previous)
        self._link_after(previous_node, self._to_item(item))
        self._length += 1

    def remove(self, item: Any) -> None:
        """Удалить элемент item из списка."""
        node = self._find(item)
        if self._length == 1:
            self.first_item = None
        else:
            previous, following = node.previous_item, node.next_item
            assert previous is not None and following is not None
            previous.next_item = following  # заодно following.previous_item
            if node is self.first_item:
                self.first_item = following
        node.next_item = None
        node.previous_item = None
        self._length -= 1

    def last(self) -> LinkedListItem | None:
        """Последний узел или None, если список пуст."""
        return self.first_item.previous_item if self.first_item else None

    def __len__(self) -> int:
        return self._length

    def __iter__(self) -> LinkedList:
        self._cursor = self.first_item
        self._steps = 0
        return self

    def __next__(self) -> Any:
        if self._steps >= self._length or self._cursor is None:
            raise StopIteration
        data = self._cursor.data
        self._cursor = self._cursor.next_item
        self._steps += 1
        return data

    def move(self, src: int, dst: int) -> None:
        """Переставить элемент с позиции src на позицию dst."""
        if src == dst:
            return
        node = self._node_at(src)
        self._node_at(dst)
        self.remove(node)
        if dst == 0:
            self.append_left(node)
        else:
            self.insert(self._node_at(dst - 1), node)

    def __getitem__(self, index: int) -> Any:
        return self._node_at(index).data

    def _node_at(self, index: int) -> LinkedListItem:
        """Узел по индексу, отрицательные индексы считаются с конца."""
        if not isinstance(index, int):
            raise TypeError("index must be int")
        if index < 0:
            index += self._length
        if not 0 <= index < self._length:
            raise IndexError("list index out of range")
        node = self.first_item
        assert node is not None
        if index <= self._length // 2:
            for _ in range(index):
                node = node.next_item
                assert node is not None
        else:
            for _ in range(self._length - index):
                node = node.previous_item
                assert node is not None
        return node

    def __contains__(self, item: Any) -> bool:
        return any(node.data == item for node in self._nodes())

    def __reversed__(self) -> Iterator[Any]:
        node = self.last()
        for _ in range(self._length):
            assert node is not None
            yield node.data
            node = node.previous_item
