"""
闲鱼助手 - 关键字检测插件

检测消息中的关键字并触发相应操作
"""

import json
import re
import os
import sys
from loguru import logger

# 导入基类
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(plugin_dir), ".."))
from plugins.plugin_base import PluginBase

class KeywordPlugin(PluginBase):
    """关键字检测插件类"""
    
    name = "keyword"  # 插件名称
    description = "检测消息中的关键字并触发相应操作"  # 插件描述
    version = "1.0.0"  # 插件版本
    author = "闲鱼助手"  # 插件作者
    priority = 300  # 插件优先级
    
    def __init__(self):
        super().__init__()
        # 加载配置
        self.load_config()
        
    def load_config(self):
        """加载配置"""
        # 配置文件路径
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
        
        # 默认配置
        self.keyword_rules = []
        
        # 如果有配置文件则加载
        if os.path.exists(config_path):
            try:
                import tomllib
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                self.keyword_rules = config.get("rules", [])
                logger.info(f"已加载关键字规则: {len(self.keyword_rules)}条")
            except Exception as e:
                logger.error(f"加载关键字规则失败: {e}")
    
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
        logger.info(f"关键字检测插件被触发: {message}")
        
        # 获取关键字规则 - 优先使用参数中的规则
        keyword_rules = kwargs.get("keyword_rules", self.keyword_rules)
        
        if not keyword_rules:
            logger.debug("未配置关键字规则")
            return False
            
        # 解析关键字规则
        try:
            if isinstance(keyword_rules, str):
                rules = json.loads(keyword_rules)
            else:
                rules = keyword_rules
                
            for rule in rules:
                keywords = rule.get("keywords", [])
                response = rule.get("response", "")
                action = rule.get("action", "")
                
                # 检查是否匹配关键字
                if any(keyword.lower() in message.lower() for keyword in keywords):
                    logger.info(f"检测到关键字匹配: {keywords}")
                    
                    # 发送响应消息
                    if response:
                        await chat_bot.send_message(response)
                        
                    # 执行动作
                    if action:
                        if action == "search_resource" and "query" in rule:
                            # 调用资源搜索插件
                            search_query = rule["query"]
                            logger.info(f"触发资源搜索: {search_query}")
                            await chat_bot.execute_plugin("resource_search", search_query, 
                                                         context=context, ai_detection=False)
                            return True
                        elif action == "custom_plugin" and "plugin_name" in rule:
                            # 调用自定义插件
                            plugin_name = rule["plugin_name"]
                            plugin_params = rule.get("plugin_params", {})
                            logger.info(f"触发自定义插件: {plugin_name}")
                            await chat_bot.execute_plugin(plugin_name, message, 
                                                         context=context, **plugin_params)
                            return True
                    
                    # 如果有响应消息但没有动作，也算处理了消息
                    if response:
                        return True
                        
        except Exception as e:
            logger.error(f"处理关键字规则时出错: {e}")
            
        return False 