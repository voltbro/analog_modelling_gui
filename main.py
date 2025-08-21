import sys

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QApplication
from MainWindow import MainWindow

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()