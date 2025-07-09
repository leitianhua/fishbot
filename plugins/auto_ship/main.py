"""
闲鱼助手 - 自动发货插件

负责检测付款状态并自动发货
"""

import os
import sys
from loguru import logger

# 导入基类
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(plugin_dir), ".."))
from plugins.plugin_base import PluginBase

class AutoShipPlugin(PluginBase):
    """自动发货插件类"""
    
    name = "auto_ship"  # 插件名称
    description = "检测付款状态并自动发货"  # 插件描述
    version = "1.0.0"  # 插件版本
    author = "闲鱼助手"  # 插件作者
    priority = 900  # 插件优先级 - 最高优先级

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
            "auto_ship_text": "【自动发货】"
        }

        # 如果有配置文件则加载
        if os.path.exists(config_path):
            try:
                import tomllib
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                logger.info(f"已加载自动发货插件配置")
                return config
            except Exception as e:
                logger.error(f"加载自动发货插件配置失败: {e}")

        logger.warning("使用默认自动发货插件配置")
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
        logger.info(f"自动发货插件被触发: {message}")
        
        # 检查是否需要自动发货
        auto_ship_required = context.get("auto_ship_required", False) if context else False
        
        if not auto_ship_required:
            logger.debug("不需要自动发货")
            return False
            
        # 获取发货内容
        buy_success_replies = chat_bot.cur_shop_buy_success_replies
        if not buy_success_replies:
            logger.warning("未设置自动发货内容")
            return False
            
        # 发送自动发货内容
        auto_ship_text = self.config.get("auto_ship_text", "【自动发货】")
        ship_text = f"{auto_ship_text}: \n{buy_success_replies}"
        await chat_bot.send_message(ship_text)
        logger.info(f"已自动发货: {ship_text}")
        
        # 重置自动发货标志
        chat_bot.auto_ship_required = False

        return True