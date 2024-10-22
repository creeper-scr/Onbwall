from nonebot import get_plugin_config, on_command
from nonebot import require
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

require("imgrander")
import onbwall.plugins.imgrander as imgrander

__plugin_meta__ = PluginMetadata(
    name="contribute",
    description="这是Onbwall的信息接收与初步处理插件",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)
current_milli_time = lambda: int(round(time.time() * 1000))
contributer = on_command("test", rule=to_me(), priority=5)
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

    async for resp in get_content(timeout=15, retry=200, prompt=""):
        if resp is None:
            await contributer.send("等待超时")
            break
        print("resp")
        print(resp)
        message_segments, session_id = resp  # 解包消息和 sessionID

        # 遍历消息中的所有 MessageSegment
        # Inside the handle function, traversing the message_segments
        # 在 for 循环外创建 message 列表
        all_segments = []

        for segment in message_segments:
            # 检查每个 segment 类型和数据
            message_type = segment.type
            message_data = segment.data

            # 将提取的 segment 格式化并添加到 all_segments 列表中
            result = {"type": message_type, "data": message_data}
            all_segments.append(result)

        # 构建 simplified_data 字典，将所有 segments 添加到 message 中
        simplified_data = {
            "message_id": current_milli_time(),
            "message": all_segments,
            "time": int(time.time())
        }

        # 输出解析后的结果
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
                isfirst = "false"
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
                isfirst = "true"
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
        except Exception as e:
            print(f'Error recording private message to database: {e}')
        if isfirst:
            try:
                simplified_json = imgrander.process_lite_json(new_tag)

                # Step 2: Update `AfterLM` field with the processed JSON
                cursor.execute('UPDATE preprocess SET AfterLM=? WHERE tag=?', (simplified_json, new_tag))
                conn.commit()
                print(f"Processed JSON stored for tag {new_tag}.")
            except Exception as e:
                        print(f"Error processing JSON for tag {new_tag}: {e}")
        conn.close()
    await contributer.send("消息处理完毕")