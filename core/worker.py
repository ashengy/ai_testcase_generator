# core/worker.py
import json
import os
import re
from typing import List, Dict, Any, Union

from PyQt5.QtCore import QThread, pyqtSignal
from openai import OpenAI
from core.utils import normalize_data
from core.pdf_image_ai_analyzer import PDFImageAIAnalyzer
from core.pdf_image_replace import extract_pdf_text_with_image_list
from core.word_image_ai_analyzer import WordImageAIAnalyzer
from core.word_image_replace import insert_image_position_with_list


class GenerateThread(QThread):
    """异步生成线程"""
    finished = pyqtSignal(str)
    current_status = pyqtSignal(str)
    current_stage = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, prompt, context, job_area, func_type, design_method, api_key=None):
        super().__init__()
        self.prompt = prompt
        self.job_area = job_area
        self.func_type = func_type
        self.design_method = design_method
        self.api_key = api_key  # 添加API Key参数
        self.context = context

    def generate_cases(self, chunk_data):
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=self.api_key if self.api_key else 'sk-8509fd7dfb9248e49334111e24141d22',  # 使用传入的API Key
            base_url='https://api.deepseek.com',
        )

        reasoning_content = ""  # 定义完整思考过程
        answer_content = ""  # 定义完整回复
        is_answering = False  # 判断是否结束思考过程并开始回复

        # 创建聊天完成请求
        print("开始跟AI进行会话.........")
        completion = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {'role': 'user', 'content': f'所在行业:  {self.job_area}；'
                                            f'文档内容： {chunk_data}； '
                                            f'生成的用例类型： {self.func_type}； '
                                            f'用例设计方法： {self.design_method}； '
                                            f'提示词：{self.prompt}；'}
            ],
            stream=True,
            max_tokens=64000 - 4000,
        )

        print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")
        for chunk in completion:
            if not chunk.choices:
                print("\nUsage:")
                print(chunk.usage)
            else:
                delta = chunk.choices[0].delta
                # 打印思考过程
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                    print(delta.reasoning_content, end='', flush=True)
                    reasoning_content += delta.reasoning_content
                else:
                    # 开始回复
                    if delta.content != "" and not is_answering:
                        print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                        is_answering = True
                    # 打印回复过程
                    print(delta.content, end='', flush=True)
                    answer_content += delta.content
                    self.current_status.emit(f"\n{answer_content}\n")
        print(f"思考字数：{len(reasoning_content)}")
        return answer_content

    def fix_and_extract_json(self, text: str) -> Union[List[Dict], Dict, str]:
        """
        修复整个文本中的JSON，使其变成有效的JSON
        返回修复后的JSON对象或原始文本
        """
        print("=" * 80)
        print("开始修复JSON过程")
        print("=" * 80)
        print(f"原始文本长度: {len(text)}")
        print("\n原始文本预览:")
        print("-" * 40)
        print(self._truncate_text(text, 500))
        print("-" * 40)

        # 步骤1: 清理文本
        cleaned_text = self._clean_json_text(text)

        # 步骤2: 尝试直接解析
        print("\n" + "=" * 40)
        print("尝试直接解析原始文本...")
        print("=" * 40)
        try:
            result = json.loads(cleaned_text)
            print("✓ 文本已经是有效的JSON，无需修复")
            print(f"解析结果类型: {type(result).__name__}")
            return result
        except json.JSONDecodeError as e:
            print(f"✗ JSON解析错误: {e}")
            print(f"错误位置: line {e.lineno} column {e.colno} (char {e.pos})")

            # 显示错误位置的上下文
            if hasattr(e, 'pos') and e.pos is not None:
                start = max(0, e.pos - 100)
                end = min(len(cleaned_text), e.pos + 100)
                error_context = cleaned_text[start:end]
                print(f"错误位置上下文:\n...{repr(error_context)}...")

        # 步骤3: 尝试修复并解析
        print("\n" + "=" * 40)
        print("开始修复JSON结构...")
        print("=" * 40)
        fixed_json = self._repair_json_structure(cleaned_text)

        print("\n" + "=" * 40)
        print("修复前后对比")
        print("=" * 40)
        print("修复前 (清理后文本):")
        print("-" * 40)
        print(self._truncate_text(cleaned_text, 300))
        print("-" * 40)
        print(f"长度: {len(cleaned_text)}")

        print("\n修复后文本:")
        print("-" * 40)
        print(self._truncate_text(fixed_json, 300))
        print("-" * 40)
        print(f"长度: {len(fixed_json)}")

        # 步骤4: 尝试解析修复后的JSON
        print("\n" + "=" * 40)
        print("尝试解析修复后的JSON...")
        print("=" * 40)
        try:
            result = json.loads(fixed_json)
            print("✓ 修复后成功解析JSON")
            print(f"解析结果类型: {type(result).__name__}")

            # 显示修复后的JSON结构信息
            if isinstance(result, list):
                print(f"列表包含 {len(result)} 个元素")
                if result and isinstance(result[0], dict):
                    print(f"第一个元素的键: {list(result[0].keys())[:5]}")
            elif isinstance(result, dict):
                print(f"字典的键: {list(result.keys())[:5]}")

            return result
        except json.JSONDecodeError as e:
            print(f"✗ 修复后仍然无法解析: {e}")
            print(f"错误位置: line {e.lineno} column {e.colno} (char {e.pos})")

            # 如果还是失败，尝试提取和合并
            print("\n" + "=" * 40)
            print("尝试提取和合并JSON对象...")
            print("=" * 40)
            return self._extract_and_merge_json_objects(cleaned_text)

    def _truncate_text(self, text: str, max_len: int = 200) -> str:
        """截断文本，显示开头和结尾"""
        if len(text) <= max_len:
            return text
        half = max_len // 2
        return text[:half] + " ... [中间部分已省略] ... " + text[-half:]

    def _clean_json_text(self, text: str) -> str:
        """清理JSON文本，移除markdown代码块标记等"""
        print("清理JSON文本...")
        original_text = text
        print(f"原始长度: {len(text)}")

        # 移除```json和```标记
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = re.sub(r'```', '', text)

        # 移除多余的空行
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.rstrip()  # 只移除右边的空格
            cleaned_lines.append(line)

        # 重新组合
        cleaned_text = '\n'.join(cleaned_lines)

        print(f"清理后长度: {len(cleaned_text)}")
        if cleaned_text != original_text:
            print("清理内容对比:")
            print("原始开头:", repr(original_text[:100]))
            print("清理后开头:", repr(cleaned_text[:100]))
        else:
            print("文本无需清理")

        return cleaned_text

    def _repair_json_structure(self, text: str) -> str:
        """修复JSON结构问题"""
        print("修复JSON结构...")
        original_text = text

        if not text.strip():
            print("文本为空，返回空数组")
            return '[]'

        # 确保文本以有效字符开头
        text = text.strip()
        original_stripped = text

        if not text.startswith(('{', '[')):
            # 查找第一个{或[
            brace_pos = text.find('{')
            bracket_pos = text.find('[')

            if brace_pos != -1 and (bracket_pos == -1 or brace_pos < bracket_pos):
                removed_prefix = text[:brace_pos]
                text = text[brace_pos:]
                print(f"移除了开头的 {brace_pos} 个字符")
                print(f"移除的内容: {repr(removed_prefix)}")
                print(f"现在以{{开头")
            elif bracket_pos != -1 and (brace_pos == -1 or bracket_pos < brace_pos):
                removed_prefix = text[:bracket_pos]
                text = text[bracket_pos:]
                print(f"移除了开头的 {bracket_pos} 个字符")
                print(f"移除的内容: {repr(removed_prefix)}")
                print(f"现在以[开头")
            else:
                # 没有找到{或[，包装成数组
                print("未找到JSON结构，包装成数组")
                print(f"包装前: {repr(text[:100])}")
                result = f'[{text}]'
                print(f"包装后: {repr(result[:100])}")
                return result

        # 检查括号是否匹配
        stack = []
        char_map = {')': '(', ']': '[', '}': '{'}
        bracket_changes = []

        for i, char in enumerate(text):
            if char in '([{':
                stack.append((char, i))
            elif char in ')]}':
                if stack and stack[-1][0] == char_map[char]:
                    stack.pop()
                else:
                    bracket_changes.append(f"位置 {i} 的括号不匹配: {char}")

        # 如果有括号不匹配问题，打印出来
        if bracket_changes:
            print(f"发现 {len(bracket_changes)} 个括号不匹配问题:")
            for change in bracket_changes[:5]:  # 只显示前5个
                print(f"  - {change}")
            if len(bracket_changes) > 5:
                print(f"  - ... 还有 {len(bracket_changes) - 5} 个问题")

        # 补全缺失的括号
        missing_brackets = []
        while stack:
            missing_char, pos = stack.pop()
            if missing_char == '(':
                text += ')'
            elif missing_char == '[':
                text += ']'
            elif missing_char == '{':
                text += '}'
            missing_brackets.append((missing_char, pos))
            print(f"在位置 {pos} 补全了 {missing_char}")

        # 修复末尾逗号
        comma_fixes = []

        def comma_replacer(match):
            comma_fixes.append(match.group(0))
            return match.group(1)  # 返回匹配的闭合括号

        text = re.sub(r',(\s*[}\]])', comma_replacer, text)
        if comma_fixes:
            print(f"修复了 {len(comma_fixes)} 个末尾逗号问题")
            for i, fix in enumerate(comma_fixes[:3]):  # 只显示前3个
                print(f"  - {repr(fix)}")
            if len(comma_fixes) > 3:
                print(f"  - ... 还有 {len(comma_fixes) - 3} 个")

        # 修复可能的多余逗号
        double_comma_fixes = len(re.findall(r',\s*,', text))
        if double_comma_fixes:
            text = re.sub(r',\s*,', ',', text)
            print(f"修复了 {double_comma_fixes} 个连续逗号问题")

        # 修复可能缺少的引号
        # 查找未闭合的字符串
        unclosed_strings = re.findall(r'"(?:[^"\\]|\\.)*?(?<!")$', text)
        if unclosed_strings:
            print(f"发现 {len(unclosed_strings)} 个未闭合的字符串")
            for s in unclosed_strings[:3]:
                print(f"  - {repr(s)}")

        print(f"修复前长度: {len(original_stripped)}")
        print(f"修复后长度: {len(text)}")

        # 总结修复内容
        total_fixes = len(bracket_changes) + len(missing_brackets) + len(comma_fixes) + double_comma_fixes
        if total_fixes > 0:
            print(f"总共进行了 {total_fixes} 处修复:")
            if bracket_changes:
                print(f"  - 括号不匹配: {len(bracket_changes)} 处")
            if missing_brackets:
                print(f"  - 补全括号: {len(missing_brackets)} 处")
            if comma_fixes:
                print(f"  - 末尾逗号: {len(comma_fixes)} 处")
            if double_comma_fixes:
                print(f"  - 连续逗号: {double_comma_fixes} 处")
        else:
            print("未发现需要修复的结构问题")

        return text

    def _extract_and_merge_json_objects(self, text: str) -> Union[List[Dict], str]:
        """
        从文本中提取所有JSON对象并合并
        作为最后的备选方案
        """
        print("尝试提取并合并JSON对象...")
        print(f"原始文本长度: {len(text)}")

        json_objects = []

        # 匹配JSON对象模式
        patterns = [
            # 匹配完整的对象 { ... }
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
            # 匹配完整的数组 [ ... ]
            r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',
        ]

        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            all_matches.extend(matches)

        print(f"找到 {len(all_matches)} 个潜在JSON对象")

        # 显示每个找到的对象
        for i, match in enumerate(all_matches[:5]):  # 只显示前5个
            print(f"对象 {i + 1} (长度 {len(match)}):")
            print(f"  预览: {self._truncate_text(match, 100)}")

        if len(all_matches) > 5:
            print(f"  ... 还有 {len(all_matches) - 5} 个对象")

        valid_objects = []
        invalid_objects = []
        for i, match in enumerate(all_matches):
            try:
                obj = json.loads(match)
                valid_objects.append(obj)
                print(f"对象 {i + 1}: ✓ 成功解析，类型: {type(obj).__name__}")
            except json.JSONDecodeError as e:
                invalid_objects.append((i, match, str(e)))
                print(f"对象 {i + 1}: ✗ 解析失败，错误: {e}")
                # 尝试修复后解析
                try:
                    fixed = self._repair_json_structure(match)
                    obj = json.loads(fixed)
                    valid_objects.append(obj)
                    print(f"对象 {i + 1}: ✓ 修复后成功解析")
                except Exception as e2:
                    print(f"对象 {i + 1}: ✗ 修复后仍然无法解析: {e2}")
                    continue

        print(f"有效对象: {len(valid_objects)}, 无效对象: {len(invalid_objects)}")

        if not valid_objects:
            print("未找到有效的JSON对象，返回原始文本")
            return text

        # 合并所有对象
        merged = self._merge_json_objects(valid_objects)
        print(f"成功合并 {len(valid_objects)} 个对象")

        return merged

    def _merge_json_objects(self, objects: List[Any]) -> List[Dict]:
        """合并多个JSON对象"""
        print(f"开始合并 {len(objects)} 个JSON对象")

        merged_list = []
        stats = {
            'list': 0,
            'dict': 0,
            'other': 0
        }

        for i, obj in enumerate(objects):
            if isinstance(obj, list):
                stats['list'] += 1
                print(f"对象 {i + 1}: 列表类型，包含 {len(obj)} 个元素")
                # 如果是数组，展开添加到结果中
                for j, item in enumerate(obj):
                    if isinstance(item, dict):
                        merged_list.append(item)
                    elif isinstance(item, list):
                        # 嵌套数组，递归处理
                        merged_list.extend(self._merge_json_objects([item]))
                    else:
                        print(f"  元素 {j + 1}: 跳过非字典类型 {type(item).__name__}")
            elif isinstance(obj, dict):
                stats['dict'] += 1
                print(f"对象 {i + 1}: 字典类型")
                merged_list.append(obj)
            else:
                stats['other'] += 1
                print(f"对象 {i + 1}: 跳过非字典/数组类型: {type(obj).__name__}")

        print(f"合并统计: 列表 {stats['list']} 个, 字典 {stats['dict']} 个, 其他 {stats['other']} 个")
        print(f"最终合并后得到 {len(merged_list)} 个测试用例")

        return merged_list

    def extract_json_objects(self, text: str) -> List[Dict]:
        """
        主要入口点：修复并提取JSON对象
        总是返回有效的JSON对象列表
        """
        print("=" * 80)
        print("开始提取JSON对象")
        print("=" * 80)
        print(f"输入文本总长度: {len(text)}")

        result = self.fix_and_extract_json(text)

        print("\n" + "=" * 80)
        print("提取JSON对象完成")
        print("=" * 80)

        # 确保返回的是列表
        if isinstance(result, list):
            # 确保列表中的元素都是字典
            filtered_list = []
            other_types = []
            for i, item in enumerate(result):
                if isinstance(item, dict):
                    filtered_list.append(item)
                elif isinstance(item, list):
                    # 递归处理嵌套列表
                    filtered_list.extend(self._merge_json_objects([item]))
                else:
                    other_types.append((i, type(item).__name__))

            if other_types:
                print(f"跳过了 {len(other_types)} 个非字典/数组类型的元素")
                for idx, type_name in other_types[:5]:
                    print(f"  位置 {idx}: 类型 {type_name}")

            print(f"最终返回 {len(filtered_list)} 个测试用例")
            if filtered_list:
                print("第一个测试用例的键:", list(filtered_list[0].keys())[:10])
            return filtered_list
        elif isinstance(result, dict):
            print("返回单个测试用例对象")
            print("对象的键:", list(result.keys())[:10])
            return [result]
        else:
            # 如果是字符串或其它类型，包装成空列表
            print(f"未提取到JSON对象，返回空列表。结果类型: {type(result).__name__}")
            return []

    def reformat_test_cases(self, data):
        """Combines a list of test case lists into a single list and renumbers the case IDs."""
        try:
            print(f"开始格式化测试用例，数据类型: {type(data)}")

            # 如果传入的是字符串，尝试解析
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                    print(f"成功解析字符串为JSON")
                except json.JSONDecodeError:
                    # 如果是字符串但不是JSON，直接返回
                    print(f"字符串不是有效JSON，直接返回")
                    return data

            # 确保data是列表
            if not isinstance(data, list):
                data = [data] if isinstance(data, dict) else []
                print(f"将数据转换为列表，长度: {len(data)}")

           # 处理多层嵌套的源数据(第二次保护）
            data = normalize_data(data)

            # 展平所有测试用例
            flat_cases = []
            for i, item in enumerate(data):
                if isinstance(item, list):
                    print(f"元素 {i}: 列表类型，展开 {len(item)} 个元素")
                    flat_cases.extend(item)
                elif isinstance(item, dict):
                    print(f"元素 {i}: 字典类型")
                    flat_cases.append(item)
                else:
                    print(f"元素 {i}: 未知类型 {type(item).__name__}，跳过")

            print(f"展平后得到 {len(flat_cases)} 个测试用例")

            if not flat_cases:
                print("没有测试用例，返回空数组")
                return '[]'

            # 重新编号
            print("开始重新编号测试用例...")
            for i, case in enumerate(flat_cases):
                if isinstance(case, dict):
                    # 优先使用case_id，否则用例编号，都没有则创建
                    if 'case_id' in case:
                        old_id = case.get('case_id', '无')
                        case['case_id'] = f"TC_{i + 1:03}"
                        print(f"用例 {i + 1}: 更新 case_id {old_id} -> {case['case_id']}")
                    elif '用例编号' in case:
                        old_id = case.get('用例编号', '无')
                        case['用例编号'] = f'TC_{i + 1:03}'
                        print(f"用例 {i + 1}: 更新 用例编号 {old_id} -> {case['用例编号']}")
                    else:
                        case['case_id'] = f"TC_{i + 1:03}"
                        print(f"用例 {i + 1}: 添加新 case_id {case['case_id']}")

            # 返回格式化的JSON
            result = json.dumps(flat_cases, indent=2, ensure_ascii=False)
            print(f"格式化完成，JSON长度: {len(result)}")
            print(f"格式化后预览:")
            print("-" * 40)
            print(self._truncate_text(result, 300))
            print("-" * 40)
            return result

        except Exception as e:
            print(f"reformat_test_cases处理出错: {e}")
            import traceback
            traceback.print_exc()
            # 返回原始数据
            return json.dumps(data, indent=2, ensure_ascii=False) if not isinstance(data, str) else data

    def run(self):
        self.current_status.emit(f"----开始生成测试用例...----\n")
        print("self.context是", self.context)
        try:
            all_result_str = ""
            count = len(self.context)
            for n, context_chunk in enumerate(self.context):
                # 开始推理时同步进度
                self.current_stage.emit(f"当前推理进度：{n}/{count}")
                result = self.generate_cases(context_chunk)
                if result is not None and isinstance(result, str):
                    all_result_str += result
                    print(f"第 {n + 1} 个chunk结果长度: {len(result)}")
                else:
                    print(f"{context_chunk}推理结果异常！")
                # 本轮推理完成时 同步进度
                self.current_stage.emit(f"当前推理进度：{n + 1}/{count}")

            print(f"\n所有结果总长度: {len(all_result_str)}")

            # 只有当确实包含JSON相关内容时才尝试解析
            if all_result_str and ('json' in all_result_str.lower() or '{' in all_result_str or '[' in all_result_str):
                print("\n" + "=" * 80)
                print("开始整合JSON")
                print("=" * 80)
                extracted_result = self.extract_json_objects(all_result_str)
                print(f"\nJSON整合完成，提取到 {len(extracted_result)} 个对象")

                if extracted_result:
                    all_result_str = self.reformat_test_cases(extracted_result)
                    print(f"\n格式化后JSON长度: {len(all_result_str)}")
                else:
                    # 如果没有提取到有效的JSON对象，保留原始内容
                    print("未提取到有效JSON对象，使用原始内容")
                print("整合已结束")
            else:
                print("内容中未检测到JSON格式，跳过JSON解析步骤")

            self.finished.emit(all_result_str if isinstance(all_result_str, str) else str(all_result_str))
            self.current_status.emit("----本轮已执行完成！----")
        except Exception as e:
            print(f"运行异常: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class ImageAnalyzer(QThread):
    current_status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, file_path, batch_delay, image_api_key, analyzer_enable: bool):
        super().__init__()
        self.image_api_key = image_api_key
        self.file_path = file_path
        self.batch_delay = batch_delay
        self.analyzer_enable = analyzer_enable

    def run(self):
        print("启动ImageAnalyzer", flush=True)
        try:
            file_type = os.path.splitext(self.file_path)[1]
            print("查看file_type:", file_type)
            # 根据开关判断是否使用ai图片分析
            if self.analyzer_enable:
                self.current_status.emit(f"----开始启动AI分析图片...----\n")
                # 根据文件类型判断pdf or docx
                if file_type == ".pdf":
                    analyzer = PDFImageAIAnalyzer(api_key=self.image_api_key, model_name="qwen-vl-plus")
                    replacements = analyzer.process_pdf_images(self.file_path, batch_delay=self.batch_delay)
                elif file_type == ".docx":
                    analyzer = WordImageAIAnalyzer(api_key=self.image_api_key, model_name="qwen-vl-plus")
                    replacements = analyzer.process_word_images(self.file_path, batch_delay=self.batch_delay)
                for i, v in enumerate(replacements):
                    if v == "":
                        v = "无效图片，已过滤"
                    self.current_status.emit(f"第{i + 1}张图分析结果:\n {v} \n")
                self.current_status.emit(f"----AI分析已完成，共发现{len(replacements)}张图片----\n")

            else:
                # 不使用ai分析直接返回空列表(已在extract_pdf_text_with_image_list兼容了有图片但是传入列表为空的情况）
                replacements = []
            if file_type == ".pdf":
                # 传入要替换的图片文字结果的列表
                context = extract_pdf_text_with_image_list(self.file_path,  # 替换为你的PDF路径
                                                           image_replacement_list=replacements)
            elif file_type == ".docx":
                context = insert_image_position_with_list(self.file_path,  # 替换为你的PDF路径
                                                          image_replacement_list=replacements)
            else:
                context = ""
            context = context.replace("◦", "")  # 把文档里不需要的符号去掉
            context = context.replace(" ", "")  # 去空格
            context = context.replace("\n\n", "\n")
            print("文档最终内容是", context, flush=True)
            self.finished.emit(context)

        except Exception as e:
            self.error.emit(f"ImageAnalyzer运行异常：{e}")
