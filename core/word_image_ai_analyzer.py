import base64
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import List, Dict, Any
from io import BytesIO

# 使用dashscope SDK直接调用，避免LangChain的兼容性问题
import dashscope
from docx import Document
from PIL import Image
from dashscope import MultiModalConversation


@dataclass
class ImagePosition:
    """图片位置信息"""
    paragraph_index: int
    run_index: int
    width: float
    height: float
    image_index: int


class WordImageAIAnalyzer:
    def __init__(self, api_key: str, model_name: str = "qwen-vl-plus"):
        """
        初始化Word文档图片AI分析器

        Args:
            api_key: 通义千问API密钥
            model_name: 模型名称
        """
        dashscope.api_key = api_key
        self.model_name = model_name
        self.image_data = []

    def extract_images_from_word(self, word_path: str, output_dir: str = "extracted_images",
                                 min_width: int = 100, min_height: int = 100,
                                 min_file_size: int = 1024) -> List[Dict[str, Any]]:
        """
        从Word文档中提取所有图片及其位置信息，支持按尺寸和文件大小过滤

        Args:
            word_path: Word文档路径
            output_dir: 图片输出目录
            min_width: 图片最小宽度（像素）
            min_height: 图片最小高度（像素）
            min_file_size: 图片最小文件大小（字节）
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        doc = Document(word_path)
        images_info = []
        image_counter = 0

        print(f"开始从Word文档提取图片...")

        # 遍历所有段落
        for para_idx, paragraph in enumerate(doc.paragraphs):
            # 遍历段落中的所有run
            for run_idx, run in enumerate(paragraph.runs):
                # 检查run中是否包含图片
                if run._element.xpath('.//pic:pic'):
                    image_counter += 1
                    try:
                        # 获取图片元素
                        drawing = run._element.xpath('.//pic:pic')[0]
                        blip = drawing.xpath('.//a:blip/@r:embed')[0]
                        image_part = doc.part.related_parts[blip]

                        # 获取图片数据
                        image_data = image_part.blob

                        # 使用PIL打开图片获取尺寸
                        image = Image.open(BytesIO(image_data))
                        width, height = image.size

                        # 检查图片尺寸是否符合要求
                        if width < min_width or height < min_height:
                            print(f"跳过小尺寸图片: {width}x{height} (要求: {min_width}x{min_height})")
                            continue

                        # 生成唯一图片ID和文件名
                        img_hash = hashlib.md5(image_data).hexdigest()[:8]
                        img_name = f"para_{para_idx + 1}_run_{run_idx + 1}_img_{image_counter}_{img_hash}.png"
                        img_path = os.path.join(output_dir, img_name)

                        # 保存图片
                        with open(img_path, 'wb') as f:
                            f.write(image_data)

                        # 检查文件大小是否符合要求
                        file_size = os.path.getsize(img_path)
                        if file_size < min_file_size:
                            print(f"跳过小文件: {file_size} bytes (要求: {min_file_size} bytes)")
                            os.remove(img_path)  # 删除不满足条件的文件
                            continue

                        # 创建位置信息
                        position = ImagePosition(
                            paragraph_index=para_idx + 1,
                            run_index=run_idx + 1,
                            width=width,
                            height=height,
                            image_index=image_counter
                        )

                        image_info = {
                            "image_id": f"para_{para_idx + 1}_run_{run_idx + 1}_img_{image_counter}",
                            "image_hash": img_hash,
                            "image_path": img_path,
                            "position": {
                                "paragraph_index": position.paragraph_index,
                                "run_index": position.run_index,
                                "width": position.width,
                                "height": position.height,
                                "image_index": position.image_index
                            },
                            "paragraph_number": para_idx + 1,
                            "run_number": run_idx + 1,
                            "image_number": image_counter,
                            "file_size": file_size,
                            "dimensions": (width, height)
                        }

                        images_info.append(image_info)
                        print(
                            f"提取图片: {image_info['image_id']} - 位置: 第{para_idx + 1}段第{run_idx + 1}运行 - 尺寸: {width}x{height}")

                    except Exception as e:
                        print(f"提取图片错误 (段{para_idx + 1}, 运行{run_idx + 1}): {e}")
                        continue

        # 检查表格中的图片（如果需要支持表格中的图片，可以添加相关代码）
        # 这里简化处理，只处理段落中的图片

        self.image_data = images_info
        print(f"图片提取完成，共找到 {len(images_info)} 张图片")
        return images_info

    def image_to_base64(self, image_path: str) -> str:
        """
        将图片转换为base64编码
        """
        try:
            with open(image_path, "rb") as img_file:
                base64_data = base64.b64encode(img_file.read()).decode('utf-8')
            return base64_data
        except Exception as e:
            print(f"图片转base64错误: {e}")
            return ""

    def analyze_image_with_ai(self, image_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用通义千问-V分析单张图片
        """
        try:
            # 将图片转换为base64
            base64_image = self.image_to_base64(image_info["image_path"])
            if not base64_image:
                return {"error": "图片读取失败"}

            # 获取位置信息
            position = image_info["position"]

            # 构建提示词
            prompt = f"""=== 核心身份定位与工作要求 ===
你是一个图片识别专家，在游戏行业深耕10年，
请分析这张来自Word文档第{position['paragraph_index']}段第{position['run_index']}运行的图片，尺寸：{position['width']:.2f} × {position['height']:.2f}，
**强制要求规则（优先级最高）
无法识别时：如果图片质量差、内容模糊、是水印、头像、或无意义元素，直接回复："无效图片，无法识别！"
回复格式：只回复图片分析结果，绝对禁止添加任何额外话术（如"如果需要进一步分析..."等）。
禁止复制示例：示例内容仅作为格式参考，不可复用任何具体细节（如物品名称、颜色、数字等）。分析必须基于实际图片内容生成。

**特殊要求规则
无效图片处理：对于流程图、纯文字图、或其他非游戏界面内容，按实际元素描述，但必须遵循强制规则。如果无法识别或不符合游戏相关上下文，回复"无效图片，无法识别！"。
分析重点：优先检查图片类型（如UI界面、图标、文本、模型），然后分区域描述位置、颜色、文字、交互元素等。确保描述基于视觉证据，不假设内容。

**示例格式参考（仅用于结构，不可复用内容）
左上角：[描述实际存在的图标、文字及其属性]。
右上角：[描述实际存在的图标、文字及其属性]。
主要区域（如列表或模型）：
[区域背景和提示]。
[条目1：图标、名称、效果描述、数量标记]。
[条目2：图标、名称、效果描述、数量标记]。
操作区域：
[核心模型或按钮描述]。
[材料显示和操作按钮]。
其他细节：界面风格、文字信息、交互提示。
**附加指令
所有描述必须基于图片实际内容，使用中性语言（如"可能表示"而非肯定断言）。
如果图片是流程图或文字图，描述其结构、箭头、文本框等元素，不强制使用游戏术语。
"""

            # 使用dashscope直接调用多模态对话API
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": f"data:image/png;base64,{base64_image}"
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]

            print(f"开始AI分析图片: {image_info['image_id']}")

            response = MultiModalConversation.call(
                model=self.model_name,
                messages=messages
            )

            if response.status_code == 200:
                result_text = response.output.choices[0].message.content[0]['text']
                analysis_result = self._parse_ai_response(result_text)
                analysis_result["analysis_status"] = "success"
                print(f"完成AI分析: {image_info['image_id']}")
                return analysis_result
            else:
                error_msg = f"API调用失败: {response.code} - {response.message}"
                print(f"AI分析图片错误 {image_info['image_id']}: {error_msg}")
                return self._create_error_result(error_msg)

        except Exception as e:
            print(f"AI分析图片错误 {image_info['image_id']}: {e}")
            return self._create_error_result(str(e))

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析AI响应文本
        """
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                # 清理JSON字符串
                json_str = self._clean_json_string(json_str)
                parsed_data = json.loads(json_str)

                # 确保所有必需的字段都存在
                required_fields = ["image_type", "main_content", "key_information", "text_content",
                                   "purpose_analysis", "quality_evaluation", "related_suggestions"]

                for field in required_fields:
                    if field not in parsed_data:
                        parsed_data[field] = ""

                # 确保key_information是列表
                if isinstance(parsed_data.get("key_information"), str):
                    # 尝试将字符串转换为列表
                    try:
                        parsed_data["key_information"] = json.loads(parsed_data["key_information"])
                    except:
                        parsed_data["key_information"] = [parsed_data["key_information"]]
                elif not isinstance(parsed_data.get("key_information"), list):
                    parsed_data["key_information"] = []

                return parsed_data
            else:
                # 如果不是标准JSON，创建结构化响应
                return {
                    "image_type": "自动解析",
                    "main_content": response_text,
                    "key_information": [],
                    "text_content": "",
                    "purpose_analysis": "",
                    "quality_evaluation": "",
                    "related_suggestions": "",
                    "raw_response": response_text
                }
        except Exception as e:
            print(f"解析AI响应错误: {e}")
            return {
                "image_type": "解析失败",
                "main_content": response_text,
                "key_information": [],
                "text_content": "",
                "purpose_analysis": "",
                "quality_evaluation": "",
                "related_suggestions": "",
                "raw_response": response_text
            }

    def _clean_json_string(self, json_str: str) -> str:
        """清理JSON字符串"""
        # 移除可能的代码块标记
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'\s*```', '', json_str)
        # 确保双引号
        json_str = re.sub(r"'", '"', json_str)
        # 修复常见的JSON格式问题
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        return json_str.strip()

    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "analysis_status": "error",
            "error_message": error_msg,
            "image_type": "分析失败",
            "main_content": "",
            "key_information": [],
            "text_content": "",
            "purpose_analysis": "",
            "quality_evaluation": "",
            "related_suggestions": ""
        }

    def process_word_images(self, word_path: str, batch_delay: float = 1.0,
                            min_width: int = 100, min_height: int = 100,
                            min_file_size: int = 1024) -> list[str]:
        """
        处理Word文档中的所有图片

        Args:
            word_path: Word文档路径
            batch_delay: 批处理延迟时间（秒）
            min_width: 图片最小宽度（像素）
            min_height: 图片最小高度（像素）
            min_file_size: 图片最小文件大小（字节）
        """
        output_dir = "extracted_images"

        # 提取所有图片（包括不符合要求的）
        all_images_info = self.extract_images_from_word(
            word_path,
            output_dir=output_dir,
            min_width=0,  # 先提取所有图片，不过滤
            min_height=0,
            min_file_size=0
        )

        if not all_images_info:
            return []

        # 筛选出符合要求的图片
        valid_images_info = self.extract_images_from_word(
            word_path,
            output_dir=output_dir,
            min_width=min_width,
            min_height=min_height,
            min_file_size=min_file_size
        )

        # 创建符合要求图片的ID集合，用于快速查找
        valid_image_ids = {img["image_id"] for img in valid_images_info}

        print(f"总共找到 {len(all_images_info)} 张图片，其中 {len(valid_images_info)} 张符合要求")

        main_contents = []

        # 为每张图片处理结果（符合要求的进行AI分析，不符合的用占位符）
        for i, image_info in enumerate(all_images_info):
            image_id = image_info["image_id"]
            print(f"处理进度: {i + 1}/{len(all_images_info)} - {image_id}")

            # 检查图片是否符合尺寸要求
            if image_id in valid_image_ids:
                # 符合要求的图片进行AI分析
                ai_analysis = self.analyze_image_with_ai(image_info)

                main_content = ai_analysis["main_content"]
                # 对于不符合要求的图片内容，传一个空占位符
                if ("这张图片不符合规定像素尺寸要求" in main_content or
                        "无效图片，无法识别" in main_content or
                        not main_content.strip()):

                    content = ""  # 空占位符
                else:
                    content = main_content
            else:
                content = ""

            main_contents.append(content)

            # 添加延迟以避免API限制（仅对需要AI分析的图片）
            if image_id in valid_image_ids and i < len(all_images_info) - 1:
                time.sleep(batch_delay)

        print("main_contents最终结果:", main_contents)

        # AI分析完成后删除extracted_images文件夹及其内容
        try:
            if os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
                print(f"已删除 {output_dir} 文件夹及其内容")
        except Exception as e:
            print(f"删除 {output_dir} 文件夹时出错: {e}")

        return main_contents


if __name__ == "__main__":
    API_KEY = "sk-ce93575f6e8d4a02ba15f8ab38a943a1"
    WORD_PATH = r"D:\ai_case\【需求】药剂工具台.docx"  # 替换为您的Word文档路径

    # 初始化分析器
    analyzer = WordImageAIAnalyzer(api_key=API_KEY, model_name="qwen-vl-plus")

    results = analyzer.process_word_images(WORD_PATH, batch_delay=1.0)