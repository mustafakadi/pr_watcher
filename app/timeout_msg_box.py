from app.msg_box_definitions import BTNS_LIST
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox, QDesktopWidget, QPushButton
from PyQt5.QtCore import pyqtSignal


class StatusUpdThread(QtCore.QThread):

    def __init__(self, timeout, msg_box):
        super().__init__()
        self.timeout = timeout
        self.msgBox = msg_box
        self.threadActive = True
        self.rspReceived = False

    def run(self):
        while self.timeout >= 0 and self.threadActive:
            self.msgBox.updContentSignal.emit(self.timeout)
            self.timeout -= 1
            self.rspReceived = False
            while not self.rspReceived:
                pass
            self.sleep(1)
        self.msgBox.closeSignal.emit(1)

    def stop(self):
        self.threadActive = False
        self.wait()

    def set_rsp(self):
        self.rspReceived = True


class MsgBoxButton(QPushButton):
    def __init__(self, button_text):
        super().__init__()
        self.setText(button_text)

    def enterEvent(self, *args, **kwargs):
        print('Enter!-' + self.text())

    def leaveEvent(self, *args, **kwargs):
        print('Leave!-' + self.text())


def _seconds_to_time_str(seconds):
    time_sec = str(seconds % 60)
    time_min = str(int(seconds / 60))
    return time_min + ':' + time_sec


class TimeoutMsgBox(QMessageBox):
    updContentSignal = pyqtSignal(int)
    closeSignal = pyqtSignal(int)

    def __init__(self, parent, msg, timeout, activate_timeout, msg_box_buttons):
        super().__init__(parent)
        self.parent = parent
        self.width = 360
        self.height = 200
        self.box_msg = msg
        self.box_timeout = timeout
        self.activate_timeout = activate_timeout
        self.content_upd_thread = None
        self.init_ui(timeout, msg_box_buttons)

    def init_ui(self, timeout, msg_box_buttons):
        self.setIcon(QMessageBox.Information)
        self.setWindowTitle('PR Watcher')
        self.setGeometry(10, 10, self.width, self.height)
        qt_rectangle = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

        if self.activate_timeout:
            self.setText(self.boxMsg + "\n(Closing in {0} seconds)".format(self.box_timeout - 1))
        else:
            self.setText(self.boxMsg)
        self.setStandardButtons(QMessageBox.NoButton)
        # self.msgBoxBtnList = []
        for msgBoxBtn in msg_box_buttons:
            if msgBoxBtn in BTNS_LIST:
                self.addButton(MsgBoxButton(msgBoxBtn), QMessageBox.AcceptRole)
                # self.addButton(msgBoxBtn, QMessageBox.HelpRole)
        self.buttonClicked.connect(self.btn_click_control)

        self.updContentSignal.connect(self.update_content)
        self.closeSignal.connect(self.close_self)

        if self.activate_timeout:
            self.content_upd_thread = StatusUpdThread(timeout, self)
            self.content_upd_thread.start()

    def btn_click_control(self, btn):
        print("btn-" + btn.text())
        self.parent.responseSignal.emit(btn.text())

    def closeEvent(self, event):
        # self.timer.stop()
        if self.activate_timeout:
            self.content_upd_thread.stop()
        event.accept()

    @QtCore.pyqtSlot(int)
    def update_content(self, time_left):
        self.setText(self.boxMsg + "\n{0} seconds left".format(time_left))
        self.content_upd_thread.set_rsp()

    @QtCore.pyqtSlot(int)
    def close_self(self, value):
        if value != 1:
            return
        self.close()

    def leaveEvent(self, *args, **kwargs):
        print('BOXLeave')

    def enterEvent(self, *args, **kwargs):
        print('BOXEnter')
