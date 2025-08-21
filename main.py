import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QApplication
from MainWindow import MainWindow

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()