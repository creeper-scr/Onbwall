from nonebot import get_plugin_config, on_command
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot.params import Event
from nonebot_plugin_waiter import waiter
from nonebot.adapters.onebot.v11 import PrivateMessageEvent

import json
import time
import os
import re
import pdfkit
import fitz

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="contribute",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

contributer = on_command("test", rule=to_me(), priority=5)

@contributer.handle()
async def handle():
    
    @waiter(waits=["message"], keep_session=True)
    async def get_content(event: PrivateMessageEvent):
        return event.get_message(), event.get_session_id()  # 返回消息和 sessionID
    
    timestamp = int(time.time())
    directory = "submissions"  # 替换为你的目标目录
    file_name = f"{timestamp}_raw.json"
    file_path = os.path.join(directory, file_name)  # 合并目录和文件名

    # 确保目录存在，如果不存在则创建
    os.makedirs(directory, exist_ok=True)

    messages_list = []  # 用于存储消息和 sessionID 的列表

    # 在获取消息的上下文外打开文件，以保持文件打开状态
    try:
        async for resp in get_content(timeout=10, retry=200, prompt=""):
            if resp is None:
                await contributer.send("等待超时")
                break
            
            message, sessionID = resp  # 解包消息和 sessionID

            # 将新消息和 sessionID 添加到字典中
            messages_list.append({"message": str(message), "sessionID": str(sessionID)})

    except Exception as e:
        await contributer.send(f"发生错误: {str(e)}")  # 错误处理
        return
    if not messages_list:
        os.remove(file_path)  # 删除空的 JSON 文件
        await contributer.send("未收到稿件")
    else:
        # 写入 JSON 文件
        with open(file_path, "w", encoding="utf-8") as file:  # 以写入模式打开文件
            json.dump(messages_list, file, ensure_ascii=False, indent=4)  # 转换为 JSON 格式并写入文件

        await contributer.send(f"消息已保存到 {file_path}")  # 可选：告知用户文件已保存
        html_path = await gotohtml(file_path)
        await gotojpg(html_path, timestamp)

async def gotohtml(file_path):
    html_file_path = f"{file_path.replace('_raw.json', '.html')}"
    if not os.path.exists(file_path):
        return "生成 HTML 失败：文件不存在。"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return "生成 HTML 失败：JSON 解析错误。"
        print("生成 HTML 失败：JSON 解析错误。")
    
    messages = []
    sessionID = ""
    
    for item in data:
        if "message" in item:
            messages.append(item["message"])
        if "sessionID" in item:
            sessionID = item["sessionID"]
    
    if not sessionID:
        return "生成 HTML 失败：未找到 sessionID。"
        print("生成 HTML 失败：未找到 sessionID。")
    # 处理消息，解析 CQ 码
    processed_messages = []
    for msg in messages:
        # 处理 CQ:image
        img_match = re.match(r'\[CQ:image,file=([^,]+),[^]]*\]', msg)
        if img_match:
            img_url = img_match.group(1)
            # 尝试提取 URL，如果有 url 参数
            url_match = re.search(r'url=([^,]+)', msg)
            if url_match:
                img_url = url_match.group(1)
            img_html = f'<img src="{img_url}" alt="Image">'
            processed_messages.append(img_html)
            continue
        
        # 处理 CQ:video
        video_match = re.match(r'\[CQ:video,file=([^,]+),[^]]*\]', msg)
        if video_match:
            video_url = video_match.group(1)
            # 尝试提取 URL，如果有 url 参数
            url_match = re.search(r'url=([^,]+)', msg)
            if url_match:
                video_url = url_match.group(1)
            video_html = f'<video controls autoplay muted><source src="{video_url}" type="video/mp4">您的浏览器不支持视频标签。</video>'
            processed_messages.append(video_html)
            continue
        
        # 处理纯文本消息，转义 HTML 特殊字符
        escaped_msg = (msg.replace("&", "&amp;")
                         .replace("<", "&lt;")
                         .replace(">", "&gt;")
                         .replace('"', "&quot;")
                         .replace("'", "&#039;"))
        # 换行符转为 <br/>
        escaped_msg = escaped_msg.replace("\n", "<br/>")
        processed_messages.append(f"<div>{escaped_msg}</div>")
    
    # 生成 HTML 内容
    html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Session {sessionID}</title>
    <style>
        @page {{
          margin: 0 !important;
          size:4in 8in;
        }}
        body {{
            font-family: Arial, sans-serif;
            background-color: #f2f2f2;
            margin: 0;
            padding: 5px;
        }}
        .container {{
            width: 4in;
            margin: 0 auto;
            padding: 20px;
            border-radius: 10px;
            background-color: #f2f2f2;
            box-sizing: border-box;
        }}
        .header {{
            display: flex;
            align-items: center;
        }}
        .header img {{
            border-radius: 50%;
            width: 50px;
            height: 50px;
            margin-right: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
        }}
        .header-text {{
            display: block;
        }}
        .header h1 {{
            font-size: 24px;
            margin: 0;
        }}
        .header h2 {{
            font-size: 12px;
            margin: 0;
        }}
        .content {{
            margin-top: 20px;
        }}
        .content div{{
            display: block;
            background-color: #ffffff;
            border-radius: 10px;
            padding: 7px;
            margin-bottom: 10px;
            word-break: break-word;
            max-width: fit-content;
            line-height: 1.5;
        }}
        .content img, .content video {{
            display: block;
            border-radius: 10px;
            padding: 0px;
            margin-top: 10px;
            margin-bottom: 10px;
            max-width: 50%;
            max-height: 300px; 
        }}
        .content video {{
            background-color: transparent;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="http://q.qlogo.cn/headimg_dl?dst_uin=10000&spec=640&img_type=jpg" alt="Profile Image">
            <div class="header-text">
                <h1>{sessionID}</h1>
                <h2></h2>
            </div>
        </div>
        <div class="content">
            {''.join(processed_messages)}
        </div>
    </div>

    <script>
        window.onload = function() {{
            const container = document.querySelector('.container');
            const contentHeight = container.scrollHeight;
            const pageHeight4in = 364; // 4 inches in pixels (96px per inch)
        
            let pageSize = '';
        
            if (contentHeight <= pageHeight4in) {{
                pageSize = '4in 4in'; // 内容适合时使用 4in x 4in
            }} else if (contentHeight >= 2304){{
                pageSize = '4in 24in';
            }} else {{
                const containerHeightInInches = (contentHeight / 96 + 0.1);
                pageSize = `4in ${{containerHeightInInches}}in`; // 根据内容高度设置页面高度
            }}
        
            // 动态应用 @page 大小
            const style = document.createElement('style');
            style.innerHTML = `
                @page {{
                    size: ${{pageSize}};
                    margin: 0 !important;
                }}
            `;
            document.head.appendChild(style);
        }};
    </script>
</body>
</html>
"""
    
    # 定义 HTML 输出目录
    output_dir = os.path.join("ONBwall", "html")
    os.makedirs(output_dir, exist_ok=True)
    
    # 使用时间戳作为 HTML 文件名的一部分，确保唯一性
    
    try:
        with open(html_file_path, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)
    except Exception as e:
        return "生成 HTML 失败：写入文件错误。"
    # 可选：将 HTML 文件路径返回或发送给用户
    return html_file_path


async def gotojpg(html_file_path, file_name):
    if not os.path.exists(html_file_path) or not html_file_path.endswith('.html'):
        raise ValueError("输入路径不存在或不是一个有效的 HTML 文件")
        
    # 创建以 file_name 命名的文件夹
    output_folder = os.path.join('submissions', str(file_name))
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)  # 如果文件夹不存在，则创建

    path_to_wkhtmltopdf = r"C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe"
    config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
    
    pdf_file_path = f"{os.path.splitext(html_file_path)[0]}.pdf"

    # 将 HTML 文件转换为 PDF
    pdfkit.from_file(html_file_path, pdf_file_path, configuration=config)
    print(f"已将 {html_file_path} 转换为 {pdf_file_path}")

    # 将 PDF 文件转换为 JPEG
    pdf_document = fitz.open(pdf_file_path)  # 打开 PDF 文件
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)  # 加载页面
        pix = page.get_pixmap()  # 获取页面的位图
        jpg_page_path = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(html_file_path))[0]}_page_{page_num + 1}.jpg")
        pix.save(jpg_page_path)  # 保存为 JPEG 文件
        print(f"已将 {pdf_file_path} 的第 {page_num + 1} 页转换为 {jpg_page_path}")

    # 删除临时 PDF 文件
    pdf_document.close()  # 关闭 PDF 文档
    os.remove(pdf_file_path)
    print(f"已删除临时 PDF 文件: {pdf_file_path}")


