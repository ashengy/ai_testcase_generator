# core/worker.py
import json
import re

from PyQt5.QtCore import QThread, pyqtSignal
from openai import OpenAI


class GenerateThread(QThread):
    """异步生成线程"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, prompt, context, job_area, func_type, design_method):
        super().__init__()
        self.prompt = prompt
        self.context = context
        self.job_area = job_area
        self.func_type = func_type
        self.design_method = design_method

    def generate_cases(self, chunk_data):
        # 初始化OpenAI客户端
        client = OpenAI(
            # 如果没有配置环境变量，请用百炼API Key替换：api_key="sk-xxx"
            # api_key='sk-xxx',
            api_key='sk-1c7c69676f2e4d5693643570dccb3960',  #
            base_url='https://api.deepseek.com'
            # base_url="xxxxxx"
        )
        # chunked_context_list = self.chunk_data(self.context, chunk_size=2000)  # 根据需要调整 chunk_size
        all_results = []
        reasoning_content = ""  # 定义完整思考过程
        answer_content = ""  # 定义完整回复
        is_answering = False  # 判断是否结束思考过程并开始回复

        # 创建聊天完成请求
        print("开始执行.........")
        completion = client.chat.completions.create(
            model="deepseek-chat",  # 此处以 deepseek-r1 为例，可按需更换模型名称
            # model="qwen3-235b-a22b-instruct-2507",  # 此处以 deepseek-r1 为例，可按需更换模型名称
            messages=[
                {'role': 'user', 'content': f'所在行业:  {self.job_area}；'
                                            f'文档内容： {chunk_data}； '
                                            f'生成的用例类型： {self.func_type}； '
                                            f'用例设计方法： {self.design_method}； '
                                            f'提示词：{self.prompt}；'}
            ],
            stream=True,
            # 解除以下注释会在最后一个chunk返回Token使用量
            # stream_options={
            #     "include_usage": True
            # }
        )
        # 初始化回复内容
        full_response = ""

        # 遍历流式响应分块
        # for chunk in completion:
        #     if chunk.choices[0].delta.content is not None:
        #         chunk_content = chunk.choices[0].delta.content
        #         full_response += chunk_content
        #         # 可选：实时打印分块内容（如聊天场景）
        #         print(chunk_content, end="", flush=True)
        #
        # print("\n完整回复:", full_response)

        print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")
        for chunk in completion:
            # 如果chunk.choices为空，则打印usage
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
        return answer_content

    def extract_json_objects(self, text):
        """获取回复中的json字符串并进行整合"""
        json_objects = []
        matches = re.findall(r'```json\s*([\s\S]*?)```', text, re.DOTALL)
        for match in matches:
            try:
                json_objects.append(json.loads(match))
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                print(match)
                continue
        return json_objects

    def reformat_test_cases(self, data):
        """Combines a list of test case lists into a single list and renumbers the case IDs."""
        try:
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return data

            if not isinstance(data, list):
                return json.dumps(data, indent=2, ensure_ascii=False) if not isinstance(data, str) else data

            combined_list = []
            for sublist in data:
                if isinstance(sublist, list):
                    combined_list.extend(sublist)
                elif isinstance(sublist, dict):
                    combined_list.append(sublist)

            for i, case in enumerate(combined_list):
                if isinstance(case, dict):
                    if 'case_id' in case.keys():
                        case['case_id'] = f"TC_{i + 1:03}"
                    elif '用例编号' in case.keys():
                        case['用例编号'] = f'TC_{i + 1:03}'

            return json.dumps(combined_list, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"reformat_test_cases处理出错: {e}")
            return json.dumps(data, indent=2, ensure_ascii=False) if not isinstance(data, str) else data

    def run(self):
        try:
            all_result_str = ""
            for n, context_chunk in enumerate(self.context):
                print(f"第{n + 1}段")
                result = self.generate_cases(context_chunk)
                print(f"第{n + 1}次请求，结果为{result}")
                if result is not None and isinstance(result, str):
                    all_result_str += result
                else:
                    print(f"{context_chunk}推理结果异常！")

            print("---------------汇总数据开始打印-------------")
            print(f"多次请求后的汇总数据：{all_result_str}")
            print("--------------汇总数据打印结束--------------")

            if 'json' in all_result_str:
                all_result_str = self.extract_json_objects(all_result_str)
                if isinstance(all_result_str, list) and len(all_result_str) > 0:
                    all_result_str = self.reformat_test_cases(all_result_str)
                print("----------------------------")
                print(all_result_str)
                print("----------------------------")

            self.finished.emit(all_result_str if isinstance(all_result_str, str) else str(all_result_str))
        except Exception as e:
            self.error.emit(str(e))
