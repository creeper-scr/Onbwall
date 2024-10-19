from nonebot import get_plugin_config, on_command
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Event
from nonebot.rule import to_me
from datetime import datetime, timedelta
import sqlite3
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="daily_sign",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

sign = on_command("签到", priority=5, rule=to_me(), block=True)

@sign.handle()
async def handle(event: Event):
    uid = event.get_user_id()
    response_message = await write_toDB(uid)
    if response_message:
        await sign.finish(response_message)

async def write_toDB(uid):
    # 创建连接
    conn = sqlite3.connect(r'sign.db')
    cursor = conn.cursor()

    # 创建包含 uid、score 和 last_sign_date 字段的表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scores (
        uid INTEGER PRIMARY KEY,
        score INTEGER,
        last_sign_date TEXT
    )
    ''')

    # 获取今天的日期
    today = datetime.now().date().isoformat()

    # 查找是否存在该 uid
    cursor.execute("SELECT score, last_sign_date FROM scores WHERE uid = ?", (uid,))
    row = cursor.fetchone()

    if row:
        current_score = row[0]
        last_sign_date = row[1]

        # 如果今天已经签到
        if last_sign_date == today:
            return "你今天已经签到过了哦！"

        # 检查上次签到是否为昨天
        previous_date = datetime.fromisoformat(last_sign_date).date()
        if previous_date == datetime.now().date() - timedelta(days=1):
            # 连续签到，增加 15 分
            new_score = current_score + 15
            points_today = 15
        else:
            # 非连续签到，增加 10 分
            new_score = current_score + 10
            points_today = 10
        
        # 更新数据库
        cursor.execute("UPDATE scores SET score = ?, last_sign_date = ? WHERE uid = ?", (new_score, today, uid))
        print(f"Updated user {uid} score to {new_score}.")
    else:
        # 如果不存在，插入新记录，初始 score 为 10，并设置今天为最后签到日期
        new_score = 10
        points_today = 10
        cursor.execute("INSERT INTO scores (uid, score, last_sign_date) VALUES (?, ?, ?)", (uid, new_score, today))
        print(f"Inserted user {uid} with initial score of 10.")

    # 提交更改
    conn.commit()

    # 关闭连接
    conn.close()

    return f"签到成功，积分+{points_today}，当前总积分为{new_score}"  # 返回今日加分和当前总积分