# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],  # 您的主入口脚本
    pathex=[], # 此处可留空
    binaries=[], # 根据您的项目结构，暂未发现明显的二进制库目录
    datas=[
        # 【关键】包含 paddleocr 包内的模型和数据文件
        # 根据您的项目结构，需要包含 _models、_pipelines、_utils 等目录
        (r'D:\ai_test\.venv\Lib\site-packages\paddleocr\_models', 'paddleocr\\_models'),
        (r'D:\ai_test\.venv\Lib\site-packages\paddleocr\_pipelines', 'paddleocr\\_pipelines'),
        (r'D:\ai_test\.venv\Lib\site-packages\paddleocr\_utils', 'paddleocr\\_utils'),

        # 【关键】包含 PaddleX 的版本文件
        (r'D:\ai_test\.venv\Lib\site-packages\paddlex\.version', 'paddlex'),

        # 包含您项目自己的资源文件
        (r'config\*', 'config'),
    ],
    hiddenimports=[
        # 显式声明 PyInstaller 可能无法自动分析到的依赖
        'numpy',
        'numpy._core',
        'numpy._core._exceptions',
        'numpy._core.multiarray',
        'cv2',
        'paddle',
        'paddlex',
        'paddleocr',

        # PaddleOCR 可能用到的子模块
        'paddleocr._models',
        'paddleocr._pipelines',
        'paddleocr._utils',
        'paddleocr._common_args',
        'paddleocr._constants',
        'paddleocr._env',
        'paddleocr._version',

        # 其他常见依赖
        'pyclipper',
        'lmdb',
        'shapely',
        'scipy._cyutility'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Ai-TestCase',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='D:\\ai_test\\config\\favicon.ico'
)