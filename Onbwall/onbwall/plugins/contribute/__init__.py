from nonebot import get_plugin_config, on_command
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot.params import Event
from nonebot_plugin_waiter import waiter

import json
import os
import time
import re
import subprocess
import shutil
import sqlite3
import requests

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="contribute",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

contributer = on_command("test", rule=to_me(), priority=5)


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
        print("生成 HTML 失败：写入文件错误。")
    # 可选：将 HTML 文件路径返回或发送给用户
    return f"HTML 文件已生成：{html_file_path}"
    print(f"HTML 文件已生成：{html_file_path}")

async def gotojpg(file_path):
    """
    使用 Chrome 打印 HTML 到 PDF 并将 PDF 转换为 JPG，然后下载 JSON 中的所有图片到同一个文件夹。
    参数:
        file_name (str): JSON 文件的文件名，用于定位相关文件
    """
    # 文件夹和文件名的设置
    input_name = os.path.splitext(os.path.basename(file_path))[0]
    html_file_path = f"{file_path.replace('_raw.json', '.html')}"
    pdf_output_path = f"{file_path.replace('_raw.json', '.pdf')}"
    jpg_folder = f"{file_path.replace('_raw.json', '-img')}"
    json_file_path = file_path
    # 确保必要的目录存在
    os.makedirs(os.path.dirname(pdf_output_path), exist_ok=True)
    os.makedirs(jpg_folder, exist_ok=True)

    # 使用 Chrome 打印 HTML 到 PDF
    chrome_command = [
        "google-chrome-stable",
        "--headless",
        f"--print-to-pdf={pdf_output_path}",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        "--virtual-time-budget=2000",
        "--pdf-page-orientation=portrait",
        "--no-margins",
        "--enable-background-graphics",
        "--print-background=true",
        f"file://{os.path.abspath(html_file_path)}"
    ]

    # 执行 Chrome 打印命令
    subprocess.run(chrome_command, check=True)

    # 使用 ImageMagick 将 PDF 转换为 JPG
    convert_command = [
        "identify",
        "-format", "%n\n",
        pdf_output_path
    ]

    # 获取 PDF 的页数
    pages = subprocess.check_output(convert_command).decode("utf-8").strip().split("\n")[0]

    # 转换每一页 PDF 为 JPG
    for i in range(int(pages)):
        formatted_index = f"{i:02d}"
        convert_page_command = [
            "convert",
            "-density", "360",
            "-quality", "90",
            f"{pdf_output_path}[{i}]",
            f"{jpg_folder}/{input_name}-{formatted_index}.jpeg"
        ]
        subprocess.run(convert_page_command, check=True)

    # 下载 JSON 中的所有图片
    next_file_index = len(os.listdir(jpg_folder))
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for item in data:
            if "message" in item:
                msg = item["message"]
                # 查找所有 CQ:image 码
                cq_images = re.findall(r'\[CQ:image,([^\]]+)\]', msg)
                for cq_data in cq_images:
                    data_dict = {}
                    # 解析 CQ 码中的数据
                    for kv in cq_data.split(','):
                        if '=' in kv:
                            k, v = kv.split('=', 1)
                            data_dict[k] = v
                    img_url = data_dict.get("url", "")
                    if img_url:
                        formatted_index = f"{next_file_index:02d}"
                        image_output_path = f"{jpg_folder}/{input_name}-{formatted_index}.jpeg"
                        download_image(img_url, image_output_path)
                        next_file_index += 1

    # 重命名文件，去掉后缀名
    for file in os.listdir(jpg_folder):
        file_path = os.path.join(jpg_folder, file)
        if os.path.isfile(file_path):
            base_name = os.path.splitext(file)[0]
            os.rename(file_path, os.path.join(jpg_folder, base_name))


def download_image(url, output_path):
    """
    下载图片并保存到指定路径。
    参数:
        url (str): 图片的 URL 地址
        output_path (str): 保存图片的文件路径
    """
    #response = requests.get(url, stream=True)
    #if response.status_code == 200:
        #with open(output_path, "wb") as f:
         #   shutil.copyfileobj(response.raw, f)
    #else:
        #print(f"下载图片失败: {url}")
    print("download"f"{url}""to" f"{output_path}")

@contributer.handle()
async def handle():
    
    @waiter(waits=["message"], keep_session=True)
    async def get_content(event: Event):
        return event.get_message(), event.get_session_id()  # 返回消息和 sessionID
    
    timestamp = int(time.time())
    directory = "submissions"  # 替换为你的目标目录
    file_name = f"{timestamp}_raw.json"
    file_path = os.path.join(directory, file_name)  # 合并目录和文件名

    # 确保目录存在，如果不存在则创建
    os.makedirs(directory, exist_ok=True)

    # 在获取消息的上下文外打开文件，以保持文件打开状态
    with open(file_path, "a", encoding="utf-8") as file:
        file.write("[\n")

        first_message = True  # 用于跟踪是否是第一条消息
        async for resp in get_content(timeout=10, retry=200, prompt=""):
            if resp is None:
                await contributer.send("等待超时")
                break
            
            message, sessionID = resp  # 解包消息和 sessionID

            # 如果不是第一条消息，前面添加逗号
            if not first_message:
                file.write(",\n")
            else:
                first_message = False

            # 将新消息包装为 JSON 对象并写入文件
            json.dump({"message": str(message)}, file, ensure_ascii=False)

        # 写入 sessionID，确保前面有逗号
        if sessionID:  # 检查 sessionID 是否存在
            if not first_message:  # 如果已经写入过消息
                file.write(",\n")
            json.dump({"sessionID": str(sessionID)}, file, ensure_ascii=False)

        file.write("\n]")  # 写入结尾的右方括号

    await contributer.send(f"消息已保存到 {file_path}")  # 可选：告知用户文件已保存
    await gotohtml(file_path)
    await gotojpg(file_path)