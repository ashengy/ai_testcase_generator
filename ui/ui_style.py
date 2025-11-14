def load_stylesheet():
    """加载界面样式表,统一处理组件样式风格"""
    return """
         QMainWindow {
             background-color: #F0F2F5;
         }
         QComboBox, QLineEdit, QListWidget {
             border: 1px solid #DCDFE6;
             border-radius: 4px;
             padding: 5px;
             min-height: 25px;
         }
         QPushButton {
             background-color: #bdc3c7;
             color: black;
             border: none;
             border-radius: 4px;
             padding: 8px 15px;
         }
         QPushButton:hover {
             background-color: #66B1FF;
         }
         QPushButton#generateButton {
             background-color: #67C23A;
             color: white;
         }
         QPushButton#generateButton:hover {
             background-color: #85CE61;
         }
         QPushButton#export_btn {
             background-color: #67C23A;
             color: white;
         }
         QPushButton#pushButton_stop_generate {
             background-color: #FF0000;
             color: white;
         }
        QPushButton#pushButton_start_analyzer_image {
             background-color: #4E72B8;
             color: white;
         }
         QTextEdit {
             border: 1px solid #DCDFE6;
             border-radius: 4px;
             padding: 10px;
             font-family: Consolas;
         }
     """