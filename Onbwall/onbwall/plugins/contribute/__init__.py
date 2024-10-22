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
from jinja2 import Template
from .config import Config
import shutil

__plugin_meta__ = PluginMetadata(
    name="contribute",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

contributer = on_command("test", rule=to_me(), priority=5)

current_milli_time = lambda: int(round(time.time() * 1000))
def create_folder(folder_path):
    """Create a folder if it doesn't already exist."""
    os.makedirs(folder_path, exist_ok=True)

def fetch_sender_info(db_file, tag):
    """Fetch sender information based on the tag from the database."""
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT senderid, receiver, ACgroup FROM preprocess WHERE tag=?", (tag,))
        return cursor.fetchone()

def fetch_rawmsg(db_file, senderid):
    """Fetch rawmsg using the senderid from the database."""
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT rawmsg FROM sender WHERE senderid=?", (senderid,))
        result = cursor.fetchone()
        return result[0] if result else None

def process_json(rawmsg, pwd_path):
    """Process the JSON data to replace face types and filter message types."""
    data = json.loads(rawmsg)
    processed = []
    
    for entry in data:
        if "message" in entry:
            entry["message"] = [
                {
                    "type": "text",
                    "data": {
                        "text": f'<img src="file://{pwd_path}/getmsgserv/LM_work/face/{msg["data"]["id"]}.png"class="cqface">'
                    }
                } if msg["type"] == "face" else msg
                for msg in entry["message"]
            ]
            
            entry["message"] = [msg for msg in entry["message"] if msg["type"] in ["text", "image", "video"]]
            
            if all(msg["type"] == "text" for msg in entry["message"]):
                entry["message"] = [{
                    "type": "text",
                    "data": {
                        "text": "".join(msg["data"]["text"] for msg in entry["message"])
                    }
                }]
            
            if len(entry["message"]) > 0:
                processed.append(entry)
    
    return processed

def check_irregular_types(data):
    """Check if there are irregular types in the processed JSON data."""
    return any(
        msg["type"] not in ["text", "image", "video", "face"]
        for entry in data if "message" in entry
        for msg in entry["message"]
    )

def download_and_replace_images(data, folder, tag, pwd_path):
    """Download images and replace URLs with local file paths in the processed JSON."""
    next_file_index = 1

    for entry in data:
        if "message" in entry:
            for msg in entry["message"]:
                if msg["type"] == "image":
                    url = msg["data"]["url"]
                    local_file = f"{folder}/{tag}-{next_file_index}.png"

                    if not os.path.exists(local_file):
                        response = requests.get(url, stream=True)
                        with open(local_file, 'wb') as out_file:
                            shutil.copyfileobj(response.raw, out_file)

                    msg["data"]["url"] = f"file://{pwd_path}/{local_file}"
                    next_file_index += 1

    return data

def output_final_json(data, has_irregular_types):
    """Output the final JSON with the notregular flag."""
    return json.dumps({
        "notregular": str(has_irregular_types).lower(),
        "messages": [entry for entry in data if "message" in entry]
    }, ensure_ascii=False, indent=4)

def process_lite_json(tag):
    """Main function to process the JSON data."""
    folder = f"cache/picture/{tag}"
    db_file = "submissions/ONBWall.db"
    pwd_path = os.getcwd()

    # Step 1: Create folder
    create_folder(folder)

    # Step 2: Fetch sender information
    sender_info = fetch_sender_info(db_file, tag)
    if not sender_info:
        print(f"No sender information found for tag={tag}. Operation aborted.")
        return
    
    senderid = sender_info[0]

    # Step 3: Fetch rawmsg
    rawmsg = fetch_rawmsg(db_file, senderid)
    if not rawmsg:
        print(f"No raw message found for senderid={senderid}. Operation aborted.")
        return

    # Step 4: Process JSON
    processed_json = process_json(rawmsg, pwd_path)
    
    # Step 5: Check for irregular types
    has_irregular_types = check_irregular_types(processed_json)

    # Step 6: Download images and replace URLs
    processed_json = download_and_replace_images(processed_json, folder, tag, pwd_path)

    # Step 7: Output final JSON
    final_json = output_final_json(processed_json, has_irregular_types)
    return(final_json)

# Example usage
# process_lite_json("example_tag")

async def gotohtml(tag):
    # Connect to the database
    conn = sqlite3.connect('cache/OQQWall.db')
    cursor = conn.cursor()

    # Fetch AfterLM, senderid, and nickname for the given tag
    cursor.execute("SELECT AfterLM, senderid, nickname FROM preprocess WHERE tag = ?", (tag,))
    result = cursor.fetchone()
    
    if not result:
        return "No data found for tag {}".format(tag)
    
    json_data, userid, nickname = result

    # Parse JSON data
    json_data = json.loads(json_data)
    
    # Extract needed values
    needpriv = "False"
    
    # Anonymize if necessary
    userid_show = userid
    if needpriv:
        json_data['sender']['user_id'] = 10000
        json_data['sender']['nickname'] = "匿名"
        nickname = "匿名"
        userid = "10000"
        userid_show = ""

    # Generate message_html using the parsed JSON
    message_html_parts = []
    for message in json_data.get('messages', []):
        for msg_part in message.get('message', []):
            if msg_part['type'] == 'text':
                message_html_parts.append(f"<div>{msg_part['data']['text']}</div>")
            elif msg_part['type'] == 'image':
                message_html_parts.append(f"<img src=\"{msg_part['data']['url']}\" alt=\"Image\">")
            elif msg_part['type'] == 'video':
                video_src = f"file://{msg_part['data'].get('file')}" if 'file' in msg_part['data'] else msg_part['data']['url']
                message_html_parts.append(
                    f"<video controls autoplay muted><source src=\"{video_src}\" type=\"video/mp4\">Your browser does not support the video tag.</video>"
                )
            else:
                continue

    message_html = " ".join(message_html_parts).replace("\n", "<br/>")

    # Prepare HTML content using Jinja2 template
    template_html = """
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OQQWall消息页</title>
        <style>
            @page {
              margin: 0!important;
              margin-top: 0cm!important;
              margin-bottom: 0cm!important;
              margin-left: 0cm!important;
              margin-right: 0cm!important;
              size:4in 8in;
            }
            body {
                font-family: Arial, sans-serif;
                background-color: #f2f2f2;
                margin: 0;
                padding: 5px;
            }
            .container {
                width: 4in;
                margin: 0 auto;
                padding: 20px;
                border-radius: 10px;
                background-color: #f2f2f2;
                box-sizing: border-box;
            }
            .header {
                display: flex;
                align-items: center;
            }
            .header img {
                border-radius: 50%;
                width: 50px;
                height: 50px;
                margin-right: 10px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
            }
            .header-text {
                display: block;
            }
            .header h1 {
                font-size: 24px;
                margin: 0;
            }
            .header h2 {
                font-size: 12px;
                margin: 0;
            }
            .content {
                margin-top: 20px;
            }
            .content div {
                display: block;
                background-color: #ffffff;
                border-radius: 10px;
                padding: 7px;
                margin-bottom: 10px;
                word-break: break-word;
                max-width: fit-content;
                line-height: 1.5;
            }
            .content img, .content video {
                display: block;
                border-radius: 10px;
                padding: 0px;
                margin-top: 10px;
                margin-bottom: 10px;
                max-width: 50%;
                max-height: 300px; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="http://q.qlogo.cn/headimg_dl?dst_uin={{ userid }}&spec=640&img_type=jpg" alt="Profile Image">
                <div class="header-text">
                    <h1>{{ nickname }}</h1>
                    <h2>{{ userid_show }}</h2>
                </div>
            </div>
            <div class="content">
                {{ message_html | safe }}
            </div>
        </div>

        <script>
            window.onload = function() {
                const container = document.querySelector('.container');
                const contentHeight = container.scrollHeight;
                const pageHeight4in = 364; // 4 inches in pixels (96px per inch)

                let pageSize = '';

                if (contentHeight <= pageHeight4in) {
                    pageSize = '4in 4in'; // Use 4in x 4in if content fits
                } else if (contentHeight >= 2304){
                    pageSize = '4in 24in'
                } else {
                    const containerHeightInInches = (contentHeight / 96 + 0.1);
                    pageSize = `4in ${containerHeightInInches}in`; // Set height to container's height
                }

                // Dynamically apply the @page size
                const style = document.createElement('style');
                style.innerHTML = `
                    @page {
                        size: ${pageSize};
                        margin: 0 !important;
                    }
                `;
                document.head.appendChild(style);
            };
        </script>
    </body>
    </html>
    """

    # Render HTML with Jinja2 template
    template = Template(template_html)
    html_content = template.render(userid=userid, nickname=nickname, userid_show=userid_show, message_html=message_html)
    
    return html_content

async def download_image(url, output_path):

db_path = 'submissions/ONBWall.db'
RAWPOST_DIR = './submissions/rawpost'
ALLPOST_DIR = './submissions/all'
COMMU_DIR = './submissions/all/'
# 检查数据库文件是否存在
if not os.path.exists(db_path):
    # 连接到 SQLite 数据库（如果数据库不存在，将会自动创建）
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建 sender 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sender (
            senderid TEXT,
            receiver TEXT,
            ACgroup TEXT,
            rawmsg TEXT,
            modtime TEXT,
            processtime TEXT
        )
    ''')

    # 创建 preprocess 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preprocess (
            tag INTEGER,
            senderid TEXT,
            nickname TEXT,
            receiver TEXT,
            ACgroup TEXT,
            AfterLM TEXT,
            comment TEXT,
            numnfinal INTEGER
        )
    ''')

    # 提交更改并关闭连接
    conn.commit()
    conn.close()

    print(f"Database and tables created at {db_path}")
else:
    print(f"Database already exists at {db_path}")

@contributer.handle()
async def handle():
    @waiter(waits=["message"], keep_session=True)
    async def get_content(event: Event):
        return event.get_message(), event.get_session_id()  # 返回消息和 sessionID

    async for resp in get_content(timeout=30, retry=200, prompt=""):
        if resp is None:
            await contributer.send("等待超时")
            break
        print("resp")
        print(resp)
        message_segments, session_id = resp  # 解包消息和 sessionID

        # 遍历消息中的所有 MessageSegment
        # Inside the handle function, traversing the message_segments
        for segment in message_segments:
            # Checking each segment type and data
            message_type = segment.type
            message_data = segment.data

            # Extracting and formatting into a list for JSON compatibility
            import json
            result = [{"type": message_type, "data": message_data}]
            result_json = json.dumps(result)  # 将其转为 JSON 字符串，保留双引号
            print(result)  # Printing the parsed result
            await contributer.send(f"Parsed message segment: {result}")
        # Continue with creating the simplified_data dictionary as before
        simplified_data = {
            "message_id": current_milli_time(),
            "message": result,
            "time": int(time.time())
        }
        await contributer.send(f"Simplified message: {simplified_data}")
        print(f"Simplified message: {simplified_data}")

        user_id = session_id
        nickname = user_id
        print(f"userid:{user_id}")
        self_id = "10000"
        #ACgroup = self_id_to_acgroup.get(self_id, 'Unknown')
        ACgroup = "notusenow"
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if a record already exists for this sender and receiver
            cursor.execute('SELECT rawmsg FROM sender WHERE senderid=? AND receiver=?', (user_id, self_id))
            row = cursor.fetchone()
            if row:
                # If exists, load the existing rawmsg and append the new message
                rawmsg_json = row[0]
                try:
                    message_list = json.loads(rawmsg_json)
                    if not isinstance(message_list, list):
                        message_list = []
                except json.JSONDecodeError:
                    message_list = []

                message_list.append(simplified_data)
                # Sort messages by time
                message_list = sorted(message_list, key=lambda x: x.get('time', 0))

                updated_rawmsg = json.dumps(message_list, ensure_ascii=False)
                cursor.execute('''
                    UPDATE sender 
                    SET rawmsg=?, modtime=CURRENT_TIMESTAMP 
                    WHERE senderid=? AND receiver=?
                ''', (updated_rawmsg, user_id, self_id))
            else:
                # If not exists, insert a new record with the message
                message_list = [simplified_data]
                rawmsg_json = json.dumps(message_list, ensure_ascii=False)
                print("startwritingtodb")
                cursor.execute('''
                    INSERT INTO sender (senderid, receiver, ACgroup, rawmsg, modtime) 
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, self_id, ACgroup, rawmsg_json))

                # Check the max tag from the preprocess table
                cursor.execute('SELECT MAX(tag) FROM preprocess')
                max_tag = cursor.fetchone()[0] or 0
                new_tag = max_tag + 1

                # Insert into preprocess table
                cursor.execute('''
                    INSERT INTO preprocess (tag, senderid, nickname, receiver, ACgroup) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (new_tag, user_id, nickname, self_id, ACgroup))

                # Commit changes
                conn.commit()
                print("endwritingtodb")
                # Call the preprocess.sh script with the new tag
                #preprocess_script_path = './getmsgserv/preprocess.sh'
                #try:
                #    subprocess.run([preprocess_script_path, str(new_tag)], check=True)
                #except subprocess.CalledProcessError as e:
                #    print(f"Preprocess script execution failed: {e}")

            conn.commit()
            conn.close()
        except Exception as e:
            print(f'Error recording private message to database: {e}')

    await contributer.send("消息处理完毕")