"""
资源搜索插件

此插件用于搜索资源并转存到网盘
"""

from loguru import logger

# 导入插件基类
from plugins.plugin_base import PluginBase

# 导入核心工具类
from .utils.core import ResourceCore

class ResourceSearchPlugin(PluginBase):
    """资源搜索插件类"""
    
    name = "resource_search"  # 插件名称
    description = "搜索网盘资源并返回结果"  # 插件描述
    version = "1.0.0"  # 插件版本
    author = "闲鱼助手"  # 插件作者
    priority = 500  # 插件优先级
    
    def __init__(self):
        """初始化插件"""
        super().__init__()
        
        # 初始化核心工具类
        self.core = ResourceCore()
        logger.info("资源搜索插件初始化完成")

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
        if not self.core or not self.core.conf:
            logger.error("资源搜索插件核心工具类未初始化或配置未加载")
            return False
            
        logger.info(f"资源搜索插件被触发: {message}")
        
        # 处理搜索指令
        if not any(message.startswith(prefix) for prefix in ["搜", "搜索"]):
            logger.debug("未匹配前缀")
            return False

        # 移除前缀，获取搜索内容
        def remove_prefix(text, prefixes):
            for prefix in prefixes:
                if text.startswith(prefix):
                    return text[len(prefix):].strip()
            return text.strip()

        search_keyword = remove_prefix(message, ["搜", "搜索"]).strip()
        
        try:
            # 调用核心搜索功能
            results = self.core.search_and_store(search_keyword)
            
            # 格式化结果
            search_reply = self.core.format_results(results, search_keyword)
            
            # 发送搜索结果
            await chat_bot.send_message(search_reply)
            return True
            
        except Exception as e:
            logger.error(f'资源搜索失败: {e}')
            await chat_bot.send_message(f"搜索过程中发生错误: {str(e)}")
            return True 