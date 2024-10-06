from nonebot import get_plugin_config, on_command
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot.params import Event
from nonebot_plugin_waiter import waiter

import json, time, os

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="contribute",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

contributer = on_command("test", rule = to_me(), priority=5)

# Handle函数
@contributer.handle()
async def handle():
    
    @waiter(waits=["message"], keep_session=True)
    async def get_content(event: Event):
        return event.get_message()
    
    # 获取当前时间戳
    timestamp = int(time.time())
    # 指定文件路径和名称
    directory = "submissions"  # 替换为你的目标目录
    file_name = f"{timestamp}_output.json"
    file_path = os.path.join(directory, file_name)  # 合并目录和文件名

    # 确保目录存在，如果不存在则创建
    os.makedirs(directory, exist_ok=True)

    # 在获取消息的上下文外打开文件，以保持文件打开状态
    with open(file_path, "a", encoding="utf-8") as file:
        async for resp in get_content(timeout=10, retry=200, prompt=""):
            if resp is None:
                await contributer.send("等待超时")
                break

            # 将新消息包装为 JSON 对象并写入文件
            json.dump({"message": str(resp)}, file, ensure_ascii=False)
            file.write("\n")  # 每条消息后换行，方便后续读取

    await contributer.send(f"消息已保存到 {file_path}")  # 可选：告知用户文件已保存
