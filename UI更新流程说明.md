# UI更新流程说明

## 优化后的工作流程

现在代码已经优化，**只需要修改UI文件后执行pyuic5即可**，无需手动修改main_window.py。

## 完整步骤

### 1. 在Qt Designer中修改UI
- 打开 `ui/DeepSeekTool.ui`
- 进行任何UI修改（布局、控件、属性等）
- **重要**：保持以下约定：
  - `label_method_combo` 标签后面必须有一个 `spacerItem`（用于占位）
  - **两个按钮的objectName**：
    - "开始推理"按钮：`generateButton`
    - "更新提示词"按钮：`refreshPromptButton`
  - （代码会自动为这两个按钮创建别名，无需手动处理）

### 2. 保存UI文件
- 在Qt Designer中保存 `ui/DeepSeekTool.ui`

### 3. 生成Python代码（仅此一步！）
```bash
python -m PyQt5.uic.pyuic ui/DeepSeekTool.ui -o ui/ui_deepseektool.py
```

或者如果已配置pyuic5命令：
```bash
pyuic5 ui/DeepSeekTool.ui -o ui/ui_deepseektool.py
```

### 4. 运行程序
```bash
python main.py
```

## 代码自动适配机制

代码会自动处理以下内容：

1. **method_combo自动替换**：
   - 自动查找包含 `label_method_combo` 的布局
   - 找到其后的 `spacerItem` 并替换为 `MultiSelectComboBox`
   - 无论布局如何变化，只要 `label_method_combo` 后面有 `spacerItem` 就能自动适配

2. **按钮别名自动创建**：
   - 自动检查是否存在 `generate_btn` 和 `refresh_prompt_btn`
   - 如果不存在，则从 `generateButton` 和 `refreshPromptButton` 创建别名
   - 如果UI中已经直接使用了这些名称，则不需要别名

3. **布局变化自动适应**：
   - 代码会遍历所有布局属性
   - 自动找到正确的布局并插入 `method_combo`
   - 无需关心布局的具体结构

## 注意事项

1. **保持spacerItem占位**：
   - 在Qt Designer中，`label_method_combo` 后面必须有一个 `spacerItem`
   - 这是代码自动替换的标记
   
   **详细解释**：
   - `label_method_combo` 是一个标签（显示"用例设计:"文字）
   - `spacerItem` 是一个**占位符**（不可见的空白空间）
   - **为什么需要占位符？**
     - 因为 `MultiSelectComboBox` 是自定义控件，Qt Designer无法直接添加
     - 所以先用 `spacerItem` 占据位置
     - 代码运行时会**自动找到这个占位符，替换成真正的 MultiSelectComboBox 控件**
   
   **在Qt Designer中的布局应该是这样**：
   ```
   [知识库目录] [下拉框] [行业] [下拉框] ... [用例设计:] [spacerItem占位] [其他控件]
                                                              ↑
                                                        这里必须是spacerItem
   ```
   
   **代码运行后的效果**：
   ```
   [知识库目录] [下拉框] [行业] [下拉框] ... [用例设计:] [MultiSelectComboBox控件] [其他控件]
                                                              ↑
                                                        自动替换成真正的控件
   ```

2. **按钮对象名**：
   - 这是**两个独立的按钮**，各自需要保持各自的objectName：
     - **"开始推理"按钮**：objectName 必须为 `generateButton`（代码会自动创建别名 `generate_btn`）
     - **"更新提示词"按钮**：objectName 必须为 `refreshPromptButton`（代码会自动创建别名 `refresh_prompt_btn`）
   - 如果修改了对象名，需要在 `main_window.py` 中更新对应的别名代码

3. **如果自动适配失败**：
   - 检查 `label_method_combo` 后面是否有 `spacerItem`
   - 检查布局结构是否正常
   - 可以查看控制台错误信息进行调试

## 如何添加新按钮

### 步骤

1. **在Qt Designer中添加按钮**：
   - 在UI中添加新的QPushButton
   - 设置按钮的 `objectName`（例如：`new_button`）
   - 保存UI文件

2. **生成Python代码**：
   ```bash
   python -m PyQt5.uic.pyuic ui/DeepSeekTool.ui -o ui/ui_deepseektool.py
   ```

3. **在main_window.py中添加按钮处理逻辑**：
   
   在 `_connect_signals()` 方法中添加按钮连接：
   ```python
   def _connect_signals(self):
       # ... 现有代码 ...
       
       # 添加新按钮连接
       if hasattr(self, 'new_button'):
           self.new_button.clicked.connect(self.new_button_handler)
   ```
   
   然后实现按钮的处理方法：
   ```python
   def new_button_handler(self):
       """新按钮的点击处理函数"""
       # 在这里添加你的业务逻辑
       pass
   ```

### 示例：添加一个"清空结果"按钮

1. **在Qt Designer中**：
   - 添加QPushButton
   - objectName设置为：`btn_clear_result`
   - 按钮文本设置为："清空结果"

2. **生成代码**：
   ```bash
   python -m PyQt5.uic.pyuic ui/DeepSeekTool.ui -o ui/ui_deepseektool.py
   ```

3. **在main_window.py中**：
   ```python
   def _connect_signals(self):
       # ... 现有代码 ...
       
       # 添加清空结果按钮
       if hasattr(self, 'btn_clear_result'):
           self.btn_clear_result.clicked.connect(self.clear_result)
   
   def clear_result(self):
       """清空结果区域"""
       self.result_area.clear()
   ```

### 注意事项

- **按钮对象名**：建议使用有意义的objectName，如 `btn_xxx` 格式
- **自动检测**：使用 `hasattr(self, 'button_name')` 可以安全地检查按钮是否存在
- **集中管理**：所有按钮连接都在 `_connect_signals()` 方法中，方便维护

**Q: 如果忘记添加spacerItem会怎样？**
A: 代码找不到占位符，`MultiSelectComboBox` 不会被创建，程序可能报错。

**Q: spacerItem的大小重要吗？**
A: 不重要，代码会替换它，大小由 `MultiSelectComboBox` 决定。

**Q: 可以放在其他位置吗？**
A: 不可以，必须紧跟在 `label_method_combo` 后面，代码是按顺序查找的。

**Q: 如果删除了spacerItem会怎样？**
A: 需要重新添加，否则 `MultiSelectComboBox` 无法正确插入到布局中。

