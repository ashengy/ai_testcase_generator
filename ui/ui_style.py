def load_stylesheet():
    """加载界面样式表,统一处理组件样式风格"""
    return """
        QMainWindow, QWidget#appSurface {
            background: #F5F7FB;
            color: #1F2937;
        }

        QStatusBar {
            background: #EEF2FF;
            color: #475569;
            border-top: 1px solid #D8E0F5;
        }

        QLabel {
            color: #334155;
            font-size: 13px;
        }

        QLabel[sectionLabel="true"] {
            color: #0F172A;
            font-size: 13px;
            font-weight: 600;
            padding-bottom: 2px;
        }

        QLabel[hintLabel="true"] {
            color: #F97316;
            font-size: 12px;
            padding-left: 8px;
        }

        QLabel[statusBadge="true"] {
            background: #E0E7FF;
            color: #3730A3;
            border: 1px solid #C7D2FE;
            border-radius: 10px;
            padding: 8px 12px;
            font-weight: 600;
        }

        QLineEdit, QComboBox, QListWidget, QTextEdit, QPlainTextEdit {
            background: #FFFFFF;
            color: #0F172A;
            border: 1px solid #D6DCE8;
            border-radius: 12px;
            padding: 8px 12px;
            selection-background-color: #C7D2FE;
            selection-color: #1E1B4B;
        }

        QLineEdit, QComboBox {
            min-height: 22px;
        }

        QLineEdit:focus, QComboBox:focus, QListWidget:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 1px solid #7C9CFF;
        }

        QComboBox::drop-down {
            border: none;
            width: 28px;
        }

        QComboBox::down-arrow {
            width: 10px;
            height: 10px;
        }

        QListWidget[panel="true"], QTextEdit[panel="true"], QPlainTextEdit[panel="true"] {
            padding: 10px 12px;
        }

        QListWidget[densePanel="true"]::item {
            padding: 8px 10px;
            border-radius: 8px;
            margin: 2px 0;
        }

        QListWidget[densePanel="true"]::item:selected {
            background: #E0E7FF;
            color: #312E81;
        }

        QListWidget[densePanel="true"]::item:hover {
            background: #F1F5F9;
        }

        QPushButton {
            background: #E2E8F0;
            color: #0F172A;
            border: 1px solid transparent;
            border-radius: 12px;
            padding: 10px 16px;
            font-weight: 600;
            min-height: 18px;
        }

        QPushButton:hover {
            background: #CBD5E1;
        }

        QPushButton:pressed {
            background: #BAC6D3;
        }

        QPushButton[secondaryButton="true"] {
            background: #FFFFFF;
            border: 1px solid #D6DCE8;
            color: #334155;
        }

        QPushButton[secondaryButton="true"]:hover {
            background: #F8FAFC;
            border: 1px solid #C5D0E6;
        }

        QPushButton[accentButton="true"] {
            background: #EEF2FF;
            color: #4338CA;
            border: 1px solid #C7D2FE;
        }

        QPushButton[accentButton="true"]:hover {
            background: #E0E7FF;
        }

        QPushButton[successButton="true"], QPushButton#export_btn {
            background: #DCFCE7;
            color: #166534;
            border: 1px solid #86EFAC;
        }

        QPushButton[successButton="true"]:hover, QPushButton#export_btn:hover {
            background: #BBF7D0;
        }

        QPushButton[dangerButton="true"], QPushButton#pushButton_stop_generate {
            background: #FEE2E2;
            color: #B91C1C;
            border: 1px solid #FECACA;
        }

        QPushButton[dangerButton="true"]:hover, QPushButton#pushButton_stop_generate:hover {
            background: #FECACA;
        }

        QPushButton#generateButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #4F46E5, stop:1 #7C3AED);
            color: white;
            padding: 11px 18px;
        }

        QPushButton#generateButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #4338CA, stop:1 #6D28D9);
        }

        QPushButton#pushButton_start_analyzer_image {
            background: #E0F2FE;
            color: #075985;
            border: 1px solid #BAE6FD;
        }

        QPushButton#pushButton_start_analyzer_image:hover {
            background: #BAE6FD;
        }

        QCheckBox {
            spacing: 8px;
            color: #334155;
            font-weight: 500;
        }

        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid #94A3B8;
            background: #FFFFFF;
        }

        QCheckBox::indicator:checked {
            background: #4F46E5;
            border: 1px solid #4F46E5;
        }

        QTextEdit, QPlainTextEdit {
            font-family: "Consolas", "Microsoft YaHei UI";
            line-height: 1.4;
        }
    """