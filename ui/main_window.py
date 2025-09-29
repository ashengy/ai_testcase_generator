# ui/main_window.py
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QListWidget, QAbstractItemView,
                             QLineEdit, QTextEdit, QFileDialog, QMessageBox, QListWidgetItem,
                             QApplication)
from PyQt5.QtGui import QFont

from config.constants import TEMPLATE_PHRASES, CONTENT_FILTER_FUZZY, CONTENT_FILTER_EXACT, CLEAN_FLAG
from core.worker import GenerateThread
from ui.widgets import MultiSelectComboBox
import json
import os


class DeepSeekTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.context = None
        self.context_chunks = []
        self.func_type = None
        self.module_input_pic = None
        self.api_key = ""  # 添加API Key属性
        self.init_ui()
        self.knowledge_bases = []
        self.current_dir = ""
        self.job_area = None
        self.load_knowledge_bases()
        self.setStyleSheet(self.load_stylesheet())

        # 使用从config导入的常量
        self.template_phrases = TEMPLATE_PHRASES
        self.content_filter_fuzzy = CONTENT_FILTER_FUZZY
        self.content_filter_exact = CONTENT_FILTER_EXACT
        self.clean_flag = CLEAN_FLAG

    def init_ui(self):
        """ 初始化界面 """
        self.setWindowTitle("测试用例生成工具")
        self.setGeometry(300, 200, 1400, 900)

        # 主控件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # 创建提示词模式下拉框
        self.param_choice_combo = QComboBox()
        self.param_choice_combo.addItems(["文档", "参数输入"])  # 下拉框选项
        self.param_choice_combo.setCurrentIndex(0)  # 默认选择"文档"

        # 功能模式下拉框
        self.func_choice_combo = QComboBox()
        self.func_choice_combo.addItems(["功能测试用例",
                                         "接口测试用例",
                                         ])  # 下拉框选项
        self.func_choice_combo.setCurrentIndex(0)  # 默认选择"文档"

        # 用例设计方法多选下拉框
        design_methods = [
            "无",
            "等价类划分",
            "边界值分析",
            "决策表",
            "状态转换",
            "错误推测",
            "场景法",
            "因果图测试",
            "正交分析法"
        ]
        self.method_combo = MultiSelectComboBox(design_methods)  # 测试用例设计方法，支持多选

        industries = [
            "无",
            "互联网/电子商务",
            "保险",
            "金融科技",
            "医疗健康",
            "教育科技",
            "游戏开发",
            "物联网",
            "人工智能",
            "大数据",
            "云计算",
            "汽车电子"
        ]

        # 知识库选择区域
        kb_layout = QHBoxLayout()
        self.btn_add_kb = QPushButton("添加知识库")
        self.combo_kb = QComboBox()
        # 行业
        self.comboBox = QComboBox(self)
        # 将选项添加到 QComboBox
        self.comboBox.addItems(industries)
        self.comboBox.currentTextChanged.connect(self.updateLabel)
        # 设置默认值为第一个选项
        self.comboBox.setCurrentIndex(0)
        self.btn_refresh = QPushButton("刷新")

        # 添加API Key输入框
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("请输入API Key")
        self.api_key_input.setEchoMode(QLineEdit.Password)  # 密码模式显示

        kb_layout.addWidget(QLabel("知识库目录:"))
        kb_layout.addWidget(self.combo_kb)
        kb_layout.addWidget(QLabel("行业:"))
        kb_layout.addWidget(self.comboBox)
        kb_layout.addWidget(QLabel("API Key:"))
        kb_layout.addWidget(self.api_key_input)
        kb_layout.addWidget(QLabel("提示词模式:"))
        kb_layout.addWidget(self.param_choice_combo)
        kb_layout.addWidget(QLabel("功能模式:"))
        kb_layout.addWidget(self.func_choice_combo)
        kb_layout.addWidget(QLabel("用例设计:"))
        kb_layout.addWidget(self.method_combo)

        kb_layout.addWidget(self.btn_add_kb)
        kb_layout.addWidget(self.btn_refresh)
        # 文件操作区域
        file_ops_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("全选")
        # self.btn_clean_docx = QPushButton("清洗")
        self.btn_clear_all = QPushButton("清空")
        file_ops_layout.addWidget(self.btn_select_all)
        # file_ops_layout.addWidget(self.btn_clean_docx)
        file_ops_layout.addWidget(self.btn_clear_all)
        # 更新提示词
        self.refresh_prompt_btn = QPushButton("更新提示词")
        self.refresh_prompt_btn.setObjectName("refreshPromptButton")
        file_ops_layout.addWidget(self.refresh_prompt_btn)
        # 生成按钮
        self.generate_btn = QPushButton("开始推理")
        self.generate_btn.setObjectName("generateButton")
        file_ops_layout.addWidget(self.generate_btn)
        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.setSortingEnabled(True)

        # 内容预览
        self.preview_area = QTextEdit()
        self.preview_area.setFixedHeight(200)
        self.preview_area.setReadOnly(False)
        # 提示词输入
        self.prompt_input = QTextEdit()
        self.prompt_input.setFixedHeight(300)
        self.prompt_input.setText("Role: 测试用例设计专家\n\n"
                                  "Rules:\n\n"
                                  "设计目标：\n"
                                  "通过正交分析法实现：\n"
                                  "使用正交表生成参数组合，覆盖所有参数对的交互组合\n\n"
                                  "用例数量：\n"
                                  "尽可能多（不少于15条）\n"
                                  "需求分析指南：\n"
                                  "1. 识别功能边界（系统做什么/不做什么）\n"
                                  "2. 提取业务规则（计算规则、验证规则）\n"
                                  "3. 定义用户角色及其权限\n"
                                  "4. 梳理关键业务流程（正常流、备选流、异常流）\n"
                                  "5. 标记敏感操作（审计日志、权限校验点）\n\n"
                                  "输出要求：\n"
                                  "1. 格式：结构化JSON,必须严格遵守JSON语法规范\n"
                                  "2. 不要使用JavaScript语法（如.repeat()方法）\n"
                                  "3. 对于需要重复字符的情况，请直接写出完整字符串，例如：\"aaaaaaa...\"而不是\"a\".repeat(7)"
                                  "4. 字符串长度限制测试时，请使用描述性文字如\"256个字符的a\"，而不是实际生成256个字符"
                                  "5. 字段：\n"
                                  "   - 用例编号：<模块缩写>-<3位序号>\n"
                                  "   - 用例标题：<测试目标> [正例/反例]\n"
                                  "   - 前置条件：初始化状态描述\n"
                                  "   - 测试数据：参数值的具体组合\n"
                                  "   - 操作步骤：带编号的明确步骤\n"
                                  "   - 预期结果：可验证的断言\n"
                                  "   - 优先级：P0(冒烟)/P1(核心)/P2(次要)\n"
                                  "3. 示例：\n"
                                  "[\n"
                                  "    {\n"
                                  "        \"用例编号\": \"PAY-001\",\n"
                                  "        \"用例标题\": \"支付功能 [正例]\",\n"
                                  "        \"前置条件\": \"用户已登录，购物车内已有商品\",\n"
                                  "        \"测试数据\": {\n"
                                  "            \"支付方式\": \"支付宝支付\",\n"
                                  "            \"金额范围\": \"100-1000\",\n"
                                  "            \"货币类型\": \"CNY\"\n"
                                  "        },\n"
                                  "        \"操作步骤\": [\n"
                                  "            \"1. 打开购物车页面\",\n"
                                  "            \"2. 点击结算按钮\",\n"
                                  "            \"3. 选择支付方式为支付宝支付\",\n"
                                  "            \"4. 确认支付金额为100-1000元人民币\",\n"
                                  "            \"5. 点击支付按钮\"\n"
                                  "        ],\n"
                                  "        \"预期结果\": \"支付成功，页面显示支付完成信息，余额扣减正确\",\n"
                                  "        \"优先级\": \"P1\"\n"
                                  "    }\n"
                                  "]\n\n"
                                  "质量标准：\n"
                                  "- 参数对组合覆盖率 ≥95%\n"
                                  "- 正向场景用例占比60%\n"
                                  "- 异常场景用例占比30%\n"
                                  "- 边界场景用例占比10%\n\n"
                                  "生成步骤：\n"
                                  "1. 参数建模 → 2. 场景分析 → 3. 用例生成 → 4. 交叉校验")

        # 内容预览
        self.preview_area = QTextEdit()
        self.preview_area.setFixedHeight(200)
        self.preview_area.setReadOnly(False)

        # 结果展示
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFixedHeight(300)

        # 组装布局
        layout.addLayout(kb_layout)
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("文本标题:"))
        self.module_input = QLineEdit()
        self.module_input.setText("需求背景,功能描述,触发")
        hbox.addWidget(self.module_input)
        hbox.addWidget(QLabel("表格标题:"))
        self.module_input_table = QLineEdit()
        self.module_input_table.setText("")
        hbox.addWidget(self.module_input_table)
        hbox.addWidget(QLabel("图片标题:"))
        self.module_input_pic = QLineEdit()
        self.module_input_pic.setText("")
        hbox.addWidget(self.module_input_pic)
        layout.addLayout(hbox)
        layout.addWidget(QLabel("文档列表:"))
        layout.addLayout(file_ops_layout)
        layout.addWidget(self.file_list)
        layout.addWidget(QLabel("内容预览:"))
        layout.addWidget(self.preview_area)
        # 底部布局修改
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(QLabel("提示词:"))
        bottom_layout.addWidget(self.prompt_input)
        bottom_layout.addWidget(QLabel("生成结果:"))
        bottom_layout.addWidget(self.result_area)

        # 组装主布局
        layout.addLayout(bottom_layout)

        # 导出区域
        export_layout = QHBoxLayout()
        self.export_combo = QComboBox()
        self.export_combo.addItems(["Word 文档", "Text 文件", "Markdown", "JSON", "XLSX"])
        self.export_btn = QPushButton("导出结果")
        export_layout.addWidget(QLabel("导出格式:"))
        export_layout.addWidget(self.export_combo)
        export_layout.addWidget(self.export_btn)

        layout.addLayout(export_layout)

        # 信号连接
        self.btn_add_kb.clicked.connect(self.add_knowledge_base)
        self.btn_refresh.clicked.connect(self.load_knowledge_bases)
        self.combo_kb.currentTextChanged.connect(self.load_directory)
        self.file_list.itemSelectionChanged.connect(self.update_preview)
        self.btn_select_all.clicked.connect(lambda: self.file_list.selectAll())
        # self.btn_clean_docx.clicked.connect(self.clean_text)  #
        self.btn_clear_all.clicked.connect(lambda: self.file_list.clearSelection())
        self.generate_btn.clicked.connect(self.generate_report)
        self.refresh_prompt_btn.clicked.connect(self.generate_testcase_prompt)
        self.export_btn.clicked.connect(self.export_result)

    def updateLabel(self):
        self.job_area = self.comboBox.currentText()

    def generate_testcase_prompt(self, params=None):
        """
        生成测试用例设计提示词的智能函数
        生成测试用例设计提示词
        参数：
        params : dict/list - 参数维度字典或需求文档类型

        返回：
        str - 结构化提示词模板
        """
        # ========== 参数处理模块 ==========
        method = self.method_combo.get_selected_items_text()
        method_list = []  # 已选方法列表
        if method not in ('选择用例设计方法', '无'):
            method_list = method.split(',')
        elif method == '选择用例设计方法' or method == '无':
            method = '常用测试用例设计方法'
        parameters = ""
        func_type = self.func_choice_combo.currentText()
        if func_type == '接口测试用例':
            prompt = """# Role: 高级接口测试架构师

## Profile
- language: 中文
- description: 专业的接口质量保障专家，擅长设计高覆盖率的自动化测试方案
- background: 10年互联网企业测试架构经验，主导过百万级API测试体系建设
- personality: 严谨细致|逻辑性强|注重风险预防
- expertise: 测试策略设计|安全渗透测试|性能调优
- target_audience: 测试工程师|开发人员|DevOps团队

## Skills

1. 核心测试能力
   - 边界分析: 精准识别参数边界条件
   - 场景建模: 构建真实业务场景测试模型
   - 漏洞检测: OWASP TOP10安全漏洞测试
   - 性能压测: 设计阶梯式压力测试方案

2. 辅助技能
   - 协议解析: 深度理解HTTP/HTTPS/WebSocket协议
   - 数据构造: 生成结构化测试数据集
   - 异常模拟: 制造网络异常和服务端故障
   - 监控分析: 实时监测系统资源指标

## Rules

1. 质量原则：
   - 等价类划分必须覆盖有效/无效等价类
   - 边界值测试必须包含上点/离点/临界值
   - 安全测试需包含至少3种攻击向量
   - 性能测试需定义明确SLA指标

2. 行为准则：
   - 优先验证核心业务流程
   - 每个参数至少设计8个测试场景
   - 必须验证非功能需求
   - 保持测试用例原子性

3. 限制条件：
   - 不处理未文档化的接口
   - 不生成破坏性测试数据
   - 不泄露敏感测试信息
   - 不超出给定接口范围
   - 构造参数超长时不要使用*及repeat形式，直接展示需要多少字符即可，让用户自行修改
   - 严格按照示例输出，不要出现幻觉
   - 不要添加注释及多余的空行

## Workflows

- 目标: 生成零缺陷测试方案
- 步骤1: 解构接口文档要素
- 步骤2: 设计参数矩阵表
- 步骤3: 构建测试决策树
- 预期结果: 可执行的测试套件

## OutputFormat

1. 结构化输出：
   - format: application/json
   - structure: 只包含测试用例数组，不要添加注释
   - style: 符合Google JSON风格指南

2. 格式规范：
   - indentation: 2空格缩进
   - sections: 分测试类型分组
   - highlighting: 关键字段加注释

3. 验证规则：
   - validation: 通过ajv校验


4. 示例说明：
   1. 功能测试示例：
      - 标题: 用户信息查询验证
      - 格式类型: JSON
      - 示例内容:
        [{
          "case_id": "TC_FUNC_001",
          "case_name": "有效用户ID查询",
          "priority": "High",
          "pre_condition": "测试用户已注册并激活",
          "steps": [
            "构造合法用户ID请求",
            "验证200状态码",
            "校验响应数据结构",
            "比对数据库记录"
          ],
          "expected_result": "返回用户完整档案信息",
          "test_data": {
            "user_id": 10001,
            "auth_token": "Bearer valid_token"
          },
          "test_type": "功能测试"
        }]
   2. 安全测试示例：
      - 标题: SQL注入检测
      - 格式类型: JSON
      - 示例内容:
          [{
            "case_id": "TC_SEC_005",
            "case_name": "用户ID参数注入检测",
            "priority": "Critical",
            "pre_condition": "启用WAF防护",
            "steps": [
              "发送恶意注入载荷: ' OR 1=1 --",
              "监控数据库查询日志",
              "分析响应内容"
            ],
            "expected_result": "返回400错误且阻断注入请求",
            "test_data": {
              "user_id": "123' UNION SELECT * FROM users --"
            },
            "test_type": "安全测试"
          }]

## Initialization
作为高级接口测试架构师，你必须遵守上述Rules，按照Workflows执行任务，并按照[输出格式]输出。  """
            self.prompt_input.clear()
            self.prompt_input.setText(prompt)
        elif func_type == '功能测试用例':
            parameters += f"输出用例类型{func_type}"
            if isinstance(params, dict) and len(params) > 0:
                # 显式参数模式
                parameters = "参数维度：\n" + "\n".join(
                    [f"▸ {k}：{', '.join(v)}" for k, v in params.items()]
                )
            elif isinstance(params, list):
                # 需求文档类型提示
                doc_type = params[0] if params else "通用需求"
                parameters += f"需求文档类型：{doc_type}\n" + \
                              "请提取以下要素：\n" + \
                              "1. 核心业务实体及其属性\n" + \
                              "2. 关键业务流程步骤\n" + \
                              "3. 状态转换规则\n" + \
                              "4. 输入验证规则\n" + \
                              "5. 错误处理策略"
            else:
                # 默认需求分析模式
                parameters += "需求分析指南：\n" + \
                              "1. 识别功能边界（系统做什么/不做什么）\n" + \
                              "2. 提取业务规则（计算规则、验证规则）\n" + \
                              "3. 定义用户角色及其权限\n" + \
                              "4. 梳理关键业务流程（正常流、备选流、异常流）\n" + \
                              "5. 标记敏感操作（审计日志、权限校验点）"

            method_library = {
                "正交分析法": {
                    "desc": "使用正交表生成参数组合，覆盖所有参数对的交互组合",
                    "steps": ["构建正交表", "优化组合数量", "验证两两覆盖"],
                    "coverage": "参数对组合覆盖率 ≥95%"
                },
                "边界值分析": {
                    "desc": "针对数值型参数测试极值：最小值、略高于最小值、正常值、略低于最大值、最大值",
                    "steps": ["识别边界参数", "生成六点值（min-1,min,min+1,norm,max-1,max）", "处理无效类"],
                    "coverage": "边界条件覆盖率100%"
                },
                "等价类划分": {
                    "desc": "将输入划分为有效/无效类，每个类选取代表值测试",
                    "steps": ["定义有效等价类", "定义无效等价类", "生成代表值"],
                    "coverage": "每个等价类至少1个用例"
                },
                "状态转换": {
                    "desc": "基于状态机模型测试合法/非法转换",
                    "steps": ["绘制状态图", "覆盖所有合法转换", "测试非法转换"],
                    "coverage": "状态转换覆盖率100%"
                },
                "决策表": {
                    "desc": "条件组合的全覆盖测试（适合复杂业务规则）",
                    "steps": ["列出所有条件桩", "构建真值表", "合并相似项"],
                    "coverage": "条件组合覆盖率100%"
                },
                "错误推测": {
                    "desc": "基于经验测试易错点：异常输入、中断测试、并发操作",
                    "steps": ["列出历史缺陷", "分析脆弱模块", "设计非常规操作"],
                    "coverage": "补充覆盖边界外的5%"
                },
                "场景法": {
                    "desc": "模拟用户旅程测试端到端流程",
                    "steps": ["识别主成功场景", "定义扩展场景", "组合异常路径"],
                    "coverage": "主流程覆盖率100%"
                },
                "因果图": {
                    "desc": "分析输入条件的逻辑关系生成用例",
                    "steps": ["识别原因和结果", "构建因果图", "生成判定表"],
                    "coverage": "因果逻辑覆盖率100%"
                }
            }
            desc_str = ''
            # ========== 方法选择 ==========
            if len(method_list) >= 1:

                for method in method_list:
                    selected_method = method_library.get(method, method_library["正交分析法"])
                    desc_str += f"""
使用{method}方法设计用例时要符合：{selected_method['desc']}

关键步骤：
 {chr(10).join([f'{i + 1}. {step}' for i, step in enumerate(selected_method['steps'])])}
示例：
 {self.generate_example(method)} \n

质量标准：
 - {selected_method['coverage']}
 - 正向场景用例占比60%
 - 异常场景用例占比30%
 - 边界场景用例占比10%
 \n
                    """
            # ========== 生成提示词 ==========
            prompt = f"""
Role: 测试用例设计专家

Rules:

设计目标：\n
通过{method}实现：\n

用例数量：\n
尽可能多（不少于15条）\n

用例设计需遵循：\n
{desc_str} \n

参数：\n
{parameters} \n

输出要求：
1. 格式：结构化JSON,必须严格遵守JSON语法规范
2. 不要使用JavaScript语法（如.repeat()方法）
3. 对于需要重复字符的情况，请直接写出完整字符串，例如："aaaaaaa..."而不是"a".repeat(7)
4. 字符串长度限制测试时，请使用描述性文字如"256个字符的a"，而不是实际生成256个字符
5. 字段：
   - 用例编号：<模块缩写>-<3位序号>
   - 用例标题：<测试目标> [正例/反例]
   - 前置条件：初始化状态描述
   - 测试数据：参数值的具体组合
   - 操作步骤：带编号的明确步骤
   - 预期结果：可验证的断言
   - 优先级：P0(冒烟)/P1(核心)/P2(次要)

生成步骤：
1. 参数建模 → 2. 场景分析 → 3. 用例生成 → 4. 交叉校验"""
            self.prompt_input.clear()
            self.prompt_input.setText(prompt)
        # return prompt

    def generate_example(self, method):
        """生成方法对应的示例"""
        examples = {
            "正交分析法": """[
        {
            "用例编号": "PAY-001",
            "用例标题": "支付功能 [正例]",
            "前置条件": "用户已登录，购物车内已有商品",
            "测试数据": {
                "支付方式": "支付宝支付",
                "金额范围": "100-1000",
                "货币类型": "CNY"
            },
            "操作步骤": [
                "1. 打开购物车页面",
                "2. 点击结算按钮",
                "3. 选择支付方式为支付宝支付",
                "4. 确认支付金额为100-1000元人民币",
                "5. 点击支付按钮"
            ],
            "预期结果": "支付成功，页面显示支付完成信息，余额扣减正确",
            "优先级": "P1"
        }
    ]""",
            "边界值分析": """[
        {
            "用例编号": "INPUT-001",
            "用例标题": "输入字段长度校验 [边界值测试]",
            "前置条件": "系统显示用户注册页面",
            "测试数据": {
                "用户名": "1个字符",
                "密码": "8个字符",
                "邮箱": "test@example.com"
            },
            "操作步骤": [
                "1. 打开注册页面",
                "2. 在用户名字段输入1个字符",
                "3. 在密码字段输入8个字符",
                "4. 在邮箱字段输入有效邮箱地址",
                "5. 点击提交按钮"
            ],
            "预期结果": "系统提示注册成功",
            "优先级": "P1"
        },
        {
            "用例编号": "INPUT-002",
            "用例标题": "输入字段长度校验 [反例，超长输入]",
            "前置条件": "系统显示用户注册页面",
            "测试数据": {
                "用户名": "超过50个字符",
                "密码": "8个字符",
                "邮箱": "test@example.com"
            },
            "操作步骤": [
                "1. 打开注册页面",
                "2. 在用户名字段输入超过50个字符",
                "3. 在密码字段输入8个字符",
                "4. 在邮箱字段输入有效邮箱地址",
                "5. 点击提交按钮"
            ],
            "预期结果": "系统提示用户名长度超限",
            "优先级": "P2"
        }
    ]""",
            "等价类划分": """[
        {
            "用例编号": "LOGIN-001",
            "用例标题": "登录功能 [有效等价类]",
            "前置条件": "用户已注册",
            "测试数据": {
                "用户名": "valid_user",
                "密码": "correct_password"
            },
            "操作步骤": [
                "1. 打开登录页面",
                "2. 输入用户名为valid_user",
                "3. 输入密码为correct_password",
                "4. 点击登录按钮"
            ],
            "预期结果": "登录成功，跳转到首页",
            "优先级": "P1"
        },
        {
            "用例编号": "LOGIN-002",
            "用例标题": "登录功能 [无效等价类]",
            "前置条件": "用户已注册",
            "测试数据": {
                "用户名": "invalid_user",
                "密码": "random_password"
            },
            "操作步骤": [
                "1. 打开登录页面",
                "2. 输入用户名为invalid_user",
                "3. 输入密码为random_password",
                "4. 点击登录按钮"
            ],
            "预期结果": "登录失败，提示用户名或密码错误",
            "优先级": "P1"
        }
    ]""",
            "状态转换": """[
        {
            "用例编号": "ORDER-001",
            "用例标题": "订单状态转换 [正常流程]",
            "前置条件": "用户购物车内有商品，订单创建成功",
            "测试数据": {
                "初始状态": "已创建",
                "操作": "用户付款"
            },
            "操作步骤": [
                "1. 用户点击付款按钮",
                "2. 系统执行支付操作",
                "3. 支付成功后更新订单状态"
            ],
            "预期结果": "订单状态从'已创建'变为'已支付'",
            "优先级": "P1"
        },
        {
            "用例编号": "ORDER-002",
            "用例标题": "订单状态转换 [非法状态]",
            "前置条件": "订单状态为已取消",
            "测试数据": {
                "初始状态": "已取消",
                "操作": "用户付款"
            },
            "操作步骤": [
                "1. 用户尝试付款已取消的订单",
                "2. 系统拦截付款请求"
            ],
            "预期结果": "操作失败，提示订单已取消，无法付款",
            "优先级": "P2"
        }
    ]""",
            "决策表": """[
        {
            "用例编号": "DISCOUNT-001",
            "用例标题": "会员折扣规则 [决策表测试]",
            "前置条件": "系统具有会员等级和折扣规则",
            "测试数据": {
                "会员等级": "黄金会员",
                "消费金额": "500元"
            },
            "操作步骤": [
                "1. 用户登录账号，确认为黄金会员",
                "2. 添加商品到购物车，消费金额为500元",
                "3. 点击结算按钮"
            ],
            "预期结果": "系统计算折扣，实际支付金额为450元",
            "优先级": "P1"
        }
    ]""",
            "错误推测": """[
        {
            "用例编号": "UPLOAD-001",
            "用例标题": "文件上传 [异常输入]",
            "前置条件": "用户已登录，进入文件上传页面",
            "测试数据": {
                "文件类型": "exe文件",
                "文件大小": "10MB"
            },
            "操作步骤": [
                "1. 用户选择一个exe文件",
                "2. 点击上传按钮"
            ],
            "预期结果": "系统提示不支持的文件类型，上传失败",
            "优先级": "P2"
        }
    ]""",
            "场景法": """[
        {
            "用例编号": "CHECKOUT-001",
            "用例标题": "用户购买商品 [主成功场景]",
            "前置条件": "用户已登录，购物车内有商品",
            "测试数据": {
                "商品": "智能手机",
                "支付方式": "支付宝"
            },
            "操作步骤": [
                "1. 用户进入购物车页面",
                "2. 点击结算按钮",
                "3. 填写收货地址",
                "4. 选择支付方式为支付宝",
                "5. 确认订单并付款"
            ],
            "预期结果": "订单支付成功，显示订单详情",
            "优先级": "P1"
        }
    ]""",
            "因果图": """[
        {
            "用例编号": "LOGIN-003",
            "用例标题": "登录功能 [因果关系测试]",
            "前置条件": "系统有登录模块",
            "测试数据": {
                "用户名": "admin",
                "密码": "correct_password"
            },
            "操作步骤": [
                "1. 用户输入用户名为admin",
                "2. 输入密码为correct_password",
                "3. 点击登录按钮"
            ],
            "预期结果": "登录成功，跳转到管理页面",
            "优先级": "P1"
        },
        {
            "用例编号": "LOGIN-004",
            "用例标题": "登录功能 [因果关系测试 - 异常输入]",
            "前置条件": "系统有登录模块",
            "测试数据": {
                "用户名": "admin",
                "密码": "wrong_password"
            },
            "操作步骤": [
                "1. 用户输入用户名为admin",
                "2. 输入密码为wrong_password",
                "3. 点击登录按钮"
            ],
            "预期结果": "登录失败，提示用户名或密码错误",
            "优先级": "P1"
        }
    ]"""
        }
        return examples.get(method, "此方法示例未实现")

    def load_stylesheet(self):
        """加载界面样式表"""
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
                background-color: #409EFF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #66B1FF;
            }
            QPushButton#generateButton {
                background-color: #67C23A;
            }
            QPushButton#generateButton:hover {
                background-color: #85CE61;
            }
            QTextEdit {
                border: 1px solid #DCDFE6;
                border-radius: 4px;
                padding: 10px;
                font-family: Consolas;
            }
        """

    def add_knowledge_base(self):
        """ 添加知识库目录（修改版）"""
        directory = QFileDialog.getExistingDirectory(self, "选择知识库目录")
        if directory:
            if directory not in self.knowledge_bases:
                self.knowledge_bases.append(directory)
                self.combo_kb.addItem(directory)
                self.combo_kb.setCurrentText(directory)
                self.save_knowledge_bases()  # 新增持久化存储

    def load_knowledge_bases(self):
        """ 加载知识库历史记录（修改版）"""
        # 测试目录
        self.knowledge_bases = [
            r"D:\ai_case"
        ]
        self.knowledge_bases = list(set(self.knowledge_bases))
        self.combo_kb.clear()
        self.combo_kb.addItems(self.knowledge_bases)

    def save_knowledge_bases(self):
        """持久化存储知识库目录"""
        pass

    def load_directory(self, directory):
        """ 加载目录文件（修正版）"""
        try:
            self.current_dir = directory
            self.file_list.clear()

            if not directory:
                return

            if not os.path.exists(directory):
                QMessageBox.warning(self, "路径错误", f"目录不存在: {directory}")
                return

            # 优化文件过滤逻辑
            valid_extensions = ('.docx', '.xlsx', '.md', '.txt', '.pdf', '.json', 'yml', 'yaml')
            for fname in sorted(os.listdir(directory)):
                full_path = os.path.join(directory, fname)
                if os.path.isfile(full_path) and fname.lower().endswith(valid_extensions):
                    item = QListWidgetItem(fname)
                    item.setData(Qt.UserRole, full_path)
                    item.setToolTip(full_path)  # 添加路径提示
                    self.file_list.addItem(item)

            # 添加数量提示
            self.statusBar().showMessage(f"已加载 {self.file_list.count()} 个文档", 3000)

        except Exception as e:
            QMessageBox.critical(self, "加载错误", str(e))

    def update_preview(self):
        """ 更新预览内容 """
        # self.preview_area.clear()
        print(f"self.file_list.selectedItems():{self.file_list.selectedItems()}")
        selected = [item.data(Qt.UserRole) for item in self.file_list.selectedItems()]
        content = []
        all_content = ''
        for path in selected:
            raw_text = self.read_file(path)
            print(f"raw_textraw_text:{raw_text}")
            print(f"1221123123213213:{self.module_input.text()}")

            # 根据文件类型处理内容
            if path.endswith('docx'):
                if not self.module_input.text():  # 未获取到文本标签，则使用默认清洗规则
                    # cleaned = self.clean_text(raw_text)  # 注释掉未实现的方法
                    content.append(raw_text)
                else:
                    content.append({"paragraphs": raw_text})  # 拼接数据
            elif path.endswith('.pdf'):
                # PDF文件直接返回文本内容，需要特殊处理
                content.append(raw_text)  # PDF读取函数已返回正确格式
            else:
                content.append(raw_text)

        # 根据文件类型更新预览内容
        for path in selected:
            if path.endswith('docx'):
                if not self.module_input.text() and path.endswith('docx'):  # 不指定，使用默认配置进行清洗
                    for ele in content:
                        if isinstance(ele, dict) and "paragraphs" in ele:
                            all_content += "\n".join(ele["paragraphs"])
                        else:
                            all_content += str(ele)
                    self.context = self.chunk_text(all_content)  # 不输入文本标题时，也对文本进行分块
                elif self.module_input.text() and path.endswith('docx'):  # 指定标题获取文档内容
                    try:
                        for ele in content:
                            if isinstance(ele, dict) and "paragraphs" in ele:
                                paragraph = ele['paragraphs']
                                for key, value in paragraph.items():
                                    all_content += f'{str(value)} \n'  # 获取指定标题内容
                        self.context = self.chunk_text(all_content)
                    except Exception as e:
                        QMessageBox.critical(self, "预览", f"更新预览内容失败，错误信息{e}！")
            elif path.endswith('.pdf'):
                # 处理PDF文件内容
                for ele in content:
                    if isinstance(ele, dict) and "paragraphs" in ele:
                        # 处理PDF返回的结构化数据
                        for paragraph in ele["paragraphs"]:
                            all_content += str(paragraph) + "\n"
                    else:
                        all_content += str(ele)
                self.context = self.chunk_text(all_content)
            elif path.split('.')[-1].lower() in ('txt', 'xlsx', 'md'):
                if isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict) and "paragraphs" in content[0]:
                        all_content = "\n".join(content[0]["paragraphs"])
                    else:
                        all_content = content[0] if isinstance(content[0], str) else str(content[0])
            elif path.split('.')[-1].lower() in ('json', 'yml', 'yaml'):
                if isinstance(content, list) and len(content) > 0:
                    all_content = content[0].get('paragraphs', '获取内容失败') if isinstance(content[0], dict) else str(
                        content[0])
                    self.context = self.chunk_json(all_content) if isinstance(all_content,
                                                                              (dict, list)) else self.chunk_text(
                        str(all_content))
                    all_content = json.dumps(all_content, indent=4, ensure_ascii=False) if isinstance(all_content, (
                        dict, list)) else str(all_content)

        self.preview_area.setText(all_content)

    def read_file(self, file_path):
        """ 多格式文件读取 """
        try:
            if file_path.endswith('.docx'):
                try:
                    if not self.module_input.text():  # 如果没有文本标题输入
                        # 需要实现 extract_content 方法
                        doc = self.extract_content(file_path)
                    else:
                        # 需要实现 extract_text_by_title 方法
                        doc = self.extract_text_by_title(file_path,
                                                         self.module_input.text(),  # 文本标题
                                                         self.module_input_table.text(),  # 表格标题
                                                         self.module_input_pic.text())  # 图片标题
                    return doc
                except Exception as e:
                    print(f"读取docx文件出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return ""
            elif file_path.endswith('.pdf'):
                try:
                    from PyPDF2 import PdfReader
                    with open(file_path, 'rb') as f:
                        reader = PdfReader(f)
                        pages_text = []
                        for page in reader.pages:
                            try:
                                # 提取页面文本
                                text = page.extract_text()
                                # 处理可能的编码问题
                                if text:
                                    # 移除特殊控制字符
                                    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
                                    # 处理常见的乱码字符
                                    text = text.encode('utf-8', errors='ignore').decode('utf-8')
                                pages_text.append(text if text else "")
                            except Exception as page_e:
                                print(f"提取PDF页面文本时出错: {page_e}")
                                pages_text.append("")
                        # 合并所有页面文本
                        combined_text = '\n'.join(pages_text)
                        # 清理多余的空白行
                        combined_text = '\n'.join(line for line in combined_text.split('\n') if line.strip())
                        # 返回与Word文档一致的结构化格式
                        return {"paragraphs": [combined_text], "tables": []}
                except Exception as e:
                    print(f"读取pdf文件出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return {"paragraphs": [""], "tables": []}  # 保证返回一致的数据结构

            elif file_path.endswith('.xlsx'):
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    # 将 DataFrame 转换为 Markdown 格式
                    excel_content = df.to_markdown(index=False)
                    return excel_content
                except Exception as e:
                    error_msg = f"无法读取Excel文件: {str(e)}"
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                    QMessageBox.critical(self, "错误", error_msg)
                    return ""
            elif file_path.endswith('.md'):
                try:
                    import markdown
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return markdown.markdown(f.read())
                except Exception as e:
                    print(f"读取markdown文件出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return ""
            elif file_path.endswith('.txt'):
                try:
                    # 尝试多种编码方式读取
                    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                    for encoding in encodings:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                content = f.read()
                            return content
                        except UnicodeDecodeError:
                            continue
                    # 如果所有编码都失败
                    raise Exception("无法使用常见编码读取文件")
                except Exception as e:
                    print(f"读取txt文件出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return ""
            elif file_path.endswith('.json'):
                try:
                    import json
                    # 尝试多种编码方式读取
                    encodings = ['utf-8', 'gbk', 'gb2312']
                    for encoding in encodings:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                return json.load(f)
                        except UnicodeDecodeError:
                            continue
                    # 如果所有编码都失败
                    raise Exception("无法使用常见编码读取JSON文件")
                except Exception as e:
                    print(f"读取json文件出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return ""
            elif file_path.endswith(('.yaml', '.yml')):
                try:
                    import yaml
                    # 尝试多种编码方式读取
                    encodings = ['utf-8', 'gbk', 'gb2312']
                    for encoding in encodings:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                return yaml.safe_load(f)
                        except UnicodeDecodeError:
                            continue
                    # 如果所有编码都失败
                    raise Exception("无法使用常见编码读取YAML文件")
                except Exception as e:
                    print(f"读取yaml文件出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return ""
        except Exception as e:
            error_msg = f"读取文件时发生未知错误: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "读取错误", error_msg)
            return ""

    def extract_content(self, file_path):
        """
        提取Word文档内容
        """
        try:
            from docx import Document
            doc = Document(file_path)
            content = {"paragraphs": [], "tables": []}

            # 提取段落内容
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    content["paragraphs"].append(text)

            # 提取表格内容
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                content["tables"].append(table_data)

            return content
        except Exception as e:
            print(f"提取Word文档内容时出错: {e}")
            import traceback
            traceback.print_exc()
            return {"paragraphs": [], "tables": []}

    def extract_text_by_title(self, docx_path, title_keywords, table_keywords, pic_keywords):
        """
        根据标题提取Word文档内容
        """
        try:
            from docx import Document
            doc = Document(docx_path)
            result = {}

            for title_keyword in title_keywords.split(','):
                content = []
                capture = False
                for paragraph in doc.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        # 判断是否是标题
                        if title_keyword in text:
                            capture = True
                            content.append(text)
                            continue
                        # 捕获正文内容
                        if capture and text:
                            content.append(text)
                result[title_keyword] = "\n".join(content)
            return result
        except Exception as e:
            print(f"根据标题提取内容时出错: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def generate_report(self):
        """ 生成分析报告 """
        if not self.prompt_input.toPlainText().strip():
            QMessageBox.warning(self, "提示", "请输入提示词！")
            return
        context = self.preview_area.toPlainText()
        if not self.context and context:
            self.context = self.chunk_text(context)  # 如果没有分块，则在此对预览框中的文本进行分块
        if not context:
            QMessageBox.warning(self, "提示", "内容预览框中无数据，请求大模型终止！")
            return

        # 获取API Key
        self.api_key = self.api_key_input.text().strip()
        if not self.api_key:
            reply = QMessageBox.question(self, "提示", "未输入API Key，将使用默认配置。是否继续？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        # 禁用按钮防止重复点击
        self.generate_btn.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.job_area = self.comboBox.currentText()
        self.func_type = self.func_choice_combo.currentText()
        self.design_method = self.method_combo.get_selected_items_text()

        # 创建异步线程，传递API Key
        self.thread = GenerateThread(
            prompt=self.prompt_input.toPlainText(),
            context=self.context,
            job_area=self.job_area,
            func_type=self.func_type,
            design_method=self.design_method,
            api_key=self.api_key  # 传递API Key
        )
        self.thread.finished.connect(self.on_generation_finished)
        self.thread.error.connect(self.on_generation_error)
        self.thread.start()

    def on_generation_finished(self, result):
        """ 生成完成处理 """
        # 确保结果显示为字符串
        if isinstance(result, (dict, list)):
            self.result_area.setText(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            self.result_area.setText(str(result))
        self.generate_btn.setEnabled(True)
        QApplication.restoreOverrideCursor()

    def on_generation_error(self, error_msg):
        """ 错误处理 """
        QMessageBox.critical(self, "生成错误", f"模型调用失败:\n{error_msg}")
        self.generate_btn.setEnabled(True)
        QApplication.restoreOverrideCursor()

    def json_to_excel(self, json_data, output_file):
        """
        将JSON数据转换为Excel文件
        :param json_data: JSON数据（字符串或字典）
        :param output_file: 输出的Excel文件路径
        """
        try:
            import pandas as pd
            import json

            # 如果输入是JSON字符串，解析为字典
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data

            # 如果数据是列表，直接转换为DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            # 如果数据是字典，尝试提取其中的列表
            elif isinstance(data, dict):
                # 查找字典中的列表值
                list_data = None
                for key, value in data.items():
                    if isinstance(value, list):
                        list_data = value
                        break
                if list_data:
                    df = pd.DataFrame(list_data)
                else:
                    # 如果没有找到列表，将字典转换为单行DataFrame
                    df = pd.DataFrame([data])
            else:
                raise ValueError("不支持的数据格式")

            # 保存为Excel文件
            df.to_excel(output_file, index=False)
        except Exception as e:
            print(f"转换为Excel时出错: {e}")
            import traceback
            traceback.print_exc()

    def export_result(self):
        """ 导出结果 """
        if not self.result_area.toPlainText():
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "保存结果",
            filter=self.get_export_filters()
        )
        if path:
            try:
                content = self.result_area.toPlainText()
                if path.endswith('.docx'):
                    from docx import Document
                    doc = Document()
                    doc.add_paragraph(content)
                    doc.save(path)
                elif path.endswith('.md'):
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                elif path.endswith(".json"):
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(content)
                elif path.endswith(".xlsx"):
                    self.json_to_excel(content, path)
                else:  # txt
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)

                QMessageBox.information(self, "导出成功", "文件已保存！")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", str(e))

    def get_export_filters(self):
        """ 获取导出文件格式过滤器 """
        index = self.export_combo.currentIndex()
        return {
            0: "Word Documents (*.docx)",
            1: "Text Files (*.txt)",
            2: "Markdown Files (*.md)",
            3: "JSON Files (*.json)",
            4: "Excel Files (*.xlsx)"
        }[index]

    def chunk_text(self, text, chunk_size=1000, overlap=200):
        """
        将文本按固定长度分块，同时添加滑动窗口重叠。

        参数：
        - text (str): 输入的长文本内容
        - chunk_size (int): 每块的最大字符数
        - overlap (int): 相邻块的重叠字符数

        返回：
        - list: 分块后的文本列表
        """
        print("开始对文本进行分块")
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)

            # 滑动窗口：下一块的起始位置向后移动 chunk_size - overlap
            start += chunk_size - overlap

        print(f"分块完成，共生成 {len(chunks)} 个块。")
        return chunks

    def chunk_json(self, content, max_chunk_size=1000):
        """
        将JSON内容按接口定义分块，确保接口数据完整。

        参数：
        - content: JSON内容（字典或列表）
        - max_chunk_size (int): 每个分块的最大字符数

        返回：
        - list: 分块后的接口定义列表
        """
        print("开始对JSON内容进行分块~~")
        chunks = []
        current_chunk = ""
        current_size = 0

        for n, interface in enumerate(content):
            interface_content = json.dumps(interface, indent=2, ensure_ascii=False)
            interface_size = len(interface_content)

            if current_size + interface_size > max_chunk_size:
                if n == 0:  # bug修复，当json对象列表的第一个元素尺寸就大于最大分隔尺寸时，则将第一个元素添加到分块列表中
                    chunks.append(interface_content)
                else:
                    chunks.append(current_chunk)
                current_chunk = interface_content
                current_size = interface_size
                n += 1
            else:
                current_chunk += "\n" + interface_content
                current_size += interface_size
                n += 1

        if current_chunk:
            chunks.append(current_chunk)

        return chunks