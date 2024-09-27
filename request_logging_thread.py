import json
from PyQt5.QtCore import QThread, pyqtSignal

class RequestLoggingThread(QThread):
    log_updated = pyqtSignal(dict, str)

    def __init__(self, driver):
        super().__init__()
        self.driver = driver
        self.is_logging = True

    def run(self):
        while self.is_logging:
            logs = self.driver.get_log('performance')
            for entry in logs:
                log = json.loads(entry['message'])['message']
                
                if log['method'] == 'Network.responseReceived' and 'response' in log['params']:
                    url = log['params']['response']['url']
                    
                    if self.is_internal_url(url):
                        continue
                    
                    status = log['params']['response']['status']
                    headers = log['params']['response']['headers']
                    initiator = log['params'].get('initiator', 'N/A')
                    request_id = log['params']['requestId']
                    payload = self.extract_payload(request_id)
                    ping = self.calculate_ping(log)

                    current_url = self.get_current_url()
                    main_domain = self.get_main_domain(current_url)
                    if main_domain:
                        method = log['params'].get('request', {}).get('method', 'N/A')
                        message = {
                            'url': url,
                            'method': method,
                            'status': status,
                            'headers': headers,
                            'payload': payload,
                            'initiator': initiator,
                            'ping': ping
                        }
                        self.log_updated.emit(message, main_domain)

    def is_internal_url(self, url):
        return url.startswith("chrome://") or url.startswith("about:")

    def extract_payload(self, request_id):
        return {}

    def calculate_ping(self, log):
        if 'params' in log and 'response' in log['params']:
            timing = log['params']['response'].get('timing', {})
            request_time = timing.get('requestTime', 0)
            response_time = timing.get('receiveHeadersEnd', 0)
            
            if request_time and response_time:
                ping = (response_time - request_time)
                return ping
        return 0.0

    def get_current_url(self):
        return self.driver.current_url

    def get_main_domain(self, url):
        try:
            base_url = '/'.join(url.split('/')[:3])
            return base_url
        except IndexError:
            return None
