import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QPushButton, QTextEdit, QLabel, QHBoxLayout, QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, QProcess


class DatabaseManager(QMainWindow):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.process = None  # 用于存储 QProcess 对象
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("数据库管理工具")
        self.setGeometry(100, 100, 800, 600)

        # 创建主布局
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Item ID", "商品名称", "商品价格", "商品描述", "其他说明", "购买成功回复"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)  # 设置表格为不可编辑
        self.table.itemDoubleClicked.connect(self.show_edit_dialog)  # 双击事件
        layout.addWidget(self.table)

        # 创建按钮
        query_button = QPushButton("查询")
        query_button.clicked.connect(self.load_data)
        self.start_button = QPushButton("启动 Playwright 程序")
        self.start_button.clicked.connect(self.toggle_playwright)
        button_layout = QHBoxLayout()
        button_layout.addWidget(query_button)
        button_layout.addWidget(self.start_button)
        layout.addLayout(button_layout)

        # 创建日志框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.log_text.customContextMenuRequested.connect(self.show_log_menu)
        layout.addWidget(self.log_text)

        self.setCentralWidget(main_widget)
        self.load_data()

    def load_data(self):
        """加载数据库数据到表格"""
        self.table.setRowCount(0)  # 清空表格
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xianyu_shop")
        rows = cursor.fetchall()
        conn.close()

        for row_idx, row_data in enumerate(rows):
            self.table.insertRow(row_idx)
            for col_idx, col_data in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))

    def show_edit_dialog(self, item):
        """双击表格项时显示编辑对话框"""
        row = self.table.row(item)
        item_id = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()
        price = self.table.item(row, 2).text()
        desc = self.table.item(row, 3).text()
        other = self.table.item(row, 4).text()
        replies = self.table.item(row, 5).text()

        # 创建编辑对话框
        self.dialog = QWidget()
        self.dialog.setWindowTitle("编辑商品信息")
        dialog_layout = QVBoxLayout()

        # 创建只读字段
        self.create_readonly_field(dialog_layout, "Item ID", item_id)
        self.create_readonly_field(dialog_layout, "商品价格", price)

        # 创建商品名称和商品描述的只读多行文本框
        self.name_input = QTextEdit(name)
        self.name_input.setReadOnly(True)
        self.name_input.setFixedHeight(60)  # 设置固定高度
        self.desc_input = QTextEdit(desc)
        self.desc_input.setReadOnly(True)
        self.desc_input.setFixedHeight(100)  # 设置固定高度

        dialog_layout.addWidget(QLabel("商品名称:"))
        dialog_layout.addWidget(self.name_input)
        dialog_layout.addWidget(QLabel("商品描述:"))
        dialog_layout.addWidget(self.desc_input)

        # 创建可编辑字段
        self.other_input = QTextEdit(other)
        self.replies_input = QTextEdit(replies)

        # 设置 QTextEdit 的内容，确保保留换行符
        self.other_input.setPlainText(other)  # 使用 setPlainText 保留换行符
        self.replies_input.setPlainText(replies)  # 使用 setPlainText 保留换行符

        dialog_layout.addWidget(QLabel("其他说明:"))
        dialog_layout.addWidget(self.other_input)
        dialog_layout.addWidget(QLabel("购买成功回复:"))
        dialog_layout.addWidget(self.replies_input)

        # 保存按钮
        save_button = QPushButton("保存")
        save_button.clicked.connect(lambda: self.save_edits(item_id, row))
        dialog_layout.addWidget(save_button)

        self.dialog.setLayout(dialog_layout)
        self.dialog.show()

    def create_readonly_field(self, layout, label_text, value):
        """创建只读字段"""
        label = QLabel(f"{label_text}: {value}")
        layout.addWidget(label)

    def save_edits(self, item_id, row):
        """保存编辑内容"""
        other = self.other_input.toPlainText()
        replies = self.replies_input.toPlainText()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE xianyu_shop
            SET shop_other = ?, buy_success_replies = ?
            WHERE item_id = ?
        """, (other, replies, item_id))
        conn.commit()
        conn.close()

        # 更新表格内容
        self.table.setItem(row, 4, QTableWidgetItem(other))
        self.table.setItem(row, 5, QTableWidgetItem(replies))

        self.dialog.close()

    def toggle_playwright(self):
        """启动或停止 Playwright 程序"""
        if self.process is None:  # 如果当前没有运行的进程
            self.start_button.setText("停止 Playwright 程序")
            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self.read_output)
            self.process.readyReadStandardError.connect(self.read_errors)
            self.process.finished.connect(self.process_finished)
            self.process.start("python", ["autoFish.py"])
        else:  # 如果当前有运行的进程
            self.start_button.setText("启动 Playwright 程序")
            self.process.kill()
            self.process = None

    def read_output(self):
        """读取标准输出"""
        data = self.process.readAllStandardOutput().data().decode("utf-8")  # 确保正确解码
        self.log_text.append(data.strip())  # 将日志追加到日志框

    def read_errors(self):
        """读取错误输出"""
        data = self.process.readAllStandardError().data().decode("utf-8")  # 确保正确解码
        self.log_text.append(data.strip())  # 将错误日志追加到日志框

    def process_finished(self):
        """进程结束时的处理"""
        self.start_button.setText("启动 Playwright 程序")
        self.process = None

    def show_log_menu(self, position):
        """显示日志框的右键菜单"""
        menu = QMenu()
        clear_action = menu.addAction("清除日志")
        action = menu.exec(self.log_text.mapToGlobal(position))
        if action == clear_action:
            self.log_text.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    db_path = "items.db"  # 数据库路径
    window = DatabaseManager(db_path)
    window.show()
    sys.exit(app.exec())
