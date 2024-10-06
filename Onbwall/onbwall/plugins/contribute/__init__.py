from nonebot import get_plugin_config, on_command
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot.params import Event
from nonebot_plugin_waiter import waiter

import json
import time
import os

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