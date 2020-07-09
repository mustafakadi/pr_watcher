"""
Main module for the application
"""
import sys
import webbrowser
import ctypes
import threading
import setuptools
from app import win_registry_management, colors_def as colors, constants_def as constants, bitbucket_rest_interaction
from app.exception_definitions import reg_key_cannot_be_read_error
from app.pr_list_manager import PrListManager, PRInProgressAction
from app.timeout_msg_box import TimeoutMsgBox
from app.repo_info import RepoInfo
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QLabel, QDialog, QDesktopWidget, QPushButton, QLineEdit, \
    QScrollArea, QFormLayout, QGroupBox, QMessageBox
from PyQt5.QtGui import QIcon, QIntValidator, QRegExpValidator
from PyQt5.QtCore import pyqtSignal, Qt, QRegExp

"""
Module related global constants and variable definitions
"""
exit_flag = threading.Event()
test = upd_test = False
version_no = str(setuptools.version)


def _get_pr_url(pr_id):
    repo_info = RepoInfo.get_instance()
    return 'https://' + repo_info.server_address + '/git/projects/' + repo_info.project_name + \
           '/repos/' + repo_info.repo_name + '/pull-requests/PR-' + str(pr_id)


class _BasicPR:
    """
    Basic PR definition
    :param pr_id: String representation of the PR id
    :param link: String representation of the link of the PR
    :param status: String representation of the built status of the PR
    """

    def __init__(self, pr_id, link, status):
        self.id = pr_id
        self.link = link
        self.status = status
        self.commentCnt = 0

    def __str__(self):
        return "ID: " + self.id + ", LINK: " + self.link + ", STATUS: " + self.status + ", COMMENT CNT: " + \
               str(self.commentCnt)


class _PRLineEdit(QLineEdit):
    def focusInEvent(self, focus_event):
        if "PR" in self.text():
            self.setText("")

    def focusOutEvent(self, focus_event):
        if self.text() == "":
            self.setText("Enter the Link of the PR to be watched!")


class _PrListIdLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.id = ""
        self.parentSign = None

    def mouseDoubleClickEvent(self, *args, **kwargs):
        if self.underMouse():
            webbrowser.open_new_tab(_get_pr_url(self.id))

    def mouseReleaseEvent(self, mouse_event):
        print(mouse_event.button())
        print(Qt.RightButton)
        if self.underMouse() and mouse_event.button() == Qt.RightButton:
            self.parentSign.deleteSig.emit(1, self.id, "Are you sure, you want to remove PR-" + self.id +
                                           "\nfrom watch-list?")


class _SettingsEditLine(QLineEdit):
    def __init__(self, line_parent, initial_text):
        super().__init__(parent=line_parent)
        self.initial_text = initial_text
        self.setText(initial_text)
        self.textChanged.connect(self.text_changed)

    def text_changed(self):
        self.parent().edit_line_updated_sig.emit()


class _SettingsWindow(QDialog):
    edit_line_updated_sig = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent, QtCore.Qt.WindowCloseButtonHint)
        self.title = 'Settings'
        self.left = constants.HORIZONTAL_PADDING
        self.top = constants.VERTICAL_PADDING
        self.width = constants.OPTIONS_WIDTH
        self.access_token_edit_line = None
        self.server_address_edit_line = None
        self.project_name_edit_line = None
        self.repo_name_edit_line = None
        self.api_version_edit_line = None
        self.apply_button = None

        self.access_token = ""
        self.server_address = ""
        self.project_name = ""
        self.repo_name = ""
        self.api_version = ""

        self.init_ui()

    def init_ui(self):
        self.init_registry_tokens()
        self.access_token_edit_line = _SettingsEditLine(self, self.access_token)
        self.server_address_edit_line = _SettingsEditLine(self, self.server_address)
        self.project_name_edit_line = _SettingsEditLine(self, self.project_name)
        self.repo_name_edit_line = _SettingsEditLine(self, self.repo_name)
        self.api_version_edit_line = _SettingsEditLine(self, self.api_version)
        self.apply_button = QPushButton(self)

        window_height = constants.VERTICAL_PADDING

        self.setWindowIcon(QIcon(constants.APP_ICON))
        self.setWindowTitle(self.title)

        """ Access Token Group """
        token_label = QLabel(self)
        token_label.setText('Enter the Generated Access Token:')
        token_label.setGeometry(constants.HORIZONTAL_PADDING, window_height, self.width, constants.DEFAULT_LABEL_HEIGHT)
        window_height += token_label.height() + constants.VERTICAL_SPACE

        self.access_token_edit_line.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                                                self.width - constants.HORIZONTAL_PADDING -
                                                constants.HORIZONTAL_PADDING, constants.DEFAULT_LABEL_HEIGHT)
        window_height += self.access_token_edit_line.height() + constants.VERTICAL_SPACE

        """ API Version Group """
        api_version_label = QLabel(self)
        api_version_label.setText('Enter the Api Version (e.g. 1.0):')
        api_version_label.setGeometry(constants.HORIZONTAL_PADDING, window_height, self.width,
                                      constants.DEFAULT_LABEL_HEIGHT)
        window_height += api_version_label.height() + constants.VERTICAL_SPACE

        regexp = QRegExp('^[0-9]{1,2}.[0-9]{1,2}')
        self.api_version_edit_line.setValidator(QRegExpValidator(regexp))
        self.api_version_edit_line.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                                               self.width - constants.HORIZONTAL_PADDING -
                                               constants.HORIZONTAL_PADDING, constants.DEFAULT_LABEL_HEIGHT)
        window_height += self.api_version_edit_line.height() + constants.VERTICAL_SPACE

        """ Server Address Group """
        server_address_label = QLabel(self)
        server_address_label.setText('Enter the Server Address (e.g. api.bitbucket.org):')
        server_address_label.setGeometry(constants.HORIZONTAL_PADDING, window_height, self.width,
                                         constants.DEFAULT_LABEL_HEIGHT)
        window_height += server_address_label.height() + constants.VERTICAL_SPACE

        self.server_address_edit_line.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                                                  self.width - constants.HORIZONTAL_PADDING -
                                                  constants.HORIZONTAL_PADDING, constants.DEFAULT_LABEL_HEIGHT)
        window_height += self.server_address_edit_line.height() + constants.VERTICAL_SPACE

        """ Project Name Group """
        project_name_label = QLabel(self)
        project_name_label.setText('Enter the Project Name:')
        project_name_label.setGeometry(constants.HORIZONTAL_PADDING, window_height, self.width,
                                       constants.DEFAULT_LABEL_HEIGHT)
        window_height += project_name_label.height() + constants.VERTICAL_SPACE

        self.project_name_edit_line.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                                                self.width - constants.HORIZONTAL_PADDING -
                                                constants.HORIZONTAL_PADDING, constants.DEFAULT_LABEL_HEIGHT)
        window_height += self.project_name_edit_line.height() + constants.VERTICAL_SPACE

        """ Repo Name Group """
        repo_name_label = QLabel(self)
        repo_name_label.setText('Enter the Repo Name:')
        repo_name_label.setGeometry(constants.HORIZONTAL_PADDING, window_height, self.width,
                                    constants.DEFAULT_LABEL_HEIGHT)
        window_height += repo_name_label.height() + constants.VERTICAL_SPACE

        self.repo_name_edit_line.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                                             self.width - constants.HORIZONTAL_PADDING -
                                             constants.HORIZONTAL_PADDING, constants.DEFAULT_LABEL_HEIGHT)
        window_height += self.repo_name_edit_line.height() + constants.VERTICAL_SPACE

        """ Apply Button """
        self.apply_button.setEnabled(False)
        self.apply_button.setText("Apply")
        self.apply_button.setGeometry(constants.HORIZONTAL_PADDING, window_height, constants.DEFAULT_BTN_WIDTH,
                                      constants.DEFAULT_BTN_HEIGHT)
        self.apply_button.clicked.connect(self.apply_button_clicked)
        window_height += self.apply_button.height() + constants.VERTICAL_PADDING

        self.setGeometry(self.top, self.left, self.width, window_height)
        qt_rectangle = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

        self.setFixedHeight(window_height)
        self.setFixedWidth(self.width)

        self.edit_line_updated_sig.connect(self.edit_line_updated)

    def apply_button_clicked(self):
        print("ADD TOKEN BUTTON CLICKED")
        result_msg = "Result:"
        repo_info = RepoInfo.get_instance()

        if self.access_token != self.access_token_edit_line.text():
            curr_access_token = self.access_token_edit_line.text()
            if win_registry_management.write_reg_key(win_registry_management.REG_ACCESS_TOKE_NAME, curr_access_token):
                repo_info.access_token = curr_access_token
                self.access_token = curr_access_token
                self.access_token_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)
                result_msg += "\n - Token Added Successfully"
            else:
                result_msg += "\n - Token Cannot be Added"

        if self.api_version != self.api_version_edit_line.text():
            curr_api_version = self.api_version_edit_line.text()
            if win_registry_management.write_reg_key(win_registry_management.REG_API_VERSION_NAME, curr_api_version):
                repo_info.api_version = curr_api_version
                self.api_version = curr_api_version
                self.api_version_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)
                result_msg += "\n - API Version Added Successfully"
            else:
                result_msg += "\n - API Version Cannot be Added"

        if self.server_address != self.server_address_edit_line.text():
            curr_server_address = self.server_address_edit_line.text()
            if win_registry_management.write_reg_key(win_registry_management.REG_SERVER_ADDRESS_NAME,
                                                     curr_server_address):
                repo_info.server_address = curr_server_address
                self.server_address = curr_server_address
                self.server_address_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)
                result_msg += "\n - Server Address Added Successfully"
            else:
                result_msg += "\n - Server Address Cannot be Added"

        if self.project_name != self.project_name_edit_line.text():
            curr_project_name = self.project_name_edit_line.text()
            if win_registry_management.write_reg_key(win_registry_management.REG_PROJECT_NAME, curr_project_name):
                repo_info.project_name = curr_project_name
                self.project_name = curr_project_name
                self.project_name_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)
                result_msg += "\n - Project Name Added Successfully"
            else:
                result_msg += "\n - Project Name Cannot be Added"

        if self.repo_name != self.repo_name_edit_line.text():
            curr_repo_name = self.repo_name_edit_line.text()
            if win_registry_management.write_reg_key(win_registry_management.REG_REPO_NAME, curr_repo_name):
                repo_info.repo_name = curr_repo_name
                self.repo_name = curr_repo_name
                self.repo_name_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)
                result_msg += "\n - Repo Name Added Successfully"
            else:
                result_msg += "\n - Repo Name Cannot be Added"

        self.parent().notifSig.emit(1, result_msg)

    def init_registry_tokens(self):
        try:
            self.access_token = win_registry_management.read_reg_key(win_registry_management.REG_ACCESS_TOKE_NAME)
            self.api_version = win_registry_management.read_reg_key(win_registry_management.REG_API_VERSION_NAME)
            self.server_address = win_registry_management.read_reg_key(win_registry_management.REG_SERVER_ADDRESS_NAME)
            self.project_name = win_registry_management.read_reg_key(win_registry_management.REG_PROJECT_NAME)
            self.repo_name = win_registry_management.read_reg_key(win_registry_management.REG_REPO_NAME)
        except reg_key_cannot_be_read_error.RegKeyCannotBeReadError as e:
            self.parent().notifSig.emit(1, "An Error Occurred While Trying to Read the Value of the Key: " + e.key_name)

    @QtCore.pyqtSlot()
    def edit_line_updated(self):
        enable_button = False
        if self.access_token != self.access_token_edit_line.text():
            enable_button = True
            self.access_token_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_CHANGED)
        else:
            self.access_token_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)

        if self.api_version != self.api_version_edit_line.text():
            enable_button = True
            self.api_version_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_CHANGED)
        else:
            self.api_version_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)

        if self.server_address != self.server_address_edit_line.text():
            enable_button = True
            self.server_address_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_CHANGED)
        else:
            self.server_address_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)

        if self.project_name != self.project_name_edit_line.text():
            enable_button = True
            self.project_name_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_CHANGED)
        else:
            self.project_name_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)

        if self.repo_name != self.repo_name_edit_line.text():
            enable_button = True
            self.repo_name_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_CHANGED)
        else:
            self.repo_name_edit_line.setStyleSheet(constants.EDIT_LINE_STYLESHEET_DEFAULT)

        self.apply_button.setEnabled(enable_button)


class _PRListWindow(QDialog):
    updateSig = pyqtSignal(int, str)
    notifSig = pyqtSignal(int, str)
    deleteSig = pyqtSignal(int, str, str)
    questionSig = pyqtSignal(int, str, str)
    closeMsgBoxSig = pyqtSignal()

    def __init__(self, parent_tray_app):
        super().__init__(None, QtCore.Qt.WindowCloseButtonHint)
        self.driverExec = False
        self.title = 'PR Watch-list ' + version_no
        self.left = constants.DEFAULT_WIN_LEFT
        self.top = constants.DEFAULT_WIN_TOP
        self.width = constants.DEFAULT_WIN_WIDTH
        self.progress_msg_box = None
        self.parent_tray_app = parent_tray_app
        self.addThread = None
        self.prs_list_container = QScrollArea(self)
        self.pr_id_edit_line = _PRLineEdit(self)
        self.init_ui()

    def init_ui(self):
        app_id = u'mycompany.myproduct.subproduct.version'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        self.setWindowIcon(QIcon(constants.APP_ICON))
        self.setWindowTitle(self.title)
        window_height = constants.VERTICAL_PADDING

        prs_label = QLabel(self)
        prs_label.setStyleSheet("font-size: 12px;")
        prs_label.setText('Pull Requests Watch-list:')
        prs_label.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                              self.width - constants.HORIZONTAL_PADDING - constants.HORIZONTAL_PADDING,
                              constants.DEFAULT_LABEL_HEIGHT)
        window_height += prs_label.height() + constants.VERTICAL_SPACE

        erase_info_label = QLabel(self)
        erase_info_label.setStyleSheet("font-size: 10px;")
        erase_info_label.setText('(To erase a PR from watch-list, right click on PR ID)')
        erase_info_label.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                                     self.width - constants.HORIZONTAL_PADDING - constants.HORIZONTAL_PADDING,
                                     constants.DEFAULT_LABEL_HEIGHT)
        window_height += erase_info_label.height() + constants.VERTICAL_SPACE

        open_link_info_label = QLabel(self)
        open_link_info_label.setStyleSheet("font-size: 10px;")
        open_link_info_label.setText('(To open the PR link, double click on PR ID)')
        open_link_info_label.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                                         self.width - constants.HORIZONTAL_PADDING - constants.HORIZONTAL_PADDING,
                                         constants.DEFAULT_LABEL_HEIGHT)
        window_height += open_link_info_label.height() + constants.VERTICAL_SPACE

        self.prs_list_container.setWidgetResizable(True)
        self.prs_list_container.setGeometry(constants.HORIZONTAL_PADDING, window_height,
                                            self.width - constants.HORIZONTAL_PADDING - constants.HORIZONTAL_PADDING,
                                            constants.DEFAULT_CONTAINER_HEIGHT)
        self.prs_list_container.setStyleSheet("border-width: 1px; border-style: ridge;")
        self.prs_list_container.show()
        window_height += self.prs_list_container.height() + constants.VERTICAL_PADDING

        self.pr_id_edit_line.setValidator(QIntValidator())
        self.pr_id_edit_line.setText("Enter the Link of the PR to be watched!")
        self.pr_id_edit_line.setGeometry(constants.HORIZONTAL_PADDING, window_height, self.prs_list_container.width(),
                                         constants.DEFAULT_LABEL_HEIGHT)
        window_height += self.pr_id_edit_line.height() + constants.VERTICAL_PADDING

        add_pr_button = QPushButton(self)
        add_pr_button.setText("Add PR")
        add_pr_button.setGeometry(constants.HORIZONTAL_PADDING, window_height, constants.DEFAULT_BTN_WIDTH,
                                  constants.DEFAULT_BTN_HEIGHT)
        add_pr_button.clicked.connect(self.add_pr_button_clicked)

        settings_button = QPushButton(self)
        settings_button.setText("Settings")
        settings_button.setGeometry(self.width - constants.DEFAULT_BTN_WIDTH - constants.HORIZONTAL_PADDING,
                                    window_height, constants.DEFAULT_BTN_WIDTH, constants.DEFAULT_BTN_HEIGHT)
        settings_button.clicked.connect(self.settings_button_clicked)
        window_height += add_pr_button.height() + constants.VERTICAL_PADDING

        self.setGeometry(self.top, self.left, self.width, window_height)
        qt_rectangle = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

        self.setFixedHeight(window_height)
        self.setFixedWidth(self.width)

        # Initialize signals with the corresponding signal functions
        self.updateSig.connect(self.update_container_for_signal)
        self.notifSig.connect(self.notify_user_for_signal)
        self.deleteSig.connect(self.delete_pr_for_signal)
        self.questionSig.connect(self.question_user_for_signal)
        self.closeMsgBoxSig.connect(self.close_msg_box)

        # Update PR container
        self.update_container_for_self()

        self.parent_tray_app.window = self
        self.exec_()

    def settings_button_clicked(self):
        settings_window = _SettingsWindow(self)
        settings_window.exec()

    def add_pr_button_clicked(self):
        print("add_pr_button Pressed!")
        if self.driverExec:
            print("Already Executing Driver")
            self.notifSig.emit(1, "Already executing another task!")
            return

        if test:
            pr_list_manager = PrListManager.get_instance()
            watch_item = _BasicPR("0000", _get_pr_url("0000"), constants.NO_STATUS)
            pr_list_manager.add_pr(watch_item)
            watch_item = _BasicPR("1111", _get_pr_url("1111"), constants.IN_PROGRESS)
            pr_list_manager.add_pr(watch_item)
            watch_item = _BasicPR("2222", _get_pr_url("2222"), constants.SUCCESS)
            pr_list_manager.add_pr(watch_item)
            watch_item = _BasicPR("3333", _get_pr_url("3333"), constants.FAILED)
            pr_list_manager.add_pr(watch_item)
            watch_item = _BasicPR("4444", _get_pr_url("4444"), constants.CONFLICT)
            pr_list_manager.add_pr(watch_item)
            watch_item = _BasicPR("5555", _get_pr_url("5555"), constants.MERGED)
            pr_list_manager.add_pr(watch_item)
            watch_item = _BasicPR("6666", _get_pr_url("6666"), constants.READY_TO_MERGE)
            pr_list_manager.add_pr(watch_item)
            self.update_container_for_self()
            return

        repo_info = RepoInfo.get_instance()
        print("add_pr_button Pressed! 1")
        # TODO: do not check just the access_token check also others
        if not repo_info.access_token:
            self.notify_user_for_signal(1, "Access token is not set!\nAccess token can be set from Settings!")
            return

        print("add_pr_button Pressed! 2")
        self.pr_id_edit_line.setFocus()
        id_to_add = self.pr_id_edit_line.text()
        print("add_pr_button Pressed! 3")
        msg_widget = QMessageBox()
        msg_widget.width = 320
        msg_widget.height = 200
        msg_widget.setGeometry(10, 10, msg_widget.width, msg_widget.height)
        qt_rectangle = msg_widget.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        msg_widget.move(qt_rectangle.topLeft())
        msg_widget.setWindowIcon(QIcon(constants.APP_ICON))
        print("add_pr_button Pressed! 4")
        if id_to_add == "":
            msg_widget.setWindowTitle('PR Watcher')
            QMessageBox.information(msg_widget, 'PR Watcher', "PR number is not valid!")
            return
        print("add_pr_button Pressed! 5")
        pr_list_manager = PrListManager.get_instance()
        if pr_list_manager.does_pr_item_exist(id_to_add):
            print("add_pr_button Pressed! 6")
            msg_widget.setWindowTitle('PR Watcher')
            QMessageBox.information(msg_widget, 'PR Watcher', "PR with the given number already exists!")
            return

        print("add_pr_button Pressed_1!")
        self.addThread = threading.Thread(target=pr_add_check, args=(self, id_to_add,))

        print("add_pr_button Pressed_2!")
        self.addThread.start()
        self.progress_msg_box = TimeoutMsgBox(self, 'Adding PR to Watch-list. Please wait.', 0, False, [])
        self.progress_msg_box.exec_()

        self.addThread.join()
        print("PR ADD THREAD END!")
        msg_widget.close()

    def update_container_for_self(self):
        print("Update_Self!")
        self.prs_list_container.hide()
        prs_container_layout = QGroupBox()
        prs_form = QFormLayout()
        pr_list_manager = PrListManager.get_instance()
        tmp_pr_node = pr_list_manager.pr_root_node
        while tmp_pr_node is not None:
            pr = tmp_pr_node.basic_pr
            pr_id_label = _PrListIdLabel()
            pr_id_label.id = pr.id
            pr_id_label.parentSign = self
            pr_id_label.setText("PR-" + pr.id)
            pr_id_label.setStyleSheet("border-style:none; font-weight:bold;")
            pr_id_label.setCursor(QtCore.Qt.PointingHandCursor)
            pr_id_label.setToolTip("Test")
            pr_status_label = QLabel()
            pr_status_label.setText(pr.status)
            if pr.status == constants.FAILED:
                pr_status_label.setStyleSheet("background-color:" + colors.FAILED_BG + "; color:" +
                                              colors.FAILED_FG + ";")
            elif pr.status == constants.SUCCESS:
                pr_status_label.setStyleSheet("background-color:" + colors.SUCCESS_BG + "; color:" +
                                              colors.SUCCESS_FG + ";")
            elif pr.status == constants.IN_PROGRESS:
                pr_status_label.setStyleSheet("background-color:" + colors.IN_PROGRESS_BG + "; color:" +
                                              colors.IN_PROGRESS_FG + ";")
            elif pr.status == constants.CONFLICT:
                pr_status_label.setStyleSheet("background-color:" + colors.CONFLICT_BG + "; color:" +
                                              colors.CONFLICT_FG + ";")
            elif pr.status == constants.MERGED:
                pr_status_label.setStyleSheet("background-color:" + colors.MERGED_BG + "; color:" +
                                              colors.MERGED_FG + ";")
            elif pr.status == constants.READY_TO_MERGE:
                pr_status_label.setStyleSheet("background-color:" + colors.MERGED_BG + "; color:" +
                                              colors.MERGED_FG + ";")
            else:
                pr_status_label.setStyleSheet("background-color:" + colors.DEFAULT_BG + "; color:" +
                                              colors.DEFAULT_FG + ";")
            prs_form.addRow(pr_id_label, pr_status_label)
            tmp_pr_node = tmp_pr_node.next_pr_node
        if pr_list_manager.pr_root_node is not None:
            prs_container_layout.setLayout(prs_form)
        self.prs_list_container.setWidget(prs_container_layout)
        self.prs_list_container.show()

    @QtCore.pyqtSlot(int, str)
    def update_container_for_signal(self, value, id_to_add):
        print("Update_Signal!")
        if value != 1 and value != 2:
            return
        self.update_container_for_self()
        # if value == 2:
        #     self.pr_id_edit_line.setText("")
        #     self.clearFocus()
        #     self.notifSig.emit(1, "PR-" + idToAdd + " is added successfully!")

    @QtCore.pyqtSlot(int, str)
    def notify_user_for_signal(self, value, msg):
        if value != 1:
            return
        msg_widget = QMessageBox()
        msg_widget.width = 320
        msg_widget.height = 200
        msg_widget.setGeometry(10, 10, msg_widget.width, msg_widget.height)
        qt_rectangle = msg_widget.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        msg_widget.move(qt_rectangle.topLeft())
        msg_widget.setWindowIcon(QIcon(constants.APP_ICON))
        QMessageBox.information(msg_widget, 'PR Watcher', msg)

    @QtCore.pyqtSlot(int, str, str)
    def delete_pr_for_signal(self, value, pr_id, msg):
        if value != 1:
            return
        info_msg_box = QMessageBox()
        info_msg_box.width = 320
        info_msg_box.height = 200
        info_msg_box.setGeometry(10, 10, info_msg_box.width, info_msg_box.height)
        qt_rectangle = info_msg_box.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        info_msg_box.move(qt_rectangle.topLeft())
        info_msg_box.setWindowIcon(QIcon(constants.APP_ICON))
        answer = QMessageBox.question(info_msg_box, 'PR Watcher', msg, QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            pr_list_manager = PrListManager.get_instance()
            if pr_list_manager.remove_pr_from_list(pr_id):
                self.update_container_for_self()
            else:
                self.notify_user_for_signal(1, "PR-" + pr_id + " item is being used by another process.\n" +
                                            "It will be removed after the process finished.")

    @QtCore.pyqtSlot(int, str, str)
    def question_user_for_signal(self, value, pr_id, msg):
        if value != 1:
            return
        msg_widget = QMessageBox()
        msg_widget.width = 320
        msg_widget.height = 200
        msg_widget.setGeometry(10, 10, msg_widget.width, msg_widget.height)
        qt_rectangle = msg_widget.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        msg_widget.move(qt_rectangle.topLeft())
        msg_widget.setWindowIcon(QIcon(constants.APP_ICON))
        answer = QMessageBox.information(msg_widget, 'PR Watcher', msg, QMessageBox.Ok | QMessageBox.Open)
        if answer == QMessageBox.Open:
            webbrowser.open_new_tab(_get_pr_url(pr_id))

    @QtCore.pyqtSlot()
    def close_msg_box(self):
        if self.progress_msg_box:
            self.progress_msg_box.closeSignal.emit(1)

    def closeEvent(self, close_event):
        self.parent_tray_app.window = None


def pr_add_check(window, id_to_add):
    print('[ADD_THREAD][-PR-' + id_to_add + '-] Add Thread Started!')
    window.driverExec = True
    pr_list_manager = PrListManager.get_instance()

    if not bitbucket_rest_interaction.does_pr_exist(id_to_add):
        window.driverExec = False
        window.closeMsgBoxSig.emit()
        window.notifSig.emit(1, "PR with the id \"" + id_to_add + "\" does not exist!")
        return

    # Check activities count
    comment_cnt = bitbucket_rest_interaction.get_activities(id_to_add)

    # Check whether the PR is merged
    if bitbucket_rest_interaction.is_pr_merged(id_to_add):
        # if pr is merged, update PR, no need to check status
        watch_item = _BasicPR(id_to_add, _get_pr_url(id_to_add), constants.MERGED)
        watch_item.commentCnt = comment_cnt
        pr_list_manager.add_pr(watch_item)
        print(
            '[ADD_THREAD][-PR-' + id_to_add + '-] PR item {' + str(watch_item) + '} is created and added to the list!')
        window.updateSig.emit(2, id_to_add)
        print('[ADD_THREAD][-PR-' + id_to_add + '-] Screen Update Signal Sent!')
        window.driverExec = False
        window.closeMsgBoxSig.emit()
        print('[ADD_THREAD][-PR-' + id_to_add + '-] Screen Message Box Close Signal Sent!')
        return
    elif bitbucket_rest_interaction.is_pr_conflicted(id_to_add):
        # if pr is not merged, check conflict
        # if there is a conflict, update PR no need to check status
        watch_item = _BasicPR(id_to_add, _get_pr_url(id_to_add), constants.CONFLICT)
        watch_item.commentCnt = comment_cnt
        pr_list_manager.add_pr(watch_item)
        print(
            '[ADD_THREAD][-PR-' + id_to_add + '-] PR item {' + str(watch_item) + '} is created and added to the list!')
        window.updateSig.emit(2, id_to_add)
        print('[ADD_THREAD][-PR-' + id_to_add + '-] Screen Update Signal Sent!')
        window.driverExec = False
        window.closeMsgBoxSig.emit()
        print('[ADD_THREAD][-PR-' + id_to_add + '-] Screen Message Box Close Signal Sent!')
        return
    elif bitbucket_rest_interaction.is_ready_to_merge(id_to_add):
        # if there is no conflict, check can be merged
        # if can be merged, update PR no need to check status
        watch_item = _BasicPR(id_to_add, _get_pr_url(id_to_add), constants.READY_TO_MERGE)
        watch_item.commentCnt = comment_cnt
        pr_list_manager.add_pr(watch_item)
        print(
            '[ADD_THREAD][-PR-' + id_to_add + '-] PR item {' + str(watch_item) + '} is created and added to the list!')
        window.updateSig.emit(2, id_to_add)
        print('[ADD_THREAD][-PR-' + id_to_add + '-] Screen Update Signal Sent!')
        window.driverExec = False
        window.closeMsgBoxSig.emit()
        print('[ADD_THREAD][-PR-' + id_to_add + '-] Screen Message Box Close Signal Sent!')
        return
    else:
        # if cannot be merged, check status
        pr_status = bitbucket_rest_interaction.get_status(id_to_add)
        if pr_status == bitbucket_rest_interaction.PrStatus.FAILED:
            watch_item = _BasicPR(id_to_add, _get_pr_url(id_to_add), constants.FAILED)
        elif pr_status == bitbucket_rest_interaction.PrStatus.IN_PROGRESS:
            watch_item = _BasicPR(id_to_add, _get_pr_url(id_to_add), constants.IN_PROGRESS)
        elif pr_status == bitbucket_rest_interaction.PrStatus.SUCCESS:
            watch_item = _BasicPR(id_to_add, _get_pr_url(id_to_add), constants.SUCCESS)
        else:
            watch_item = _BasicPR(id_to_add, _get_pr_url(id_to_add), constants.NO_STATUS)
        watch_item.commentCnt = comment_cnt
        pr_list_manager.add_pr(watch_item)
        print(
            '[ADD_THREAD][-PR-' + id_to_add + '-] PR item {' + str(watch_item) + '} is created and added to the list!')
        window.updateSig.emit(2, id_to_add)
        print('[ADD_THREAD][-PR-' + id_to_add + '-] Screen Update Signal Sent!')
        window.driverExec = False
        window.closeMsgBoxSig.emit()
        print('[ADD_THREAD][-PR-' + id_to_add + '-] Screen Message Box Close Signal Sent!')
        return


def _btn_open_action(pr_id):
    webbrowser.open_new_tab(_get_pr_url(pr_id))


class MsgWindow(QDialog):
    infoMsgBoxSig = pyqtSignal(str, str)

    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowCloseButtonHint)
        self.hide()
        self.infoMsgBoxSig.connect(self.info_msg_box_sig_func)

    @QtCore.pyqtSlot(str, str)
    def info_msg_box_sig_func(self, pr_id, msg_txt):
        btn_ok = QPushButton("Ok", self)
        btn_open = QPushButton("Open", self)
        btn_open.clicked.connect(lambda: _btn_open_action(pr_id))
        msg_widget = QMessageBox()
        msg_widget.setIcon(QMessageBox.Information)
        msg_widget.setText(msg_txt)
        msg_widget.width = 320
        msg_widget.height = 200
        msg_widget.setWindowIcon(QIcon(constants.APP_ICON))
        msg_widget.setWindowTitle('PR Watcher')
        msg_widget.addButton(btn_ok, QMessageBox.AcceptRole)
        msg_widget.addButton(btn_open, QMessageBox.ActionRole)
        msg_widget.setGeometry(10, 10, msg_widget.width, msg_widget.height)
        qt_rectangle = msg_widget.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        msg_widget.move(qt_rectangle.topLeft())
        msg_widget.exec_()

    def btn_ok_action(self):
        sys.exit(self.exec_())


class TrayApp:

    def __init__(self, application):
        tray_app_icon = QIcon(constants.APP_ICON)
        self.tray_icon = QSystemTrayIcon(tray_app_icon, parent=application)
        self.window = None
        # To be used in check thread for pop-up notification
        self.msg_window = MsgWindow()
        self.init_ui()

    def init_ui(self):
        self.tray_icon.setToolTip('PR Watcher')
        self.tray_icon.activated.connect(self.icon_click)
        menu = QMenu()
        menu.addAction('PR Watch-list', self.window_clicked)
        menu.addSeparator()
        menu.addAction('Exit', self.exit_clicked)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def exit_clicked(self):
        print('Exit Clicked')
        exit_flag.set()
        # sys.exit(app.exec_())
        sys.exit(self.tray_icon.parent().exec_())

    def window_clicked(self):
        print('_PRListWindow Clicked')
        if not self.window:
            _PRListWindow(self)

    def icon_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if not self.window:
                _PRListWindow(self)


class PrCheckThread(QtCore.QThread):

    def __init__(self, main_tray_app):
        super().__init__()
        self.main_tray_app = main_tray_app
        self.window = None

    def run(self):
        print('[UPDATE_THREAD] First Run!')
        while not exit_flag.wait(timeout=10):
            repo_info = RepoInfo.get_instance()
            if test:
                continue
            if not repo_info.access_token:
                continue
            print('[UPDATE_THREAD] Start of the Cycle!')
            pr_list_manager = PrListManager.get_instance()
            tmp_pr_node = pr_list_manager.pr_root_node
            while tmp_pr_node is not None:
                pr = tmp_pr_node.basic_pr
                if pr_list_manager.update_pr_id_in_progress(pr.id) == PRInProgressAction.PR_REMOVED:
                    if self.main_tray_app.window:
                        self.main_tray_app.window.updateSig.emit(1, "")
                message_text = "Changes for PR-" + pr.id + ":"
                change_cnt = 0
                # Check activities
                comment_cnt = bitbucket_rest_interaction.get_activities(pr.id)
                if comment_cnt != pr.commentCnt and comment_cnt != 0:
                    change_cnt += 1
                    message_text += "\n" + str(change_cnt) + "- New changes in comment section."
                    pr.commentCnt = comment_cnt

                # Check whether the PR is merged
                if bitbucket_rest_interaction.is_pr_merged(pr.id):
                    pr_status = constants.MERGED
                elif bitbucket_rest_interaction.is_pr_conflicted(pr.id):
                    pr_status = constants.CONFLICT
                elif bitbucket_rest_interaction.is_ready_to_merge(pr.id):
                    pr_status = constants.READY_TO_MERGE
                else:
                    pr_status_enum = bitbucket_rest_interaction.get_status(pr.id)
                    if pr_status_enum == bitbucket_rest_interaction.PrStatus.FAILED:
                        pr_status = constants.FAILED
                    elif pr_status_enum == bitbucket_rest_interaction.PrStatus.IN_PROGRESS:
                        pr_status = constants.IN_PROGRESS
                    elif pr_status_enum == bitbucket_rest_interaction.PrStatus.SUCCESS:
                        pr_status = constants.SUCCESS
                    else:
                        pr_status = constants.NO_STATUS

                if upd_test:
                    change_cnt += 1
                    message_text += "\n" + str(change_cnt) + "- New comments are added."
                    pr_status = constants.IN_PROGRESS

                if pr_status != pr.status:
                    pr_old_status = pr.status
                    pr.status = pr_status
                    change_cnt += 1
                    message_text += "\n" + str(change_cnt) + "- Status is updated from " + pr_old_status + " to " + \
                                    pr.status + "."

                print('[UPDATE_THREAD][-PR-' + pr.id + '-] CHANGE_CNT: ' + str(change_cnt) + ', MSG: ' + message_text)
                if change_cnt > 0:
                    if self.main_tray_app.window:
                        print('[UPDATE_THREAD][-PR-' + pr.id + '-] _PRListWindow Exists!')
                        if not self.main_tray_app.window.isHidden():
                            print('[UPDATE_THREAD][-PR-' + pr.id + '-] _PRListWindow Shown!')
                            self.main_tray_app.window.updateSig.emit(1, "")
                            print('[UPDATE_THREAD][-PR-' + pr.id + '-] Screen Update Signal Sent!')
                    print('[UPDATE_THREAD][-PR-' + pr.id + '-] There are changes to be informed about!')
                    self.main_tray_app.msg_window.infoMsgBoxSig.emit(pr.id, message_text)
                tmp_pr_node = tmp_pr_node.next_pr_node
            if pr_list_manager.update_pr_id_in_progress("") == PRInProgressAction.PR_REMOVED:
                if self.main_tray_app.window:
                    self.main_tray_app.window.updateSig.emit(1, "")
            print('[UPDATE_THREAD] End of Cycle!')


def _init_app_config():
    try:
        repo_info = RepoInfo.get_instance()
        repo_info.access_token = win_registry_management.read_reg_key(
            win_registry_management.REG_ACCESS_TOKE_NAME)
        repo_info.api_version = win_registry_management.read_reg_key(
            win_registry_management.REG_API_VERSION_NAME)
        repo_info.server_address = win_registry_management.read_reg_key(
            win_registry_management.REG_SERVER_ADDRESS_NAME)
        repo_info.project_name = win_registry_management.read_reg_key(
            win_registry_management.REG_PROJECT_NAME)
        repo_info.repo_name = win_registry_management.read_reg_key(
            win_registry_management.REG_REPO_NAME)
    except reg_key_cannot_be_read_error.RegKeyCannotBeReadError:
        pass


if __name__ == '__main__':
    # upd_test = True
    # test = True
    _init_app_config()
    main_app = QtWidgets.QApplication(sys.argv)
    main_app.setQuitOnLastWindowClosed(False)
    tray_app = TrayApp(main_app)
    periodic_pr_checker_thread = PrCheckThread(tray_app)
    periodic_pr_checker_thread.start()
    sys.exit(main_app.exec_())
