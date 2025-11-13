import base64
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import List, Dict, Any

# 使用dashscope SDK直接调用，避免LangChain的兼容性问题
import dashscope
import fitz  # PyMuPDF
from dashscope import MultiModalConversation


@dataclass
class ImagePosition:
    """图片位置信息"""
    page_num: int
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    height: float


class PDFImageAIAnalyzer:
    def __init__(self, api_key: str, model_name: str = "qwen-vl-plus"):
        """
        初始化PDF图片AI分析器

        Args:
            api_key: 通义千问API密钥
            model_name: 模型名称
        """
        dashscope.api_key = api_key
        self.model_name = model_name
        self.image_data = []

    def extract_images_from_pdf(self, pdf_path: str, output_dir: str = "extracted_images") -> List[Dict[str, Any]]:
        """
        从PDF中提取所有图片及其位置信息
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        doc = fitz.open(pdf_path)
        images_info = []

        print(f"开始从PDF提取图片...")
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)

                    if pix.n - pix.alpha < 4:  # 检查是否是RGB
                        # 生成唯一图片ID
                        img_hash = hashlib.md5(pix.samples).hexdigest()[:8]
                        img_name = f"page_{page_num + 1}_img_{img_index + 1}_{img_hash}.png"
                        img_path = os.path.join(output_dir, img_name)

                        # 保存图片
                        pix.save(img_path)

                        # 获取图片位置信息
                        image_instances = page.get_image_rects(xref)

                        for instance in image_instances:
                            position = ImagePosition(
                                page_num=page_num + 1,
                                x0=instance.x0,
                                y0=instance.y0,
                                x1=instance.x1,
                                y1=instance.y1,
                                width=instance.width,
                                height=instance.height
                            )

                            image_info = {
                                "image_id": f"page_{page_num + 1}_img_{img_index + 1}",
                                "image_hash": img_hash,
                                "image_path": img_path,
                                "position": {
                                    "page_num": position.page_num,
                                    "x0": position.x0,
                                    "y0": position.y0,
                                    "x1": position.x1,
                                    "y1": position.y1,
                                    "width": position.width,
                                    "height": position.height
                                },
                                "page_number": page_num + 1,
                                "image_index": img_index + 1,
                                "file_size": os.path.getsize(img_path),
                                "dimensions": (pix.width, pix.height)
                            }

                            images_info.append(image_info)
                            print(
                                f"提取图片: {image_info['image_id']} - 位置: 第{page_num + 1}页 ({position.x0:.1f}, {position.y0:.1f})")

                    pix = None  # 释放内存

                except Exception as e:
                    print(f"提取图片错误 (页{page_num + 1}, 图{img_index + 1}): {e}")
                    continue

        doc.close()
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
，请分析这张来自PDF文档第{position['page_num']}页的图片，位置坐标：({position['x0']:.2f}, {position['y0']:.2f}) 到 ({position['x1']:.2f}, {position['y1']:.2f})，尺寸：{position['width']:.2f} × {position['height']:.2f}，
=== *****强制要求规则 《强制要求规则的优先级最高>===
**无法识别时，请勿使用本关键词示例的内容作为回复，直接回复：无效图片，无法识别！
**只需要回复图片分析结果，不需要回复任何其他的话术，比如：<如果需要进一步的分析或有其他相关问题，请提供更多的上下文信息>诸如此类的信息

=== 特殊要求规则 ===
**对于识别为水印、头像等无效的、或是图片质量非常差的，请回复我：无效图片，无法识别。
**对于流程图、纯文字的、无法使用上述格式的情况，可以按实际内容回答，但是一定要遵循<强制要求>里的规则。

**请详细分析图片内容
=== 识别图片内容后，按照以下示例内容为格式参考，但不可复用具体内容 ===
左上角：有一个蓝色的向左箭头图标（返回按钮），旁边用白色字体标注"药剂工作台"，字体风格粗犷，带有撕裂边缘效果。
右上角：一个蓝色对话框形状的图标，内部有一个白色房屋图案（主页按钮）。

左侧物品列表区域
背景为浅棕色纸张纹理，带有撕边效果，顶部有一行灰色小字提示："长按图标显示详情"。列表包含三个可制作的物品，每个物品条目由图标、名称、效果描述和数量标记组成：
兽肉干 (10)
图标：左侧显示一块烤熟的肉块（棕色，表面有焦痕）。
名称：黑色加粗字体"兽肉干 (10)"，括号内数字可能表示制作消耗的材料数量。
效果描述：3秒内持续恢复生命720，并在5分钟内增加1点敏捷、精神"
（文字为黑色，字体较小）。
数量标记：右侧红色标签显示"X0"，表示当前已制作数量为0。
浆果干
图标：左侧显示一碗红色浆果（碗为棕色，浆果饱满）。
名称：黑色加粗字体"浆果干"。
效果描述：3秒内持续恢复生命600，并在5分钟内增加3点力量、智力"
数量标记：右侧红色标签显示"X0"。
烤肉串 (5)
图标：左侧显示一串烤肉串（三块肉穿在木签上，表面焦黄）。
名称：黑色加粗字体"烤肉串 (5)"。
效果描述：3秒内持续恢复生命900，并在5分钟内增加3点敏捷、精神"
数量标记：右侧红色标签显示"X4"，表示当前已制作数量为4。

右侧制作区域
核心模型：一个3D篝火装置，由浅棕色木棍搭建的支架和底部的灰色石块围成，中间有燃烧的火焰（橙红色）。
材料显示：篝火正下方有一个小图标，显示一块生肉（红色肉块），下方标注"10/1"，表示制作该物品需要10个生肉材料，当前玩家持有1个。
操作按钮（底部横向排列）：
减号按钮：左侧灰色按钮，带白色"-"符号，用于减少制作数量。
数量显示：中间灰色区域显示数字"1"，表示当前选择制作1份。
加号按钮：右侧黄色按钮，带白色"+"符号，用于增加制作数量。
Max按钮：黄色按钮，标注"Max"，点击后自动设置为最大可制作数量。
合成按钮：最右侧黄色按钮，标注"合成"，下方有倒计时"00:00:02"，表示合成操作需要2秒完成。

其他细节
界面风格：整体采用复古纸张质感，列表区域边缘有撕裂效果，按钮带有手绘风格的边框。
文字信息：所有描述文字均为简体中文，字体清晰，关键数值（如生命恢复值、属性加成）用数字明确标注。
交互提示：列表顶部的"长按图标显示详情"暗示玩家可通过长按查看更详细信息。
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

    def process_pdf_images(self, pdf_path: str, batch_delay: float) -> list[str]:
        """
        处理PDF中的所有图片
        """
        # 提取图片
        images_info = self.extract_images_from_pdf(pdf_path)

        if not images_info:
            return []

        print(f"开始AI分析 {len(images_info)} 张图片...")

        results = {
            "pdf_info": {
                "file_path": pdf_path,
                "total_pages": max([img['page_number'] for img in images_info]) if images_info else 0,
                "total_images": len(images_info),
                "processing_time": None
            },
            "analysis_results": [],
            "summary": {}
        }

        start_time = time.time()

        # 依次处理每张图片
        for i, image_info in enumerate(images_info):
            print(f"处理进度: {i + 1}/{len(images_info)} - {image_info['image_id']}")

            # AI分析图片
            ai_analysis = self.analyze_image_with_ai(image_info)

            # 整合结果
            result_entry = {
                **image_info,
                "ai_analysis": ai_analysis
            }

            results["analysis_results"].append(result_entry)

            # 添加延迟以避免API限制
            if i < len(images_info) - 1:
                time.sleep(batch_delay)

        # # 计算处理时间
        # processing_time = time.time() - start_time
        # results["pdf_info"]["processing_time"] = f"{processing_time:.2f}秒"

        # 生成摘要
        # results["summary"] = self._generate_summary(results)
        print("AI回复内容：",results)

        main_contents = []
        for i in results["analysis_results"]:
            main_content = i["ai_analysis"]["main_content"]
            if "这张图片并不是来自PDF文档的游戏界面截图" in main_content:
                content = main_content[45:]
            elif "无效图片，无法识别" in main_content:
                content = " "
            else:
                content = main_content
            main_contents.append(content)
        return main_contents



if __name__ == "__main__":
    API_KEY = "sk-ce93575f6e8d4a02ba15f8ab38a943a1"
    PDF_PATH = r"攀爬功能文档_20251029112101.pdf"  # 替换为您的PDF路径
    # 初始化分析器
    analyzer = PDFImageAIAnalyzer(api_key=API_KEY, model_name="qwen-vl-plus")

    results = analyzer.process_pdf_images(PDF_PATH, batch_delay=1.0)
