
import serial.tools.list_ports
import numpy as np
from PyQt6.QtWidgets import QDialog, QPushButton, QMessageBox
from PyQt6.QtGui import QIcon

from forms.ui_mainwindow import Ui_Dialog
from vb_plot import Plot
from serial_port import SerialPort

XLIM = 20.0
YLIM = 3.5

VMAX = 1024.0
VREF = 3.3

DT = 1.0 / 40.0


class MainWindow(QDialog, Ui_Dialog):
    def __init__(self):
        """
            Инициализация главного окна, настройка интерфейса, подключение сигналов и установка 
            начальных значений
        """
        # инициализация главного окна
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Аналоговое моделирование")

        # инициализация виджета Plot для отображения графика
        self.plot = Plot(1000, 400)
        self.main_layout.addWidget(self.plot)
        self.plot.set_xlim(XLIM)
        self.plot.set_ylim(YLIM*2)
        self.plot.mouse_clicked.connect(self.show_mouse_pos)

        # инициализация элементов управления
        icon = QIcon("./icons/refresh.png") 
        self.portRefreshBtn.setIcon(icon)
        self.stopBtn.setEnabled(False)
        self.ch1IcoLbl.setPixmap(QIcon("./icons/red_circle.ico").pixmap(15, 15))
        self.ch2IcoLbl.setPixmap(QIcon("./icons/blue_circle.ico").pixmap(15, 15))

        # подключение сигналов к элементам управления
        self.clearBtn.clicked.connect(self.clear_plot)
        self.startBtn.clicked.connect(self.startBtn_clicked)
        self.stopBtn.clicked.connect(self.stopBtn_clicked)
        self.portRefreshBtn.clicked.connect(self.update_comport_list)
        self.connectBtn.clicked.connect(self.connectBtn_clicked)
        self.freqSlider.valueChanged.connect(self.update_frequency)
        self.grtRadioBtn.toggled.connect(self.on_grtRadio_changed)
        self.grxyRadioBtn.toggled.connect(self.on_grxyRadio_changed)
        
        # обновление списка COM-портов
        self.update_comport_list()

        # инициализация переменных класса
        self.port = None
        self.connected = False

        self.dt = DT
        self.t = 0.0
        self.t_prev = 0.0

        self.graph_type = "g_t"
        

    def update_comport_list(self):
        """
            Обновляет список доступных COM-портов в выпадающем списке
        """
        ports = serial.tools.list_ports.comports()
        port_lst = []
        self.portComboBox.clear()
        for port, desc, hwid in sorted(ports):
            port_lst.append(f"{port} - {desc}")
        self.portComboBox.addItems(port_lst)
    
    def connectBtn_clicked(self):
        """
            Обрабатывает нажатие кнопки подключения/отключения к выбранному COM-порту. 
            Если порт не подключен, то пытается подключиться к нему, иначе отключается.
            При успешном подключении активирует кнопки управления и обновляет текст кнопки.
        """
        if self.connected == False:
            port_name = self.portComboBox.currentText().split()[0]
            if not port_name:
                QMessageBox.critical(self, "Ошибка", "Выберите COM-порт")
                return
            self.port = SerialPort(port=port_name, baudrate=57600)
            self.port.set_start_identifier("")
            self.port.set_stop_identifier("")
            self.port.data_ready.connect(self.update_plot)
            if self.port.connect():
                self.connected = True
                print(f"Connected to {port_name}")
                self.startBtn.setEnabled(True)
                self.stopBtn.setEnabled(True)
                self.clearBtn.setEnabled(True)
                self.freqSlider.setEnabled(True)
                self.connectBtn.setText("Отсоединиться")
            else:
                QMessageBox.critical(self, "Ошибка", f"Невозможно подключиться к {port_name}")
        else:
            self.port.disconnect()
            self.port = None
            self.connected = False
            self.startBtn.setEnabled(False)
            self.stopBtn.setEnabled(False)
            self.clearBtn.setEnabled(False)
            self.freqSlider.setEnabled(False)
            self.connectBtn.setText("Cоединиться")

    def clear_plot(self):
        """
            Очищает график и сбрасывает время t
        """
        self.plot.clear()
        self.t = 0.0

    def parse_raw_data(self, raw_data) -> tuple [float, float]:
        """
            Парсит входящий пакет данных со стенда, возвращает значения двух каналов.
            
            Args:
                raw_data (bytes): Сырые данные от устройства.
            Returns:
                tuple: (ch1, ch2) — значения каналов в вольтах.
            Raises:
                ValueError: Если данные некорректны или не соответствуют формату.
        """
        if len(raw_data) < 12:
            raise ValueError("Недостаточно данных для разбора пакета")
        if raw_data[0] != 98 or raw_data[1] != 98:
            raise ValueError("Пакет не начинается с синхросимволов 'bb'")
        
        ch1 = VREF * int.from_bytes(raw_data[6:8], byteorder="big", signed=False) / VMAX
        ch2 = VREF * int.from_bytes(raw_data[8:10], byteorder="big", signed=False) / VMAX
        return ch1, ch2

    def update_plot(self, raw_data):
        """
            Обновляет график новыми данными, полученными со стенда
            Args:
                raw_data (bytes): Сырые данные от устройства.
        """
        try:
            ch1, ch2 = self.parse_raw_data(raw_data)
        except ValueError as e:
            print(f"Ошибка разбора данных: {e}")
            return

        if self.graph_type == "g_t":
            self.t %= XLIM
            if self.t_prev != self.t:
                self.clear_plot()
            self.plot.add_point(0, self.t, ch1)
            self.plot.add_point(1, self.t, ch2)
            self.t += self.dt
            self.t_prev = self.t
        else:
            self.plot.add_point(0, ch1, ch2)

        self.ch1ValueLbl.setText(f"{ch1:.2f}")
        self.ch2ValueLbl.setText(f"{ch2:.2f}")

    def update_frequency(self, value):
        """
            Обновляет частоту генератора на стенде в соответствии с положением слайдера
            Args:
                value (int): Значение слайдера, определяющее частоту
        """
        if self.port is not None:
            self.freqLbl.setText(f"{value}")
            self.port.send_data(bytes([value]))

    def startBtn_clicked(self):
        """
            Обрабатывает нажатие кнопки 'Старт', отправляет команду перехода стенда
            в режим передачи данных
        """
        if self.port is not None:
            self.port.send_data(bytes([0xff]))
            self.startBtn.setEnabled(False)
            self.stopBtn.setEnabled(True)

    def stopBtn_clicked(self):
        """
            Обрабатывает нажатие кнопки 'Стоп', отправляет команду перехода стенда
            в ждущий режим
        """
        if self.port is not None:
            self.port.send_data(bytes([0x00]))
            self.startBtn.setEnabled(True)
            self.stopBtn.setEnabled(False)

    def show_mouse_pos(self, x, y):
        """
            Обрабатывает событие нажатия мыши на графике, отображает координаты клика
            Args:
                x (float): Координата X клика в графических координатах
                y (float): Координата Y клика в графических координатах
        """
        self.mouse_x_lbl.setText(f"{x:.2f}")
        self.mouse_y_lbl.setText(f"{y:.2f}")

    def on_grtRadio_changed(self):
        """
            Переключает режим отображения графика на зависимость сигналов от времени
        """
        self.graph_type = "g_t"
        self.clear_plot()

    def on_grxyRadio_changed(self):
        """
            Переключает режим отображения графика на зависимость одного сигнала от другого
        """
        self.graph_type = "g_xy"
        self.clear_plot()

    def closeEvent(self, event):
        """
            Обрабатывает событие закрытия окна. Отключает порт, если он подключен.
        """
        if self.connected and self.port is not None:
            self.port.send_data(bytes([0x00]))
            self.port.disconnect()
        super().closeEvent(event)