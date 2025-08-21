import serial
import time
import threading
from PySide6.QtCore import QObject, Signal

PACKET_LENGTH = 12


class SerialPort(QObject):
    """
    Класс для работы с последовательным портом с помощью PyQt сигналов.
    """
    data_ready = Signal(bytes)
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 500000) -> None:
        super().__init__()
        self.busy = False
        self.ack = False
        self.data = b""
        self.soft_timeout = 1.0
        self.t = 0.0
        self.port = port
        self.baudrate = baudrate
        self.data_lag = 0

        self.ser = serial.Serial()
        self.ser.baudrate = self.baudrate
        self.ser.port = self.port

        self.kill = True
        self.th1 = threading.Thread(target=self.check_callback, daemon=True)
        self.th1.start()

        self.start_symb = bytes("#", 'utf-8')
        self.stop_symb = bytes("\n", 'utf-8')


    def set_start_identifier(self, symb: str) -> None:
        """Устанавливает стартовый идентификатор для передачи данных."""
        self.start_symb = bytes(symb, 'utf-8')


    def set_stop_identifier(self, symb: str) -> None:
        """Устанавливает стоповый идентификатор для передачи данных."""
        self.stop_symb = bytes(symb, 'utf-8')


    def connect(self) -> bool:
        """Открывает последовательный порт."""
        self.kill = False
        try:
            self.ser.open()
            return True
        except serial.SerialException as e:
            print(f"Ошибка при открытии порта {self.port}: {e}")
            return False


    def disconnect(self) -> None:
        """Закрывает последовательный порт и очищает буферы."""
        self.kill = True
        self.data = b""
        if self.ser.is_open:
            self.ser.reset_input_buffer()
            self.ser.close()


    def check_callback(self) -> None:
        """Фоновый поток для чтения данных из последовательного порта."""
        buffer = b""
        while True:
            if not self.kill and self.ser.is_open:
                if self.ser.in_waiting > 0:
                    self.busy = True
                    # читаем всё, что пришло
                    buffer = self.ser.read(self.ser.in_waiting)

                    # пока хватает на целый пакет (12 байт) – разбираем
                    while len(buffer) >= PACKET_LENGTH:
                        # ищем синхросимволы 'bb'
                        if buffer[0] == 98 and buffer[1] == 98:  # 'b' == 98
                            packet = buffer[:PACKET_LENGTH]
                            buffer = buffer[PACKET_LENGTH:]

                            # сохраняем в self.data
                            self.data = packet
                            # вызываем сигнал data_ready
                            self.data_ready.emit(self.data)
                        else:
                            # сдвигаем буфер до первой 'b'
                            buffer = buffer[1:]
                else:
                    time.sleep(0.005)
            else:
                time.sleep(0.005)
            self.busy = False
            

    def send_data(self, data) -> None:
        """Отправляет данные в последовательный порт."""
        while self.busy:
            time.sleep(0.001)

        if isinstance(data, str):
            sending_data = self.start_symb + bytes(data, 'utf-8') + self.stop_symb
        elif isinstance(data, bytes):
            sending_data = self.start_symb + data + self.stop_symb
        else:
            raise RuntimeError("SerialPort.send_data(): Only 'str' and 'bytes' are supported!")
        # print(sending_data)  # Для отладки, можно раскомментировать
        self.ser.write(sending_data)


    def get_last_data(self) -> bytes:
        """Возвращает последние полученные данные."""
        return self.data
    

    def __del__(self):
        """Закрывает порт и прекращает выполнение потока при удалении объекта."""
        self.disconnect()
        self.th1.stop()
