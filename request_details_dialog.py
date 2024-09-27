from PyQt5.QtWidgets import QDialog, QTextBrowser, QVBoxLayout

class RequestDetailsDialog(QDialog):
    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Request Details")
        self.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()
        url = request.get('url', 'N/A')
        method = request.get('method', 'N/A')
        status = request.get('status', 'N/A')
        headers_info = self.format_headers(request.get('headers', {}))
        payload_info = self.format_payload(request.get('payload', {}))
        initiator_info = request.get('initiator', 'N/A')
        self.text_browser = QTextBrowser()
        self.text_browser.setText(f"URL: {url}\nMethod: {method}\nStatus: {status}")
        layout.addWidget(self.text_browser)
        headers_browser = QTextBrowser()
        headers_browser.setPlainText(headers_info)
        layout.addWidget(headers_browser)
        payload_browser = QTextBrowser()
        payload_browser.setPlainText(payload_info)
        layout.addWidget(payload_browser)
        initiator_browser = QTextBrowser()
        initiator_browser.setPlainText(f"Initiator: {initiator_info}")
        layout.addWidget(initiator_browser)
        self.setLayout(layout)

    def format_headers(self, headers):
        return '\n'.join([f"{key}: {value}" for key, value in headers.items()])

    def format_payload(self, payload):
        return str(payload)
