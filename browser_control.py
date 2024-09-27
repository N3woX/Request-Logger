import psutil
from PyQt5.QtCore import QThread

class BrowserControlThread(QThread):
    def __init__(self, browser_pid):
        super().__init__()
        self.browser_pid = browser_pid

    def run(self):
        if self.browser_pid:
            try:
                p = psutil.Process(self.browser_pid)
                p.terminate()
            except psutil.NoSuchProcess:
                pass
