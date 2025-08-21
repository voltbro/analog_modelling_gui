from PyQt6 import QtWidgets, QtGui
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal



class Plot(QtWidgets.QWidget):
    """
    Кастомный виджет для отображения двух линий на графике с поддержкой масштабирования 
    и событий мыши. 
    Потенциально можно расширить для большего количества линий, но такая
    возможность еще не тестирвалась. Чтобы эта возможность заработала, нужно изменить
    функцию __init_lines и добавить в нее возможность динамического создания линий и их 
    стилей.
    """
    mouse_clicked = pyqtSignal(float, float)

    LINE_WIDTH = 2
    AXIS_OFFSET = 5
    LINE_COUNT = 2

    def __init__(self, size_x: int = 800, size_y: int = 400, *args, **kwargs) -> None:
        """
        Инициализация графического виджета Plot.
        Args:
            size_x (int): ширина области рисования.
            size_y (int): высота области рисования.
        """
        super().__init__(*args, **kwargs)
        self.size_x = size_x
        self.size_y = size_y

        layout = QtWidgets.QVBoxLayout()
        self.graphics_label = QLabel()
        layout.addWidget(self.graphics_label)

        self.clear()
        self.setLayout(layout)

        self.line_prev_x = [0.0] * self.LINE_COUNT
        self.line_prev_y = [0.0] * self.LINE_COUNT
        self.line_pen = [0.0] * self.LINE_COUNT
        self.first_line = [True] * self.LINE_COUNT

        self.__init_lines()

        self.x_scale = 1.0
        self.y_scale = 1.0


    def __draw_axis(self) -> None:
        """Рисует оси координат на canvas."""
        canvas = self.graphics_label.pixmap()
        pen = QtGui.QPen()
        pen.setWidth(2)
        pen.setColor(QtGui.QColor('gray'))
        painter = QtGui.QPainter(canvas)
        painter.setPen(pen)
        painter.drawLine(self.AXIS_OFFSET, 0, self.AXIS_OFFSET, int(self.size_y))
        painter.drawLine(self.AXIS_OFFSET, int(self.size_y / 2), int(self.size_x), int(self.size_y / 2))
        painter.end()
        self.graphics_label.setPixmap(canvas)

    def __init_lines(self) -> None:
        """Инициализирует стили линий для графика."""
        self.line_pen[0] = QtGui.QPen()
        self.line_pen[0].setWidth(self.LINE_WIDTH)
        self.line_pen[0].setColor(QtGui.QColor('red'))

        self.line_pen[1] = QtGui.QPen()
        self.line_pen[1].setWidth(self.LINE_WIDTH)
        self.line_pen[1].setColor(QtGui.QColor('blue'))

    def set_xlim(self, xlim: float) -> None:
        """Устанавливает масштаб по оси X."""
        self.x_scale = self.size_x / xlim

    def set_ylim(self, ylim: float) -> None:
        """Устанавливает масштаб по оси Y."""
        self.y_scale = self.size_y / ylim

    def add_point(self, line_num: int, x: float, y: float) -> None:
        """Добавляет точку на график для заданной линии."""
        y *= -1
        if self.first_line[line_num]:
            self.line_prev_x[line_num] = x
            self.line_prev_y[line_num] = y
            self.first_line[line_num] = False

        canvas = self.graphics_label.pixmap()
        painter = QtGui.QPainter(canvas)
        painter.setPen(self.line_pen[line_num])
        painter.drawLine(
            int(self.line_prev_x[line_num] * self.x_scale) + self.AXIS_OFFSET,
            int(self.line_prev_y[line_num] * self.y_scale + self.size_y / 2),
            int(x * self.x_scale) + self.AXIS_OFFSET,
            int(y * self.y_scale + self.size_y / 2)
        )
        painter.end()
        self.graphics_label.setPixmap(canvas)

        self.line_prev_x[line_num] = x
        self.line_prev_y[line_num] = y

    def clear(self) -> None:
        """Очищает график и рисует оси."""
        self.first_line = [True] * self.LINE_COUNT
        canvas = QPixmap(self.size_x, self.size_y)
        canvas.fill(Qt.GlobalColor.white)
        self.graphics_label.setPixmap(canvas)
        self.__draw_axis()

    def mousePressEvent(self, event) -> None:
        """
        Обрабатывает нажатие мыши по графику и отправляет сигнал с координатами
        клика в графических координатах.
        Args:
            event: Событие мыши.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.graphics_label.mapFromParent(event.position().toPoint())
            px, py = pos.x(), pos.y()
            graph_x = (px - self.AXIS_OFFSET) / self.x_scale
            graph_y = - (py - self.size_y / 2) / self.y_scale
            self.mouse_clicked.emit(graph_x, graph_y)
