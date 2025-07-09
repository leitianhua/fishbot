"""
闲鱼助手 - 通知插件

负责发送各种通知消息(钉钉、微信等)
"""

import os
import sys
import time
import json
from loguru import logger

# 导入基类
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(plugin_dir), ".."))
from plugins.plugin_base import PluginBase

class NoticePlugin(PluginBase):
    """通知插件类"""
    
    name = "notice"  # 插件名称
    description = "发送各种通知消息(钉钉、微信等)"  # 插件描述
    version = "1.0.0"  # 插件版本
    author = "闲鱼助手"  # 插件作者
    priority = 200  # 插件优先级
    
    def __init__(self):
        super().__init__()
        # 加载配置
        self.config = self.load_config()
        # 已发送消息的哈希值和时间戳
        self.sent_hashes = {}
        
        # 导入需要的模块
        try:
            import aiohttp
            self.aiohttp = aiohttp
        except ImportError:
            logger.error("未安装aiohttp，请使用pip install aiohttp安装")
            
        if self.config.get("wxpusher", {}).get("enabled", False):
            try:
                from wxpusher import WxPusher
                self.WxPusher = WxPusher
            except ImportError:
                logger.error("未安装wxpusher，请使用pip install wxpusher安装")
                self.config["wxpusher"]["enabled"] = False
                
        # 初始化通知渠道状态
        self.channels_status = {
            "dingding": self.config.get("dingding", {}).get("enabled", False),
            "wxpusher": self.config.get("wxpusher", {}).get("enabled", False)
        }
        
        # 记录初始化完成
        logger.info(f"通知插件初始化完成，已启用的通知渠道: {[k for k, v in self.channels_status.items() if v]}")
        
        # 发送插件启动通知
        self.send_startup_notice()
    
    def load_config(self):
        """加载配置"""
        # 配置文件路径
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
        
        # 默认配置
        default_config = {
            "dingding": {
                "enabled": True,
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=5c22c63ba1a742a9a09eee52b551a02c6059230a777835e89e237b87306c63b4",
                "keyword": "【闲鱼助手】"
            },
            "wxpusher": {
                "enabled": True,
                "token": "AT_jQkJqc1f9R13kVVdjwxFNcG4pWLNerOq",
                "uids": ["UID_DebxzN3NJVgefxEhL7FLq5tzPWbg"]
            },
            "cooldown": 600,  # 10分钟内不重复发送相同消息
            "startup_notice": True  # 是否在启动时发送通知
        }
        
        # 如果有配置文件则加载
        if os.path.exists(config_path):
            try:
                import tomllib
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                logger.info(f"已加载通知插件配置")
                return config
            except Exception as e:
                logger.error(f"加载通知插件配置失败: {e}")
        
        logger.warning("使用默认通知插件配置")
        return default_config
    
    def send_startup_notice(self):
        """发送插件启动通知"""
        if self.config.get("startup_notice", True):
            import asyncio
            # 获取主机名
            import socket
            hostname = socket.gethostname()
            # 获取IP地址
            try:
                ip_address = socket.gethostbyname(hostname)
            except:
                ip_address = "未知"
            
            # 获取当前时间
            import datetime
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 构建启动通知消息
            startup_message = f"通知插件已启动\n时间: {current_time}\n主机: {hostname}\nIP: {ip_address}"
            
            # 异步发送通知
            asyncio.create_task(self.send_notice(startup_message, pre="系统通知"))
    
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
        # 获取用户信息
        user_name = context.get("user_name", "未知用户") if context else "未知用户"
        
        # 构建通知消息
        notice_message = f"用户 {user_name} 发送消息:\n{message}"
        
        # 发送通知
        await self.send_notice(notice_message, pre="用户消息")
        
        # 通知插件不处理用户消息，只发送通知
        return False
    
    async def send_notice(self, message, pre=''):
        """发送通知消息
        
        Args:
            message: 要发送的消息内容
            pre: 消息前缀
            
        Returns:
            bool: 是否发送成功
        """
        # 如果 message 是列表，提取每个字典中的 'content' 和 'role' 值并拼接成字符串
        if isinstance(message, list):
            formatted_message = []
            for item in message:
                role = item.get('role', 'unknown')  # 默认角色为 'unknown'
                content = item.get('content', '')  # 默认内容为空字符串
                formatted_message.append(f"{role}：{content}")
            message = "\n".join(formatted_message)

        # 生成消息的唯一标识（哈希值）
        message_hash = hash((message, pre))  # 包括前缀和消息内容

        # 获取当前时间戳
        current_timestamp = time.time()
        cooldown = self.config.get("cooldown", 600)  # 默认10分钟

        # 检查是否已经发送过该消息，并且是否过期
        if message_hash in self.sent_hashes:
            sent_timestamp = self.sent_hashes[message_hash]
            if current_timestamp - sent_timestamp < cooldown:
                logger.debug(f"消息已发送过且未过期，跳过重复发送")
                return False

        # 记录发送的消息
        logger.info(f"发送通知: {message[:100]}{'...' if len(message) > 100 else ''}")
        
        # 标记是否有任何通知渠道成功发送
        success = False

        # 钉钉消息通知
        if self.config.get("dingding", {}).get("enabled", False):
            dingding_result = await self._send_dingding(message, pre)
            success = success or dingding_result

        # 微信wxpusher
        if self.config.get("wxpusher", {}).get("enabled", False):
            wxpusher_result = await self._send_wxpusher(message, pre)
            success = success or wxpusher_result

        # 只有在成功发送时才更新哈希值
        if success:
            # 更新已发送消息的哈希值和时间戳
            self.sent_hashes[message_hash] = current_timestamp

            # 清理过期的消息哈希值
            self.sent_hashes = {k: v for k, v in self.sent_hashes.items() if current_timestamp - v < cooldown}
            
            return True
        else:
            logger.warning("所有通知渠道发送失败")
            return False
    
    async def _send_dingding(self, message, pre=''):
        """发送钉钉消息
        
        Returns:
            bool: 是否发送成功
        """
        try:
            dingding_config = self.config.get("dingding", {})
            webhook = dingding_config.get("webhook", "")
            keyword = dingding_config.get("keyword", "【闲鱼助手】")
            
            # 构造请求数据
            headers = {"Content-Type": "application/json;charset=utf-8"}
            data = {
                "msgtype": "text",
                "text": {
                    "content": f'{keyword}{pre}\n {message}'
                }
            }

            # 发送 POST 请求
            async with self.aiohttp.ClientSession() as session:
                async with session.post(webhook, headers=headers, json=data) as response:
                    response_data = await response.json()
                    if response_data.get("errcode") == 0:
                        logger.info(f"钉钉消息发送成功")
                        return True
                    else:
                        logger.error(f"钉钉消息发送失败: {response_data}")
                        return False
        except Exception as e:
            logger.error(f"发送钉钉消息失败: {e}")
            return False
    
    async def _send_wxpusher(self, message, pre=''):
        """发送微信消息
        
        Returns:
            bool: 是否发送成功
        """
        try:
            wxpusher_config = self.config.get("wxpusher", {})
            token = wxpusher_config.get("token", "")
            uids = wxpusher_config.get("uids", [])
            
            # 构建完整消息
            full_message = f'{pre}\n {message}' if pre else message
            
            # 发送消息
            response_data = self.WxPusher.send_message(full_message, uids=uids, token=token)
            
            # 检查发送结果
            if isinstance(response_data, dict) and response_data.get("code") == 1000:
                logger.info(f"微信wxpusher消息发送成功")
                return True
            else:
                logger.error(f"微信wxpusher消息发送失败: {response_data}")
                return False
        except Exception as e:
            logger.error(f"发送微信消息失败: {e}")
            return False
            
    async def send_system_notice(self, title, content):
        """发送系统通知
        
        Args:
            title: 通知标题
            content: 通知内容
            
        Returns:
            bool: 是否发送成功
        """
        message = f"【{title}】\n{content}"
        return await self.send_notice(message, pre="系统通知")
        
    async def send_user_notice(self, user_name, content):
        """发送用户相关通知
        
        Args:
            user_name: 用户名
            content: 通知内容
            
        Returns:
            bool: 是否发送成功
        """
        message = f"用户 {user_name} 的消息:\n{content}"
        return await self.send_notice(message, pre="用户通知")