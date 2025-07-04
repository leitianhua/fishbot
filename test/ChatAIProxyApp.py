import sys
import threading
import requests
import logging
from flask import Flask, request, jsonify
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QComboBox, QPushButton, QLineEdit, QLabel, QSystemTrayIcon, QMenu,
    QTextEdit, QHBoxLayout
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QObject
import json
import http.client

# 创建自定义的QT信号发射器，用于在线程间传递日志消息


class LogSignalEmitter(QObject):
    log_signal = pyqtSignal(str)

# 创建自定义的日志处理器


class QTextEditHandler(logging.Handler):
    def __init__(self, signal_emitter):
        super().__init__()
        self.signal_emitter = signal_emitter

    def emit(self, record):
        log_message = self.format(record)
        self.signal_emitter.log_signal.emit(log_message)


class ChatAIProxyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatAI Proxy App")
        self.setFixedSize(600, 500)
        self.init_logging()
        self.init_apis()
        self.init_ui()
        self.server_thread = None
        self.selected_api = "API 1"  # 默认选择第一个API
        self.is_server_running = False

    def init_logging(self):
        self.log_signal_emitter = LogSignalEmitter()
        self.log_signal_emitter.log_signal.connect(self.update_log_display)

        # 配置日志
        self.logger = logging.getLogger('ChatAIProxy')
        self.logger.setLevel(logging.INFO)

        # 设置更详细的日志格式，包含文件名和行号
        log_format = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'

        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(console_handler)

        # 添加GUI显示处理器
        qt_handler = QTextEditHandler(self.log_signal_emitter)
        qt_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(qt_handler)

    def init_apis(self):
        # API配置，包含URL和处理方法
        self.api_configs = {
            "API 1": {
                "url": "codewebchat.fittenlab.cn",
                "handler": self.handle_api1_request
            },
            "API 2": {
                "url": "http://api2.example.com",
                "handler": self.handle_api2_request
            },
            "API 3": {
                "url": "http://api3.example.com",
                "handler": self.handle_api3_request
            }
        }

    def init_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout()
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # 控制面板布局
        control_layout = QVBoxLayout()

        # API选择和端口输入区域
        self.api_list = QComboBox()
        self.api_list.addItems(list(self.api_configs.keys()))
        self.api_list.setCurrentText("API 1")  # 默认选择第一个
        self.api_list.currentIndexChanged.connect(self.on_api_changed)
        control_layout.addWidget(QLabel("选择API:"))
        control_layout.addWidget(self.api_list)

        # 端口输入
        port_layout = QHBoxLayout()
        self.port_label = QLabel("端口号:")
        self.port_input = QLineEdit()
        self.port_input.setText("9696")  # 设置默认端口
        port_layout.addWidget(self.port_label)
        port_layout.addWidget(self.port_input)
        control_layout.addLayout(port_layout)

        # 状态显示
        self.status_label = QLabel("服务器状态: 未运行")
        control_layout.addWidget(self.status_label)

        # 按钮区域
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("启动服务")
        self.stop_button = QPushButton("关闭服务")
        self.start_button.clicked.connect(self.start_server)
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        control_layout.addLayout(button_layout)

        main_layout.addLayout(control_layout)

        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        main_layout.addWidget(QLabel("日志:"))
        main_layout.addWidget(self.log_display)

        # 系统托盘
        self.tray_icon = QSystemTrayIcon(QIcon("../server.svg"), self)
        self.tray_icon.setVisible(True)
        self.tray_menu = QMenu()
        self.tray_menu.addAction("显示", self.show)
        self.tray_menu.addAction("退出", self.quit_app)
        self.tray_icon.setContextMenu(self.tray_menu)

    def update_log_display(self, message):
        self.log_display.append(message)

    def on_api_changed(self, index):
        self.selected_api = self.api_list.currentText()
        self.logger.info(f"已选择API: {self.selected_api}")

    def start_server(self):
        port = self.port_input.text()
        if not port.isdigit():
            self.logger.error("无效的端口号")
            return
        port = int(port)

        if not self.is_server_running:
            self.server_thread = threading.Thread(
                target=self.run_flask_server, args=(port,))
            self.server_thread.daemon = True
            self.server_thread.start()

            self.is_server_running = True
            self.status_label.setText("服务器状态: 运行中")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.logger.info(f"服务器已启动，监听端口 {port}")

    def stop_server(self):
        if self.is_server_running:
            # 实际停止服务器的逻辑需要在这里实现
            self.is_server_running = False
            self.status_label.setText("服务器状态: 已停止")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.logger.info("服务器已停止")

    def handle_api1_request(self, param):
        """API 1的处理方法 - CodeWebChat API"""
        try:
            url = "https://codewebchat.fittenlab.cn/codeapi/chat?no_login=1&ide=webview&lang=zh&show_shortcut=0&apikey="
            self.logger.debug(f"开始请求API 1, 参数: {param}")

            input_text = f"""<|system|>\n请完全使用中文回答。\n<|end|>\n<|user|>\n{param['input']}@FCV9\n<|end|>\n<|assistant|>"""
            payload = json.dumps({
                "inputs": input_text,
                "ft_token": "FT_NOAPIKEY"
            })

            headers = {
                'Host': 'codewebchat.fittenlab.cn',
                'Referer': 'https://codewebchat.fittenlab.cn/?no_login=1&ide=webview&lang=zh&show_shortcut=0',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
                'Origin': 'https://codewebchat.fittenlab.cn',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Ch-Ua-Mobile': '?0',
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }

            response = requests.request("POST", url, headers=headers, data=payload)
           
            if response.status_code != 200:
                raise ApiException(response.status_code, "API请求失败")

            text = ''.join(json.loads(line).get('delta', '') for line in response.text.strip().split('\n'))
            return text, 200

        except requests.exceptions.RequestException as e:
            raise ApiException(500, f"API 1请求异常: {str(e)}")
        except Exception as e:
            raise ApiException(500, f"API 1处理失败: {str(e)}")

    def handle_api2_request(self, param):
        """API 2的处理方法"""
        try:
            url = self.api_configs["API 2"]["url"]
            headers = {
                'Content-Type': 'text/plain'
            }
            response = requests.post(url, data={"input": param}, headers=headers)
            
            if response.status_code != 200:
                raise ApiException(response.status_code, "API 2请求失败")
                
            return response.text, 200
        except requests.exceptions.RequestException as e:
            raise ApiException(500, f"API 2请求异常: {str(e)}")
        except Exception as e:
            raise ApiException(500, f"API 2处理失败: {str(e)}")

    def handle_api3_request(self, param):
        """API 3的处理方法"""
        try:
            url = self.api_configs["API 3"]["url"]
            params = {'input': param}
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                raise ApiException(response.status_code, "API 3请求失败")
                
            return response.text, 200
        except requests.exceptions.RequestException as e:
            raise ApiException(500, f"API 3请求异常: {str(e)}")
        except Exception as e:
            raise ApiException(500, f"API 3处理失败: {str(e)}")

    def run_flask_server(self, port):
        app = Flask(__name__)

        @app.route('/proxy', methods=['POST'])
        def handle_proxy_request():
            try:
                data = request.get_json()
                if not data or 'param' not in data:
                    return ApiResponse.error(400, "Missing 'param' parameter")

                param = data['param']
                self.logger.info(f"收到客户端请求，输入内容: {param}")

                if data.get('type') and self.api_configs.get(data['type']):
                    api_config = self.api_configs[data['type']]
                elif self.selected_api:
                    api_config = self.api_configs.get(self.selected_api)

                if api_config:
                    handler = api_config["handler"]
                    response_text, status_code = handler(param)
                    self.logger.info(f"API响应状态码: {status_code}")
                    
                    if status_code == 200:
                        return ApiResponse.success(
                            data=ApiResponse.format_data(response_text)
                        )
                    return ApiResponse.error(
                        status_code,
                        "API请求失败", 
                        ApiResponse.format_data(response_text)
                    )
                return ApiResponse.error(400, "API失效")

            except Exception as e:
                self.logger.exception(f"请求处理失败:")
                return ApiResponse.error(500, str(e))

        app.run(host='0.0.0.0', port=port)

    def quit_app(self):
        self.stop_server()
        self.logger.info("应用程序正在关闭...")
        self.close()
        self.tray_icon.deleteLater()
        sys.exit()


class ApiException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


class ApiResponse:
    @staticmethod
    def success(data=None, msg="请求成功"):
        return jsonify({
            "code": 200,
            "data": data,
            "msg": msg
        })

    @staticmethod
    def error(code, msg, data=None):
        return jsonify({
            "code": code,
            "data": data,
            "msg": msg
        }), code

    @staticmethod
    def format_data(text):
        return {"text": text} if text else None


def api_exception_handler(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ApiException as e:
            self.logger.error(f"业务异常: {str(e)}")
            return ApiResponse.error(e.code, e.message)
        except Exception as e:
            self.logger.exception("系统异常:")  # 这会打印完整的堆栈跟踪
            return ApiResponse.error(500, f"系统异常: {str(e)}")
    return wrapper


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatAIProxyApp()
    window.show()
    sys.exit(app.exec())
