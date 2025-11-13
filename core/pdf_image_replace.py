import pdfplumber
from core.pdf_image_ai_analyzer import PDFImageAIAnalyzer

def extract_pdf_text_with_image_list(
        pdf_path,
        image_replacement_list  # 必传：按图片顺序替换的文字列表（如["图1", "图2",...]）
):
    """
    提取PDF中的文字，按图片出现顺序用列表中的文字依次替换图片

    参数：
        pdf_path (str)：PDF文件路径
        image_replacement_list (list)：替换图片的文字列表（长度需≥图片数量）

    返回：
        str：按PDF顺序排列的文字+替换后的图片文字
    """
    full_content = []
    with pdfplumber.open(pdf_path) as pdf:
        # 1. 先收集所有页的图片，确定全局顺序（按页码→页面内位置排序）
        all_images = []  # 存储所有图片信息：(页码, 图片坐标, 原始索引)
        for page_num, page in enumerate(pdf.pages, 1):
            for img in page.images:
                # 记录图片的页码、y0（垂直位置）、x0（水平位置），用于全局排序
                all_images.append({
                    "page_num": page_num,
                    "y0": img["y0"],
                    "x0": img["x0"],
                    "img_obj": img  # 原始图片对象
                })

        # 2. 对所有图片按出现顺序排序（先按页码，再按页面内y0/x0）
        # 排序规则：页码升序 → y0降序（上到下）→ x0升序（左到右）
        all_images_sorted = sorted(
            all_images,
            key=lambda x: (x["page_num"], -x["y0"], x["x0"])
        )

        # 如果是空列表，但是又存在图片，则插入空的字符串进去（为了满足 是否使用AI的判断）
        if not image_replacement_list:
            for i in range(len(all_images_sorted)):
                image_replacement_list.append("")

        # 3. 验证替换列表长度是否足够
        if len(image_replacement_list) < len(all_images_sorted):
            fill_num = len(all_images_sorted) - len(image_replacement_list)
            for _ in range(fill_num):
                image_replacement_list.append("")
            print(f"替换列表长度不足！PDF中有{len(all_images_sorted)}张图片，但列表仅提供{len(image_replacement_list)}个元素")
        print("打印image_replacement_list",image_replacement_list)
        # 4. 遍历每一页，替换图片
        for page_num, page in enumerate(pdf.pages, 1):
            chars = page.chars
            images = page.images

            # 4.1 处理当前页文字行（带坐标）
            text_lines = []
            if chars:
                sorted_chars = sorted(chars, key=lambda c: (c["y0"], c["x0"]))
                current_line_chars = []
                current_y0 = None

                for char in sorted_chars:
                    if current_y0 is None or abs(char["y0"] - current_y0) > 1:
                        if current_line_chars:
                            line_text = "".join([c["text"] for c in current_line_chars])
                            text_lines.append({
                                "type": "text",
                                "content": line_text,
                                "y0": current_line_chars[0]["y0"],
                                "x0": current_line_chars[0]["x0"]
                            })
                        current_line_chars = [char]
                        current_y0 = char["y0"]
                    else:
                        current_line_chars.append(char)

                if current_line_chars:
                    line_text = "".join([c["text"] for c in current_line_chars])
                    text_lines.append({
                        "type": "text",
                        "content": line_text,
                        "y0": current_line_chars[0]["y0"],
                        "x0": current_line_chars[0]["x0"]
                    })

            # 4.2 处理当前页图片：按全局顺序匹配替换文字
            page_image_marks = []
            if images:
                # 筛选当前页的图片，并按全局排序后的顺序匹配替换文字
                for img in images:
                    # 找到当前图片在全局排序中的索引
                    img_index = next(
                        i for i, global_img in enumerate(all_images_sorted)
                        if global_img["img_obj"] == img and global_img["page_num"] == page_num
                    )
                    # 获取对应的替换文字
                    replacement_text = image_replacement_list[img_index]
                    page_image_marks.append({
                        "type": "image",
                        "content": replacement_text,
                        "y0": img["y0"],
                        "x0": img["x0"]
                    })

            # 4.3 合并当前页的文字和图片替换内容，按坐标排序
            all_elements = text_lines + page_image_marks
            all_elements.sort(key=lambda elem: (-elem["y0"], elem["x0"]))
            # 4.4 拼接当前页内容
            page_content = " ".join([elem["content"] for elem in all_elements])
            full_content.append(f"{page_content}")

    # 5. 输出结果
    content = " ".join(full_content)
    return content


# 调用示例
if __name__ == "__main__":
    # 替换列表：按PDF中图片出现的顺序依次对应
    # 替换列表：按PDF中图片出现的顺序依次对应
    API_KEY = "sk-ce93575f6e8d4a02ba15f8ab38a943a1"
    PDF_PATH = r"D:\ai\神兵.pdf"  # 替换为您的PDF路径
    # 初始化分析器
    # analyzer = PDFImageAIAnalyzer(api_key=API_KEY, model_name="qwen-vl-plus")
    # replacements = analyzer.process_pdf_images(PDF_PATH, batch_delay=1.0)

    pdf_content = extract_pdf_text_with_image_list(
        pdf_path=PDF_PATH,  # 替换为你的PDF路径
        image_replacement_list=[]
    )
    print("pdf_content是\n",pdf_content)