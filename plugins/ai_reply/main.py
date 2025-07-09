"""
闲鱼助手 - AI回复插件

使用AI模型回复客户消息
"""

import requests
import os
import sys
import re
from loguru import logger

# 导入基类
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(plugin_dir), ".."))
from plugins.plugin_base import PluginBase

class AIReplyPlugin(PluginBase):
    """AI回复插件类"""
    
    name = "ai_reply"  # 插件名称
    description = "使用AI模型回复客户消息"  # 插件描述
    version = "1.0.0"  # 插件版本
    author = "闲鱼助手"  # 插件作者
    priority = 100  # 插件优先级，最低优先级
    
    def __init__(self):
        super().__init__()
        # 加载配置
        self.load_config()
    
    def load_config(self):
        """加载配置"""
        # 配置文件路径
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
        
        # 默认配置
        self.api_key = '0e1ec3fdad241a16189b54ef6de10e96.P951D07Cn2Cw7lIu'
        self.api_url = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
        self.model = 'GLM-4-Flash'
        self.system_prompt = """不需要引导语句。不需要任何前缀。
            你现在的身份是闲鱼二手交易平台的卖家，你需要尽可能模仿真实的人回答客户的问题，并吸引客户下单，你需要根据商品介绍回答问题，需要简洁的回答
            商品价格：{price}
            商品介绍：{description}
            其他说明：{other}
            """
        
        # 如果有配置文件则加载
        if os.path.exists(config_path):
            try:
                import tomllib
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                self.api_key = config.get("api", {}).get("key", self.api_key)
                self.api_url = config.get("api", {}).get("url", self.api_url)
                self.model = config.get("api", {}).get("model", self.model)
                
                # 加载自定义系统提示词
                if "system_prompt" in config:
                    self.system_prompt = config.get("system_prompt")
                
                logger.info(f"已加载AI回复插件配置，模型: {self.model}")
            except Exception as e:
                logger.error(f"加载AI回复插件配置失败: {e}")
    
    def format_system_prompt(self, variables):
        """格式化系统提示词，替换变量
        
        Args:
            variables: 变量字典
            
        Returns:
            格式化后的系统提示词
        """
        prompt = self.system_prompt
        
        # 使用正则表达式查找所有变量占位符
        placeholders = re.findall(r'\{([^}]+)\}', prompt)
        
        # 替换变量
        for placeholder in placeholders:
            if placeholder in variables:
                prompt = prompt.replace(f"{{{placeholder}}}", str(variables[placeholder]))
            else:
                logger.warning(f"系统提示词中的变量 {{{placeholder}}} 未找到对应值")
        
        return prompt
    
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
        logger.info(f"AI回复插件被触发: {message}")
        
        # 如果需要自动发货，不进行AI回复
        if context and context.get("auto_ship_required"):
            logger.info("需要自动发货，跳过AI回复")
            return False
            
        # 获取消息列表
        messages = context.get("messages", []) if context else []
        
        # 准备变量字典
        variables = {
            "price": getattr(chat_bot, "cur_shop_price", "未知价格"),
            "description": getattr(chat_bot, "cur_shop_desc", "未知描述"),
            "other": getattr(chat_bot, "cur_shop_other", ""),
            "shop_name": getattr(chat_bot, "cur_shop_name", "未知商品"),
            "user_name": context.get("user_name", "客户") if context else "客户",
            "message": message
        }
        
        # 添加商品自定义变量
        if hasattr(chat_bot, "cur_shop_custom_vars") and isinstance(chat_bot.cur_shop_custom_vars, dict):
            variables.update(chat_bot.cur_shop_custom_vars)
        
        # 格式化系统提示词
        formatted_prompt = self.format_system_prompt(variables)
        
        # 构建系统提示
        system_message = {
            "role": "system",
            "content": formatted_prompt
        }
        
        # 添加系统提示
        all_messages = [system_message, *messages]
        
        try:
            # 调用API获取回复
            response = requests.post(
                self.api_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                },
                json={
                    "model": self.model,
                    "messages": all_messages
                }
            )
            response.raise_for_status()  # 检查请求是否成功
            data = response.json()
            reply = data.get('choices', [{}])[0].get('message', {}).get('content', '无法获取回复')
            logger.info(f'AI回复: {reply}')
            
            # 发送回复
            await chat_bot.send_message(reply)
            return True
            
        except requests.RequestException as e:
            logger.error(f'请求AI接口失败: {e}')
            return False