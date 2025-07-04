import os
from playwright.async_api import async_playwright
import logging
import requests
from urllib.parse import unquote
import re
import sqlite3
from collections import deque
import time
import aiohttp
import asyncio

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(asctime)s - %(message)s')
log = logging.getLogger()

# 钉钉机器人webhook
dingding_webhook = "https://oapi.dingtalk.com/robot/send?access_token=5c22c63ba1a742a9a09eee52b551a02c6059230a777835e89e237b87306c63b4"
dingding_keyword = "【闲鱼助手】"
# 开启钉钉消息监控闲鱼消息通知
open_dingding = True

async def send_dingtalk_message(message, pre=None):
    """
    异步发送钉钉机器人文本消息
    :param message: 要发送的文本内容
    :param pre: 前缀
    """
    # 构造请求数据
    headers = {"Content-Type": "application/json;charset=utf-8"}
    data = {
        "msgtype": "text",
        "text": {
            "content": f'{dingding_keyword} {pre}\n{message}' if pre else f'{dingding_keyword}\n{message}'
        }
    }
    # 发送 POST 请求
    async with aiohttp.ClientSession() as session:
        async with session.post(dingding_webhook, headers=headers, json=data) as response:
            response_data = await response.json()
            log.info(f"钉钉机器人: {response_data}")  # 打印发送结果，但不阻塞后续逻辑

if __name__ == '__main__':
    asyncio.run(send_dingtalk_message("测试消息"))