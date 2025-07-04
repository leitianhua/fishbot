"""
闲鱼助手 - 自动转人工客服插件

检测转人工客服请求并通知
"""

import asyncio
import os
import sys
from loguru import logger

# 导入基类
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(plugin_dir), ".."))
from plugins.plugin_base import PluginBase

class AutoNoticePlugin(PluginBase):
    """自动转人工客服插件类"""
    
    name = "auto_notice"  # 插件名称
    description = "检测转人工客服请求并通知"  # 插件描述
    version = "1.0.0"  # 插件版本
    author = "闲鱼助手"  # 插件作者
    priority = 800  # 插件优先级，仅次于自动发货
    
    async def handle_message(self, chat_bot, message, context=None, **kwargs):
        """处理消息
        
        Args:
            chat_bot: ChatBot实例
            message: 触发插件的用户消息
            context: 消息上下文
            **kwargs: 额外参数
            
        Returns:
            True 如果消息已处理，False 如果未处理
        """
        logger.info(f"自动转人工客服插件被触发: {message}")
        
        # 检查是否需要自动转人工客服
        auto_notice_required = context.get("auto_notice_required", False) if context else False
        
        # 检查消息中是否包含转人工关键词
        if not auto_notice_required and "转人工" in message:
            auto_notice_required = True
            
        if not auto_notice_required:
            logger.debug("不需要转人工客服")
            return False
            
        # 发送通知
        await chat_bot.send_message(f"已为您通知人工客服，请稍等...")
        
        # 调用发送通知消息的函数
        if hasattr(chat_bot, 'send_notice_msg'):
            asyncio.create_task(chat_bot.send_notice_msg(f"客户：{chat_bot.cur_user_name}:需要转人工"))
        
        return True 