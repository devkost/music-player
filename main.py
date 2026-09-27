"""Точка входа: запуск музыкального плеера."""

import sys

from PySide6 import QtWidgets

from services.player_controller import PlayerController
from ui.main_window import MainWindow


def main() -> int:
    """Создать приложение, показать окно и запустить цикл событий."""
    app = QtWidgets.QApplication([])

    window = MainWindow()
    window.controller = PlayerController(window)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
