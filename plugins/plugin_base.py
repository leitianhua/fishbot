"""
闲鱼助手 - 插件基类

所有插件都应继承这个基类
"""

from abc import ABC, abstractmethod
from loguru import logger

class PluginBase(ABC):
    """插件基类"""
    
    # 插件元数据
    name = None  # 插件名称，如果不指定则使用类名
    description = "未提供描述"  # 插件描述
    version = "1.0.0"  # 插件版本
    author = "unknown"  # 插件作者
    priority = 100  # 插件优先级，数字越大优先级越高
    
    def __init__(self):
        """插件初始化"""
        if self.name is None:
            self.name = self.__class__.__name__
        logger.debug(f"插件 {self.name} 初始化")
    
    @abstractmethod
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
        pass 