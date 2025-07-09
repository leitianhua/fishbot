"""
闲鱼助手 - 自动转人工客服插件

负责检测转人工关键词并通知
"""

import os
import sys
import asyncio
from loguru import logger

# 导入基类
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(plugin_dir), ".."))
from plugins.plugin_base import PluginBase

class AutoNoticePlugin(PluginBase):
    """自动转人工客服插件类"""
    
    name = "manual_service"  # 插件名称
    description = "检测转人工关键词并通知"  # 插件描述
    version = "1.0.0"  # 插件版本
    author = "闲鱼助手"  # 插件作者
    priority = 800  # 插件优先级 - 第二高优先级
    
    def __init__(self):
        super().__init__()
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置"""
        # 配置文件路径
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
        
        # 默认配置
        default_config = {
            "auto_notice_text": "转人工",
            "reply_message": "已为您通知人工客服，请稍等..."
        }
        
        # 如果有配置文件则加载
        if os.path.exists(config_path):
            try:
                import tomllib
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                logger.info(f"已加载自动转人工客服插件配置")
                return config
            except Exception as e:
                logger.error(f"加载自动转人工客服插件配置失败: {e}")
        
        logger.warning("使用默认自动转人工客服插件配置")
        return default_config
    
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
        auto_notice_text = self.config.get("auto_notice_text", "转人工")
        if not auto_notice_required and auto_notice_text in message:
            auto_notice_required = True
            chat_bot.auto_notice_required = True
            
        if not auto_notice_required:
            logger.debug("不需要转人工客服")
            return False
            
        # 发送回复消息
        reply_message = self.config.get("reply_message", "已为您通知人工客服，请稍等...")
        await chat_bot.send_message(reply_message)
        
        # 发送通知
        user_name = context.get("user_name", "未知用户") if context else "未知用户"
        notice_message = f"客户：{user_name}:需要转人工"
        
        # 使用通知插件发送通知
        if "notice" in chat_bot.plugins:
            notice_plugin = chat_bot.plugins["notice"]["handler"]
            asyncio.create_task(notice_plugin.send_notice(notice_message))
        
        # 重置转人工标志
        chat_bot.auto_notice_required = False
        
        return True 