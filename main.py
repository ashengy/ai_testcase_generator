# main.py
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from ui.main_window import DeepSeekTool

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("微软雅黑", 10))
    window = DeepSeekTool()
    window.show()
    sys.exit(app.exec_())