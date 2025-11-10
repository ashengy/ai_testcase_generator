# ui_test/widgets.py
import sys

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QDialog, QListWidget, QVBoxLayout


class MultiSelectComboBox(QWidget):
    def __init__(self, items):
        super().__init__()
        self.items = items
        self.selected_items = []
        self.init_ui()

    def init_ui(self):
        self.layout = QHBoxLayout(self)
        self.combo_button = QPushButton("选择用例设计方法")
        self.combo_button.clicked.connect(self.show_dialog)
        self.layout.addWidget(self.combo_button)

    def show_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("选择用例设计方法")
        dialog.setGeometry(100, 100, 300, 300)

        list_widget = QListWidget(dialog)
        list_widget.addItems(self.items)
        list_widget.setSelectionMode(QListWidget.MultiSelection)

        ok_button = QPushButton("确定", dialog)
        ok_button.clicked.connect(lambda: self.get_selected_items(list_widget, dialog))

        layout = QVBoxLayout(dialog)
        layout.addWidget(list_widget)
        layout.addWidget(ok_button)

        dialog.exec_()

    def get_selected_items(self, list_widget, dialog):
        self.selected_items = [item.text() for item in list_widget.selectedItems()]
        self.combo_button.setText(", ".join(self.selected_items))
        dialog.accept()

    def get_selected_items_text(self):
        return self.combo_button.text()
