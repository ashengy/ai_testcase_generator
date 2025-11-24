from docx import Document
from docx.oxml.ns import qn
from lxml import etree


def insert_image_position_with_list(
        doc_path,
        image_replacement_list  # 必传：按图片顺序替换的文字列表
):
    """
    提取Word中的文字，按图片出现顺序用列表中的文字依次替换图片

    参数：
        doc_path (str)：Word文件路径
        image_replacement_list (list)：替换图片的文字列表（长度需≥图片数量）
    返回：
        str：按文档顺序排列的文字+替换后的图片文字，保持原有换行格式
    """
    doc = Document(doc_path)
    final_content = []
    namespaces = {
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    }

    # 第一步：先收集文档中所有图片，确定全局顺序
    all_images = []  # 存储所有图片的信息（用于排序）
    for para_idx, paragraph in enumerate(doc.paragraphs):
        for run_idx, run in enumerate(paragraph.runs):
            # 解析当前run中的图片
            run_xml = etree.fromstring(etree.tostring(run.element))
            blip_elements = run_xml.xpath('.//a:blip', namespaces=namespaces)
            for blip in blip_elements:
                r_id = blip.get(qn('r:embed'))
                if r_id and r_id in doc.part.related_parts:
                    # 记录图片的位置信息（段落索引→run索引→r_id）用于排序
                    all_images.append({
                        "para_idx": para_idx,  # 段落索引（按文档顺序）
                        "run_idx": run_idx,  # run索引（段落内顺序）
                        "r_id": r_id  # 图片唯一标识
                    })
    print(f"word共找到{len(all_images)}张图片")
    # 如果是空列表，但是又存在图片，则插入空的字符串进去（为了满足 是否使用AI的判断）
    if not image_replacement_list:
        for i in range(len(all_images)):
            image_replacement_list.append("")

        # 3. 验证替换列表长度是否足够
    if len(image_replacement_list) < len(all_images):
        print(f"替换列表长度不足！PDF中有{len(all_images)}张图片，但列表仅提供{len(image_replacement_list)}个元素")
        fill_num = len(all_images) - len(image_replacement_list)
        for _ in range(fill_num):
            image_replacement_list.append("")
    print(f"替换时，共找到{all_images}张图片")

    # 验证替换列表长度
    if len(image_replacement_list) < len(all_images):
        raise ValueError(
            f"替换列表长度不足！Word中有{len(all_images)}张图片，"
            f"但列表仅提供{len(image_replacement_list)}个元素"
        )

    # 第二步：按文档顺序遍历内容，替换图片
    img_replace_idx = 0  # 替换列表的当前索引

    for para_idx, paragraph in enumerate(doc.paragraphs):
        para_content = ""

        # 处理段落内的所有run
        for run_idx, run in enumerate(paragraph.runs):
            run_text = run.text or ""

            # 检查当前run中是否有图片
            run_xml = etree.fromstring(etree.tostring(run.element))
            blip_elements = run_xml.xpath('.//a:blip', namespaces=namespaces)

            if blip_elements:
                # 如果run中有图片，先添加文本内容，然后替换图片
                if run_text:
                    para_content += run_text

                # 按顺序从列表中取替换文字
                for blip in blip_elements:
                    r_id = blip.get(qn('r:embed'))
                    if r_id and r_id in doc.part.related_parts:
                        replacement_text = image_replacement_list[img_replace_idx]
                        para_content += f"[图片:{replacement_text}]"  # 用括号标记图片位置
                        img_replace_idx += 1
            else:
                # 如果没有图片，直接添加文本内容
                if run_text:
                    para_content += run_text

        # 将处理好的段落内容添加到结果中
        if para_content.strip():  # 只添加非空段落
            final_content.append(para_content)

    # 使用换行符连接各个段落，保持文档原有的段落结构
    content = "\n".join(final_content)
    return content


# 调用示例
if __name__ == "__main__":
    # 替换列表：按Word中图片出现的顺序依次对应
    replacements = [
        "图1：系统架构图",
        "图2：操作流程图",
        "图3：数据对比表",
        "图4：数据对比表",
        # 更多图片请继续添加...
    ]

    content = insert_image_position_with_list(
        doc_path=r"D:\Download\好友系统联系人系统屏蔽系统.docx",
        image_replacement_list=replacements,
    )
    print(content)