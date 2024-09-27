import os
import tempfile
import pickle
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QMainWindow, QListWidgetItem, QAction, QMenu, QMessageBox, QFileDialog, QApplication
from PyQt5 import uic
from request_logging_thread import RequestLoggingThread
from browser_control import BrowserControlThread
from request_details_dialog import RequestDetailsDialog
from browser_utils import initialize_driver
from urllib.parse import urlsplit
import mimetypes
import requests
import psutil

class RequestLogger(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main.ui', self)
        self.driver = None
        self.logging_thread = None
        self.is_logging = False
        self.pid_file = os.path.join(tempfile.gettempdir(), "browser_pid.txt")
        self.whitelisted_pids = set()
        self.toggle_button.clicked.connect(self.toggle_logging)
        self.log_browser.itemDoubleClicked.connect(self.handle_item_double_clicked)
        self.domain_requests = {}
        self.current_domain = None
        self.toolbar = self.addToolBar("Main Toolbar")
        self.back_button = QAction("Back to Domains", self)
        self.back_button.triggered.connect(self.go_back_to_domains)
        self.toolbar.addAction(self.back_button)
        
        with open('style.qss', 'r') as style_file:
            self.setStyleSheet(style_file.read())

        self.mute_action = QAction("Mute Browser", self)
        self.mute_action.triggered.connect(self.mute_browser)
        self.toolbar.addAction(self.mute_action)

        self.save_config_action = QAction("Save Current Config", self)
        self.save_config_action.triggered.connect(self.save_config)
        self.toolbar.addAction(self.save_config_action)

        self.load_config_action = QAction("Load Config", self)
        self.load_config_action.triggered.connect(self.load_config)
        self.toolbar.addAction(self.load_config_action)

        self.log_browser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_browser.customContextMenuRequested.connect(self.show_context_menu)

        self.whitelisted_extensions = self.load_whitelisted_extensions()

    def toggle_logging(self):
        if self.is_logging:
            self.stop_logging()
        else:
            self.start_logging()

    def start_logging(self):
        self.is_logging = True
        self.toggle_button.setText("Stop Browser")
        self.whitelisted_pids = {proc.pid for proc in psutil.process_iter(attrs=['pid', 'name']) if proc.info['name'] == 'chrome.exe'}
        print("Whitelisted PIDs:", self.whitelisted_pids)
        
        result = initialize_driver()
        print("Result of initialize_driver:", result)
        self.driver, browser_pid, _ = result
        if self.driver:
            with open(self.pid_file, 'w') as f:
                f.write(str(browser_pid))
            self.logging_thread = RequestLoggingThread(self.driver)
            self.logging_thread.log_updated.connect(self.update_log_browser)
            self.logging_thread.start()

    def stop_logging(self):
        self.is_logging = False
        self.toggle_button.setText("Start Browser")
        if os.path.exists(self.pid_file):
            with open(self.pid_file, 'r') as f:
                browser_pid = int(f.read().strip())
            self.terminate_non_whitelisted_processes()

    def terminate_non_whitelisted_processes(self):
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'] == 'chrome.exe' and proc.pid not in self.whitelisted_pids:
                try:
                    proc.terminate()
                    print(f"Successfully terminated process with PID {proc.pid}.")
                except psutil.NoSuchProcess:
                    print(f"Error: Process with PID {proc.pid} not found.")
                except Exception as e:
                    print(f"Error: Could not terminate process with PID {proc.pid}. Reason: {e}")
        
        if self.is_logging:
            self.toggle_button.setText("Stop Browser")
        else:
            self.toggle_button.setText("Start Browser")

    def update_log_browser(self, message, main_domain):
        if main_domain not in self.domain_requests:
            self.domain_requests[main_domain] = []
            log_item = QListWidgetItem(main_domain)
            log_item.setData(Qt.UserRole, main_domain)
            self.log_browser.addItem(log_item)
        request_data = {
            'url': message['url'],
            'method': message['method'],
            'status': message['status'],
            'headers': message.get('headers', {}),
            'payload': message.get('payload', {}),
            'initiator': message.get('initiator', 'N/A'),
        }
        self.domain_requests[main_domain].append(request_data)

    def handle_item_double_clicked(self, item):
        if self.current_domain is None:
            self.current_domain = item.data(Qt.UserRole)
            self.show_requests_for_domain(self.current_domain)
        else:
            index = self.log_browser.row(item)
            requests = self.domain_requests[self.current_domain]
            request = requests[index - 1]
            self.show_request_detail(request)

    def show_requests_for_domain(self, domain):
        self.log_browser.clear()
        for request in self.domain_requests[domain]:
            log_item = QListWidgetItem(request['url'])
            log_item.setData(Qt.UserRole, request)
            self.log_browser.addItem(log_item)

    def go_back_to_domains(self):
        self.log_browser.clear()
        self.current_domain = None
        for domain in self.domain_requests.keys():
            log_item = QListWidgetItem(domain)
            log_item.setData(Qt.UserRole, domain)
            self.log_browser.addItem(log_item)

    def show_request_detail(self, request):
        dialog = RequestDetailsDialog(request, self)
        dialog.exec_()

    def show_context_menu(self, pos: QPoint):
        index = self.log_browser.indexAt(pos)
        if not index.isValid():
            return

        item = self.log_browser.itemAt(pos)
        data = item.data(Qt.UserRole)

        if isinstance(data, dict):
            menu = QMenu(self)

            copy_url_action = QAction("Copy URL", self)
            copy_url_action.triggered.connect(lambda: self.copy_url(data['url']))
            menu.addAction(copy_url_action)

            save_request_action = QAction("Save Request Info", self)
            save_request_action.triggered.connect(lambda: self.save_request_info(data))
            menu.addAction(save_request_action)

            download_action = QAction("Download Resource", self)
            download_action.triggered.connect(lambda: self.download_resource(data))
            menu.addAction(download_action)

            menu.exec_(self.log_browser.mapToGlobal(pos))
        else:
            menu = QMenu(self)
            show_details_action = QAction("Show Details", self)
            show_details_action.triggered.connect(lambda: self.show_domain_details(data))
            menu.addAction(show_details_action)
            menu.exec_(self.log_browser.mapToGlobal(pos))

    def copy_url(self, url):
        QApplication.clipboard().setText(url)
        QMessageBox.information(self, "URL Copied", "The URL has been copied to the clipboard.")

    def save_request_info(self, request):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Request Info", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'w') as f:
                    f.write(str(request))
                QMessageBox.information(self, "Saved", "Request info saved successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Save Error", f"Failed to save request info: {str(e)}")

    def load_whitelisted_extensions(self):
        whitelisted_extensions = set()
        try:
            with open('whitelisted_extensions.txt', 'r') as file:
                for line in file:
                    ext = line.strip().lower()
                    if ext.startswith('.'):
                        whitelisted_extensions.add(ext)
        except FileNotFoundError:
            QMessageBox.warning(self, "File Not Found", "The 'whitelisted_extensions.txt' file could not be found.")
        return whitelisted_extensions

    def download_resource(self, request):
        url = request['url']
        filename = os.path.basename(urlsplit(url).path)
        mime_type, _ = mimetypes.guess_type(filename)

        if not mime_type:
            QMessageBox.warning(self, "Download Error", "The request does not seem to be for a file.")
            return

        if os.path.splitext(filename)[1].lower() in self.whitelisted_extensions:
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()

                options = QFileDialog.Options()
                file_name, _ = QFileDialog.getSaveFileName(self, "Download Resource", filename, f"All Files (*);;{mime_type} Files (*.{mime_type.split('/')[-1]})", options=options)

                if file_name:
                    with open(file_name, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    QMessageBox.information(self, "Download Complete", "Resource downloaded successfully.")
            except requests.exceptions.RequestException as e:
                QMessageBox.warning(self, "Download Error", f"Failed to download resource: {str(e)}")
        else:
            QMessageBox.warning(self, "Download Error", "The file extension is not whitelisted.")

    def mute_browser(self):
        if self.driver:
            self.driver.execute_script("document.querySelectorAll('video, audio').forEach(el => el.muted = true);")
            QMessageBox.information(self, "Muted", "Browser audio has been muted.")

    def save_config(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Config", "", "Config Files (*.cfg);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'wb') as f:
                pickle.dump(self.domain_requests, f)
            QMessageBox.information(self, "Config Saved", "Configuration saved successfully.")

    def load_config(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Config", "", "Config Files (*.cfg);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'rb') as f:
                self.domain_requests = pickle.load(f)
            self.go_back_to_domains()
            QMessageBox.information(self, "Config Loaded", "Configuration loaded successfully.")

    def show_domain_details(self, domain):
        if domain in self.domain_requests:
            num_requests = len(self.domain_requests[domain])
            request_info = "\n".join(f"{i+1}: {req['url']} (Method: {req['method']}, Status: {req['status']})"
                                     for i, req in enumerate(self.domain_requests[domain]))
            details_message = (f"Domain: {domain}\n"
                               f"Number of requests: {num_requests}\n\n")
        else:
            details_message = f"Domain: {domain}\nNo requests found."
    
        QMessageBox.information(self, "Domain Details", details_message)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    logger = RequestLogger()
    logger.show()
    sys.exit(app.exec_())