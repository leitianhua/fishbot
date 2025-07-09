#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
闲鱼助手 - 聊天机器人核心模块
"""

import os
import re
import json
import asyncio
import importlib.util
from collections import deque
from urllib.parse import unquote
from loguru import logger

from config import config, PLUGINS_DIR
from database import get_shop_info, save_shop_info

class ChatBot:
    """闲鱼聊天机器人类"""
    
    def __init__(self, page):
        """初始化聊天机器人
        
        Args:
            page: Playwright页面对象
        """
        self.page = page
        self.is_replying = False
        self.is_processing_message = False
        self.auto_ship_required = False
        self.auto_notice_required = False
        self.is_get_shop = False
        self.current_conversation_id = None
        
        # 当前会话信息
        self.cur_user_name = None
        self.cur_item_id = None
        self.cur_shop_name = None
        self.cur_shop_price = None
        self.cur_shop_desc = None
        self.cur_shop_other = None
        self.cur_shop_buy_success_replies = None
        self.cur_plugins_config = None
        
        # 插件系统
        self.plugins = {}

    async def wait_for_messages(self):
        """等待消息加载完成"""
        logger.debug('等待消息加载...')
        for _ in range(10):
            message_rows = await self.page.query_selector_all('[class^="ant-dropdown-trigger"]')
            if message_rows:
                logger.debug('消息已加载')
                return True
            await asyncio.sleep(1)
        logger.debug('等待消息加载超时')
        return False

    async def check_and_reply_new_messages(self):
        """检查并回复新消息"""
        if self.is_replying or self.is_processing_message:
            logger.debug('正在处理或回复消息，跳过本次检查')
            return

        if not await self.wait_for_messages():
            logger.debug('无法加载消息，跳过本次回复')
            return

        # 获取当前用户
        cur_user = await self.page.query_selector('[class^="text1"]')
        if not cur_user:
            logger.debug('未找到当前用户信息，跳过本次回复')
            return
        self.cur_user_name = await cur_user.text_content()

        # 等待商品信息加载
        try:
            async with asyncio.timeout(5):
                while not self.is_get_shop:
                    logger.debug("等待获取商品信息...")
                    await asyncio.sleep(1)
        except asyncio.TimeoutError:
            logger.warning("获取商品信息超时，跳过本次回复")
            return

        if not self.cur_shop_desc:
            logger.debug("未获取到商品信息，跳过本次回复")
            return
        
        # 每次处理消息前重新从数据库加载商品插件配置
        if self.cur_item_id:
            self.reload_shop_plugins_config()

        self.is_processing_message = True
        self.is_replying = True

        # 提取消息内容
        messages = await self.extract_messages()
        if messages:
            last_message = messages[-1]
            if last_message['role'] == 'user':
                # 打印用户最新消息
                logger.info(f"用户最新消息: {last_message['content']}")

                # 构建消息上下文
                context = {
                    "messages": messages,
                    "is_payed": self.auto_ship_required,
                    "is_ship": False,
                    "auto_ship_required": self.auto_ship_required,
                    "auto_notice_required": self.auto_notice_required,
                    "user_name": self.cur_user_name
                }
                
                # 执行插件链处理消息
                await self.execute_plugins_chain(last_message['content'], context)

        self.is_replying = False
        self.is_processing_message = False

    async def get_current_conversation_id(self):
        """获取当前对话ID"""
        conversation_element = await self.page.query_selector('.conversation-id')
        return await conversation_element.get_attribute('data-id') if conversation_element else None

    async def observe_new_messages(self):
        """监控新消息"""
        if self.is_replying or self.is_processing_message:
            logger.info('正在处理或回复消息，跳过本次检查')
            return

        logger.info('开始监控新消息...')
        chat_container = await self.page.query_selector('div.message-list--tD5r4eck#message-list-scrollable')
        if not chat_container:
            logger.info('未找到聊天容器，无法监控新消息')
            return

        self.current_conversation_id = await self.get_current_conversation_id()
        logger.info(f'新消息监控已成功启动，当前对话ID: {self.current_conversation_id}')

        # 立即检查一次，以防有未回复的消息
        await self.check_and_reply_new_messages()

    async def check_new_message_badge(self):
        """检查新消息角标"""
        if self.is_replying or self.is_processing_message:
            logger.info('正在处理或回复消息，跳过检查新消息角标')
            return False

        logger.debug('检查新消息角标...')
        unread_badge = await self.page.query_selector('#conv-list-scrollable .rc-virtual-list-holder div.ant-dropdown-trigger span sup')
        if unread_badge:
            badge_text = await unread_badge.text_content()
            logger.debug(f'找到消息角标，待回复消息数量: {badge_text}')
            if badge_text != '0':
                logger.info('检测到新消息，尝试点击角标...')
                await self.click_badge(unread_badge)
                return True
        else:
            logger.debug('未找到消息角标元素')
        return False

    async def click_badge(self, badge):
        """点击消息角标"""
        clickable_element = await badge.query_selector('a, button, *')
        if clickable_element:
            logger.debug('找到可点击元素，模拟点击...')
            await clickable_element.click()
            logger.debug('已模拟点击操作')
            await asyncio.sleep(2)
            await self.check_and_reply_new_messages()
        else:
            logger.warning('未找到与角标关联的可点击元素')

    async def extract_messages(self):
        """提取消息内容"""
        logger.debug('开始提取消息内容...')
        message_rows = await self.page.query_selector_all('[class^="message-row"]')
        messages = []
        latest_cust_msg_queue = deque(maxlen=1)
        is_payed = False
        is_ship = False
        
        # 从配置中获取关键字
        auto_ship_text = config.get("system", {}).get("auto_ship_text", "【自动发货】")
        auto_notice_text = config.get("system", {}).get("auto_notice_text", "转人工")
        
        for row in message_rows:
            # 付款信息
            bug_msg = await row.query_selector('[class*="msg-dx-title"]')
            if bug_msg:
                bug_msg_text = await bug_msg.text_content()
                if '我已付款，等待你发货' in bug_msg_text:
                    is_payed = True

            # 聊天消息
            message_content = await row.query_selector('[class*="message-text"]')
            if message_content:
                content = await message_content.text_content()
                content = content.strip()
                # 判断是否是自己
                is_own_message = 'message-text-right' in await message_content.get_attribute('class')

                if is_own_message:
                    # 发货关键字 判断自己是否已发货
                    if auto_ship_text in content:
                        is_ship = True
                else:
                    # 客户最新的消息队列
                    latest_cust_msg_queue.append(content)

                # 拼接消息
                role = 'assistant' if is_own_message else 'user'
                messages.append({'role': role, 'content': content})
                
        # 需要自动发货 已付款并没发货
        self.auto_ship_required = is_payed and not is_ship

        # 客户最新的消息队列
        for msg in latest_cust_msg_queue:
            # 转人工关键字 判断是否需要转人工客服
            if auto_notice_text in msg:
                self.auto_notice_required = True

        return messages

    async def send_message(self, message):
        """发送消息"""
        logger.info('开始发送消息...')
        textarea = await self.page.query_selector('textarea.ant-input')
        if not textarea:
            logger.warning('未找到消息输入框')
            return

        # 处理字符串中的每个字符
        for char in message:
            if char == '\n':
                # 模拟 Shift + Enter
                await self.page.keyboard.down('Shift')
                await textarea.press('Enter')
                await self.page.keyboard.up('Shift')
            else:
                # 输入普通字符
                await textarea.type(char)
        await textarea.press('Enter')

        logger.info(f'已尝试发送消息: {message}')

    async def handle_request(self, request):
        """处理请求"""
        # 只处理特定的请求
        if "mtop.taobao.idle.item.detail.wireless.get" in request.url:
            await self.handle_request_get_context(request)
        # 添加对闲鱼PC端消息头信息的处理
        elif "mtop.idle.trade.pc.message.headinfo" in request.url:
            await self.handle_request_get_context(request)

    async def handle_request_get_context(self, request):
        """处理获取商品介绍的请求"""
        logger.debug("获取商品介绍")
        if request.method == "POST" and request.post_data:
            decoded_post_data = unquote(request.post_data)
            logger.debug(f"POST URL: {request.url} 请求参数: {decoded_post_data}")

            # 使用正则表达式提取 itemId
            match = re.search(r'"itemId":(\d+)', decoded_post_data)
            if match:
                item_id = match.group(1)  # 提取匹配到的数字部分
                logger.debug(f"提取到的 itemId: {item_id}")
                self.cur_item_id = item_id

                # 从数据库获取商品信息
                shop_info = get_shop_info(item_id)
                
                if shop_info:
                    # 设置商品信息
                    self.cur_shop_name = shop_info["shop_name"]
                    self.cur_shop_price = shop_info["shop_price"]
                    self.cur_shop_desc = shop_info["shop_desc"]
                    self.cur_shop_other = shop_info["shop_other"]
                    self.cur_shop_buy_success_replies = shop_info["buy_success_replies"]
                    self.cur_plugins_config = shop_info["plugins_config"]
                    self.is_get_shop = True
                    logger.info(f"从数据库获取到商品信息: {self.cur_shop_name}")
                else:
                    logger.warning(f"数据库中未找到商品信息: {item_id}")
                    # 设置默认值
                    self.cur_shop_name = "未知商品"
                    self.cur_shop_price = "未知价格"
                    self.cur_shop_desc = "未知描述"
                    self.cur_shop_other = ""
                    self.cur_shop_buy_success_replies = ""
                    self.cur_plugins_config = ["keyword", "auto_ship", "manual_service", "ai_reply"]
                    self.is_get_shop = True
                    
                    # 保存到数据库
                    shop_info = {
                        "shop_name": self.cur_shop_name,
                        "shop_price": self.cur_shop_price,
                        "shop_desc": self.cur_shop_desc,
                        "shop_other": self.cur_shop_other,
                        "buy_success_replies": self.cur_shop_buy_success_replies,
                        "plugins_config": self.cur_plugins_config
                    }
                    save_shop_info(item_id, shop_info)

    def register_plugin(self, plugin_name, plugin_func, priority=100):
        """注册一个插件
        
        Args:
            plugin_name: 插件名称
            plugin_func: 插件函数
            priority: 插件优先级，数字越小优先级越高，默认为100
        """
        self.plugins[plugin_name] = {
            "priority": priority,
            "handler": plugin_func
        }
        logger.info(f"插件 {plugin_name} 注册成功，优先级: {priority}")
        
    async def execute_plugin(self, plugin_name, *args, **kwargs):
        """执行插件
        
        Args:
            plugin_name: 插件名称
            *args, **kwargs: 传递给插件的参数
            
        Returns:
            插件执行结果
        """
        if plugin_name not in self.plugins:
            logger.warning(f"插件 {plugin_name} 未注册")
            return None
            
        try:
            result = await self.plugins[plugin_name]["handler"](self, *args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"执行插件 {plugin_name} 失败: {e}")
            return None
            
    async def execute_plugins_chain(self, message, context=None):
        """按优先级执行所有启用的插件
        
        Args:
            message: 用户消息
            context: 上下文信息
            
        Returns:
            是否有插件处理了消息
        """
        if not self.cur_plugins_config:
            logger.debug("没有启用的插件")
            return False
            
        # 获取当前商品启用的插件
        enabled_plugins = self.cur_plugins_config
        
        # 过滤出已注册且启用的插件
        plugins_to_execute = []
        for plugin_name in enabled_plugins:
            if plugin_name in self.plugins:
                plugins_to_execute.append({
                    "name": plugin_name,
                    "priority": self.plugins[plugin_name]["priority"]
                })
            else:
                logger.warning(f"插件 {plugin_name} 已启用但未注册")
                
        # 按优先级排序 - 数字越大优先级越高
        plugins_to_execute.sort(key=lambda x: x["priority"], reverse=True)
        
        # 依次执行插件
        for plugin_info in plugins_to_execute:
            plugin_name = plugin_info["name"]
            logger.info(f"执行插件 {plugin_name}，优先级: {plugin_info['priority']}")
            
            # 执行插件
            result = await self.execute_plugin(plugin_name, message, context=context)
            
            # 如果插件返回True，表示消息已处理，停止执行后续插件
            if result is True:
                logger.info(f"插件 {plugin_name} 已处理消息，停止执行后续插件")
                return True
                
        return False

    async def load_plugins(self):
        """加载所有插件"""
        # 确保插件目录存在
        if not PLUGINS_DIR.exists():
            logger.warning(f"插件目录不存在: {PLUGINS_DIR}")
            PLUGINS_DIR.mkdir(exist_ok=True)
            return
            
        # 遍历插件目录
        for item in os.listdir(PLUGINS_DIR):
            plugin_path = PLUGINS_DIR / item
            
            # 检查是否是目录且包含__init__.py文件
            if plugin_path.is_dir() and (plugin_path / "__init__.py").exists():
                try:
                    logger.info(f"尝试加载插件: {item}")
                    
                    # 导入插件模块
                    module_name = f"plugins.{item}"
                    plugin_module = importlib.import_module(module_name)
                    
                    # 从模块中获取所有类
                    for attr_name in dir(plugin_module):
                        if attr_name.startswith("__"):
                            continue
                            
                        attr = getattr(plugin_module, attr_name)
                        # 检查是否是插件类(有handle_message方法)
                        if isinstance(attr, type) and hasattr(attr, "handle_message"):
                            # 实例化插件
                            plugin_instance = attr()
                            plugin_name = getattr(plugin_instance, "name", attr_name.lower())
                            priority = getattr(plugin_instance, "priority", 100)
                            
                            # 使用实例方法作为处理函数
                            self.register_plugin(
                                plugin_name,
                                lambda bot, msg, context=None, instance=plugin_instance, **kwargs: 
                                    instance.handle_message(bot, msg, context=context, **kwargs),
                                priority
                            )
                            logger.info(f"插件 {plugin_name} 已加载，优先级: {priority}")
                            
                except Exception as e:
                    logger.error(f"加载插件 {item} 失败: {e}")
                    
        logger.info(f"已加载 {len(self.plugins)} 个插件")

    def reload_shop_plugins_config(self):
        """重新从数据库加载商品插件配置"""
        try:
            from database import get_shop_info
            
            # 从数据库获取最新的商品信息
            shop_info = get_shop_info(self.cur_item_id)
            
            if shop_info and "plugins_config" in shop_info:
                # 更新插件配置
                old_config = self.cur_plugins_config
                self.cur_plugins_config = shop_info["plugins_config"]
                
                # 如果配置有变化，记录日志
                if old_config != self.cur_plugins_config:
                    logger.info(f"商品 {self.cur_item_id} 插件配置已更新: {old_config} -> {self.cur_plugins_config}")
        except Exception as e:
            logger.error(f"重新加载商品插件配置失败: {e}")
