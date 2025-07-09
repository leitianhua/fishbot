#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
闲鱼助手 - 主程序入口
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from loguru import logger

# 导入自定义模块
from config import load_config, CONFIG_PATH, LOGS_DIR, USER_DATA_DIR, EXECUTABLE_PATH
from database import init_database
from chatbot import ChatBot

# 检查依赖
try:
    from playwright.async_api import async_playwright
except ImportError:
    logger.error("未安装playwright，请使用pip install playwright安装")
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    logger.error("未安装aiohttp，请使用pip install aiohttp安装")
    sys.exit(1)

# 加载配置
config = load_config()

async def main():
    """主函数 - 启动闲鱼助手"""
    logger.info("闲鱼助手启动中...")
    
    # 初始化数据库
    await init_database()
    
    async with async_playwright() as p:
        # 启动浏览器
        logger.info(f"启动浏览器，用户数据目录: {USER_DATA_DIR}")
        browser = await p.chromium.launch_persistent_context(
            headless=False,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled'],
            user_data_dir=USER_DATA_DIR,
            executable_path=EXECUTABLE_PATH,
        )
        page = await browser.new_page()

        # 创建聊天机器人实例
        chat_bot = ChatBot(page)
        
        # 异步加载插件
        try:
            await chat_bot.load_plugins()
            logger.info(f"插件加载成功，共 {len(chat_bot.plugins)} 个插件")
        except Exception as e:
            logger.error(f"加载插件失败: {e}")

        # 监听请求
        page.on("request", chat_bot.handle_request)
        
        # 打开闲鱼
        logger.info("正在打开闲鱼网站...")
        await page.goto("https://www.goofish.com/im", wait_until="networkidle")
        logger.info("闲鱼网站已打开")

        # 主循环
        last_refresh_time = time.time()
        refresh_interval = config.get("system", {}).get("refresh_interval", 12) * 3600  # 默认12小时，单位：秒
        logger.info(f"页面刷新间隔设置为 {refresh_interval//3600} 小时")

        logger.info("闲鱼助手已成功启动，开始监控消息...")
        while True:
            try:
                current_time = time.time()
                if current_time - last_refresh_time >= refresh_interval:
                    logger.info(f'已运行{refresh_interval//3600}小时，准备刷新页面...')
                    # 模拟按下 F5 键
                    await page.evaluate("location.reload()")
                    # 等待页面加载完成
                    await page.wait_for_load_state('networkidle')
                    # 更新刷新时间
                    last_refresh_time = time.time()
                    logger.info('页面刷新完成')
                    continue

                logger.debug('开始新的检查循环')
                if chat_bot.is_replying or chat_bot.is_processing_message:
                    logger.debug('正在处理或回复消息，等待5秒后继续循环')
                    await asyncio.sleep(5)
                    continue

                try:
                    # 检查是否有打开的对话框
                    conversation_open = await page.query_selector('#message-list-scrollable')
                    if conversation_open:
                        logger.debug('检测到打开的对话框')
                        await chat_bot.check_and_reply_new_messages()

                        if not chat_bot.is_replying and not chat_bot.is_processing_message:
                            logger.debug('当前对话没有新消息，检查其他对话的红点')
                            await chat_bot.check_new_message_badge()
                    else:
                        logger.debug('当前没有打开的对话框，检查新消息红点')
                        await chat_bot.check_new_message_badge()
                except Exception as e:
                    logger.error(f"处理消息时发生错误: {e}")
                    await asyncio.sleep(3)  # 出错后等待一小段时间
                    continue

            except Exception as e:
                logger.error(f"主循环发生错误: {e}")
                await asyncio.sleep(5)  # 发生错误时等待较长时间
                continue

            logger.debug('等待3秒后继续下一次循环')
            await asyncio.sleep(3)


if __name__ == '__main__':
    asyncio.run(main())