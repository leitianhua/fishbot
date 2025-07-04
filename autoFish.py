"""
闲鱼助手 - 自动回复与资源搜索功能

功能说明：
1. 自动回复客户消息
2. 自动发货
3. 自动转人工客服
4. 资源搜索功能

资源搜索功能使用说明：
1. 客户可以直接使用"搜索:关键词"或"搜:关键词"指令搜索资源
2. AI会智能识别客户的资源搜索意图，自动触发搜索
3. 搜索结果包含网盘链接，30分钟后自动删除

配置说明：
1. 每个商品可单独配置是否开启AI回复功能
2. 资源搜索功能依赖ToolResourceSearcher模块
3. 默认使用夸克网盘存储搜索结果

使用示例：
客户: 我想找三体这本书
AI: [识别搜索意图] 正在为您搜索"三体"相关资源，请稍等...

客户: 搜索:python教程
系统: [直接搜索] 正在为您搜索"python教程"相关资源，请稍等...
"""

import os
import re
import sys
import json
import time
import random
import asyncio
import sqlite3
import requests
import importlib.util
from collections import deque
from datetime import datetime
from urllib.parse import unquote
from loguru import logger

# 加载.env文件
def load_dotenv():
    try:
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
            return True
    except Exception as e:
        print(f"加载.env文件失败: {e}")
    return False

# 加载环境变量
load_dotenv()

# 配置loguru
# 移除默认处理器
logger.remove()
# 设置日志级别，可以通过环境变量控制
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
# 添加控制台处理器
logger.add(sys.stderr, level=LOG_LEVEL, 
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
# 添加文件处理器
logger.add("logs/autofish_{time:YYYY-MM-DD}.log", rotation="00:00", retention="7 days", level=LOG_LEVEL, encoding="utf-8")

logger.info(f"日志级别设置为: {LOG_LEVEL}")

# 设置日志
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# log = logging.getLogger()

# 是否开启Ai回复
open_chatai = False
# chatAi配置
API_KEY = '0e1ec3fdad241a16189b54ef6de10e96.P951D07Cn2Cw7lIu'
API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'

# 用户数据目录和浏览器路径
# user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data","可爱尼")
user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data", "大号")
executable_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 设置数据库路径
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "items.db")

# 自动发货关键字
auto_ship_text = '【自动发货】'
# 转人工关键字
auto_notice_text = '转人工'

# 开启消息通知
enable_notice = True
# wxpusher token
wxpusher_token = "AT_jQkJqc1f9R13kVVdjwxFNcG4pWLNerOq"

# 钉钉机器人webhook
open_dingding = True
dingding_webhook = 'https://oapi.dingtalk.com/robot/send?access_token=5c22c63ba1a742a9a09eee52b551a02c6059230a777835e89e237b87306c63b4'
dingding_keyword = "【闲鱼助手】"

# 微信WxPusher 消息平台
open_wxpusher = True
wxpusher_uids = ["UID_DebxzN3NJVgefxEhL7FLq5tzPWbg"]

try:
    from playwright.async_api import async_playwright
except ImportError:
    logger.error("未安装playwright，请使用pip install playwright安装")

try:
    import aiohttp
except ImportError:
    logger.error("未安装aiohttp，请使用pip install aiohttp安装")
    
try:
    from wxpusher import WxPusher
except ImportError:
    logger.error("未安装wxpusher，请使用pip install wxpusher安装")

async def send_notice_msg(message, pre=''):
    """
    异步发送消息
    :param message: 要发送的文本内容
    :param pre: 前缀
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

    # 静态字典，用于存储已发送的消息哈希值和时间戳
    if not hasattr(send_notice_msg, "sent_hashes"):
        send_notice_msg.sent_hashes = {}

    # 获取当前时间戳
    current_timestamp = time.time()

    # 检查是否已经发送过该消息，并且是否过期（10分钟内不重复发送）
    if message_hash in send_notice_msg.sent_hashes:
        sent_timestamp = send_notice_msg.sent_hashes[message_hash]
        if current_timestamp - sent_timestamp < 600:  # 600秒 = 10分钟
            logger.debug(f"消息已发送过且未过期，跳过重复发送")
            return

    # 钉钉消息通知
    if open_dingding:
        # 构造请求数据
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {
            "msgtype": "text",
            "text": {
                "content": f'{dingding_keyword}{pre}\n {message}'
            }
        }

        # 发送 POST 请求
        async with aiohttp.ClientSession() as session:
            async with session.post(dingding_webhook, headers=headers, json=data) as response:
                response_data = await response.json()
                logger.info(f"钉钉机器人: {response_data}")  # 打印发送结果，但不阻塞后续逻辑

    # 微信wxpusher
    if open_wxpusher:
        response_data = WxPusher.send_message(f'{pre}\n {message}', uids=wxpusher_uids, token=wxpusher_token)
        logger.info(f"微信wxpusher: {response_data}")  # 打印发送结果，但不阻塞后续逻辑

    # 更新已发送消息的哈希值和时间戳
    send_notice_msg.sent_hashes[message_hash] = current_timestamp

    # 清理过期的消息哈希值
    send_notice_msg.sent_hashes = {k: v for k, v in send_notice_msg.sent_hashes.items() if current_timestamp - v < 600}


class ChatBot:
    def __init__(self, page):
        self.page = page
        self.is_replying = False
        # 是否需要自动发货
        self.auto_ship_required = False
        # 是否自动转人工客服
        self.auto_notice_required = False
        # 是否获取到了商品信息
        self.is_get_shop = False
        self.cur_user_name = None
        self.cur_item_id = None
        self.cur_shop_name = None
        self.cur_shop_price = None
        self.cur_shop_desc = None
        self.cur_shop_other = None
        self.cur_shop_buy_success_replies = None
        # 当前商品的插件配置
        self.cur_plugins_config = None
        # 已加载的插件列表 {plugin_name: {"priority": priority, "handler": handler_func}}
        self.plugins = {}
        self.is_processing_message = False
        self.current_conversation_id = None
        
        # 加载插件会在初始化后异步调用
        # 不要在__init__中使用await，因为__init__不能是异步函数

    async def wait_for_messages(self):
        logger.debug('等待消息加载...')
        for _ in range(10):
            # message_rows = await self.page.query_selector_all('[class^="message-row"]')
            message_rows = await self.page.query_selector_all('[class^="ant-dropdown-trigger"]')
            if message_rows:
                logger.debug('消息已加载')
                return True
            await asyncio.sleep(1)
        logger.debug('等待消息加载超时')
        return False

    async def check_and_reply_new_messages(self):
        if self.is_replying or self.is_processing_message:
            logger.debug('正在处理或回复消息，跳过本次检查')
            return

        if not await self.wait_for_messages():
            logger.debug('无法加载消息，跳过本次回复')
            return

        # 当前用户
        cur_user = await self.page.query_selector('[class^="text1"]')
        if not cur_user:
            logger.debug('未找到当前用户信息，跳过本次回复')
            return
        self.cur_user_name = await cur_user.text_content()

        # 异步获取商品信息，设置超时时间为5秒
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

        self.is_processing_message = True
        self.is_replying = True

        # 开始提取消息内容
        messages = await self.extract_messages()
        if messages:
            last_message = messages[-1]
            if last_message['role'] == 'user':
                # 打印用户最新消息
                logger.info(f"用户最新消息: {last_message['content']}")

                # 钉钉通知闲鱼消息
                if enable_notice:
                    asyncio.create_task(send_notice_msg(pre=f"客户：{self.cur_user_name}\n", message=messages))
                
                # 执行插件链处理消息
                context = {
                    "messages": messages,
                    "is_payed": self.auto_ship_required,
                    "is_ship": False,
                    "auto_ship_required": self.auto_ship_required,
                    "auto_notice_required": self.auto_notice_required
                }
                
                message_handled = await self.execute_plugins_chain(last_message['content'], context)
                
                # 如果没有插件处理消息，且配置了AI回复，则使用AI回复
                if not message_handled and self.cur_plugins_config and "ai_reply" in self.cur_plugins_config:
                    logger.info('没有插件处理消息，使用AI回复')
                    reply = await self.get_gpt_reply(messages)
                    if reply:
                        await self.send_message(reply)

        # 是否需要自动发货
        if self.auto_ship_required:
            await self.send_message(f"{auto_ship_text}: \n{self.cur_shop_buy_success_replies}")
            self.auto_ship_required = False

        # 是否需要转人工
        if self.auto_notice_required:
            asyncio.create_task(send_notice_msg(f"客户：{self.cur_user_name}:需要转人工"))
            await self.send_message(f"已为您通知")
            self.auto_notice_required = False

        self.is_replying = False
        self.is_processing_message = False

    async def get_current_conversation_id(self):
        conversation_element = await self.page.query_selector('.conversation-id')
        return await conversation_element.get_attribute('data-id') if conversation_element else None

    async def observe_new_messages(self):
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
        if self.is_replying or self.is_processing_message:
            logger.info('正在处理或回复消息，跳过检查新消息角标')
            return False

        logger.debug('检查新消息角标...')
        # 标签.标签下的 类class1.类class2
        # <span class="ant-scroll-number-only-unit current">4</span>
        # span.ant-scroll-number-only-unit.current
        # unread_badge = await self.page.query_selector('span.ant-scroll-number-only-unit.current') # 已过时
        # 找到角标元素 右击元素 复制 -> 复制selector
        # unread_badge = await self.page.query_selector('#conv-list-scrollable > div > div.rc-virtual-list-holder > div > div > div:nth-child(1) > div > div > div.ant-dropdown-trigger > div:nth-child(1) > div:nth-child(1) > span > sup')
        unread_badge = await self.page.query_selector('#conv-list-scrollable .rc-virtual-list-holder div.ant-dropdown-trigger span sup')
        if unread_badge:
            logger.debug(f'找到消息角标，待回复消息数量: {await unread_badge.text_content()}')
            if await unread_badge.text_content() != '0':
                logger.info('检测到新消息，尝试点击角标...')
                await self.click_badge(unread_badge)
                return True
        else:
            logger.debug('未找到消息角标元素')
        return False

    async def click_badge(self, badge):
        clickable_element = await badge.query_selector('a, button, *')
        # clickable_element = await badge.query_selector(f'xpath=/html/body/div[2]/div[2]/div/div/aside/div/div[2]/div/div[1]/div/div/div[1]/div/div/div[1]/div[1]/div[2]')
        if clickable_element:
            logger.debug('找到可点击元素，模拟点击...')
            await clickable_element.click()
            logger.debug('已模拟点击操作')
            await asyncio.sleep(2)
            await self.check_and_reply_new_messages()
        else:
            logger.warning('未找到与角标关联的可点击元素')



    async def extract_messages(self):
        logger.debug('开始提取消息内容...')
        message_rows = await self.page.query_selector_all('[class^="message-row"]')
        messages = []
        latest_cust_msg_queue = deque(maxlen=1)
        is_payed = False
        is_ship = False
        
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

    async def get_gpt_reply(self, messages):
        """
        获取GPT回复
        """
        # 使用AI回复插件
        context = {"messages": messages}
        if "ai_reply" in self.plugins:
            await self.execute_plugin("ai_reply", messages[-1]["content"], context=context)
            return None  # 插件会直接发送消息，这里返回None
        else:
            logger.warning("AI回复插件未加载，无法获取回复")
            return "AI回复插件未加载，请联系管理员"

    async def get_element_text(self, url, shop_name_xpath, shop_price_xpath, shop_desc_xpath):
        try:
            page = await self.page.context.new_page()
            await page.goto(url)
            await page.wait_for_load_state("networkidle")

            shop_name = await page.query_selector(shop_name_xpath)
            shop_price = await page.query_selector(shop_price_xpath)
            shop_desc = await page.query_selector(shop_desc_xpath)
            if shop_name and shop_price and shop_desc:
                return await shop_name.text_content(), await shop_price.text_content(), await shop_desc.text_content()
            else:
                logger.warning("未找到目标元素，请检查 XPath 是否正确。")
                return None, None, None
        except Exception as e:
            logger.error(f"获取元素时出错: {e}")
            return None, None, None
        finally:
            await page.close()

    async def handle_request_get_context(self, request):
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

                # 检查数据库中是否有该商品信息
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT shop_name, shop_price, shop_desc, shop_other, buy_success_replies, plugins_config FROM xianyu_shop WHERE item_id = ?", (item_id,))
                result = cursor.fetchone()
                conn.close()

                shop_name, shop_price, shop_desc, shop_other, buy_success_replies, plugins_config = None, None, None, None, None, None
                if result:
                    shop_name, shop_price, shop_desc, shop_other, buy_success_replies, plugins_config = result
                    logger.info(f"从数据库中获取到的商品信息：{shop_name}, {shop_desc}")
                else:
                    # 打开详情页并获取文本内容
                    target_url = f"https://www.goofish.com/item?id={item_id}&categoryId=0"
                    shop_name_xpath = '//*[@id="content"]/div[1]/div[2]/div[2]/div[3]/div[1]/div/span/span[1]/span'
                    shop_price_xpath = '//*[@id="content"]/div[1]/div[2]/div[2]/div[2]/div[1]/div/div[2]'
                    shop_desc_xpath = '//*[@id="content"]/div[1]/div[2]/div[2]/div[3]/div[1]/div/span'
                    try:
                        result = await self.get_element_text(target_url, shop_name_xpath, shop_price_xpath, shop_desc_xpath)
                        if result[0] is not None:  # 检查是否成功获取到商品名称
                            shop_name, shop_price, shop_desc = result
                            logger.info(f"打开详情页 id：{item_id} 商品：{shop_name} 商品介绍：{shop_desc}")
                        else:
                            logger.error(f"获取商品信息失败：id：{item_id} 无法获取商品详情")
                            shop_name, shop_price, shop_desc, shop_other = None, None, None, None
                    except Exception as e:
                        logger.error(f"获取商品信息失败：id：{item_id}  error:{e}")
                        shop_name, shop_price, shop_desc, shop_other = None, None, None, None

                    # 保存到数据库中
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                            INSERT INTO xianyu_shop (item_id, shop_name, shop_price, shop_desc, plugins_config) 
                            VALUES (?, ?, ?, ?, ?) 
                            ON CONFLICT(item_id) 
                            DO UPDATE SET shop_name = excluded.shop_name, shop_desc = excluded.shop_desc
                        """, (item_id, shop_name, shop_price, shop_desc, None))
                    conn.commit()
                    conn.close()
                    logger.info(f"商品信息已保存到数据库：id={item_id}, 名称={shop_name}, 描述={shop_desc}")

                self.is_get_shop = True
                self.cur_item_id = item_id
                self.cur_shop_name = shop_name
                self.cur_shop_price = shop_price
                self.cur_shop_desc = shop_desc
                self.cur_shop_other = shop_other
                self.cur_shop_buy_success_replies = buy_success_replies
                
                # 解析插件配置 - 只使用插件名称数组
                self.cur_plugins_config = []
                if plugins_config:
                    try:
                        self.cur_plugins_config = json.loads(plugins_config)
                        if not isinstance(self.cur_plugins_config, list):
                            logger.error(f"插件配置必须是数组格式: {plugins_config}")
                            self.cur_plugins_config = []
                    except json.JSONDecodeError:
                        logger.error(f"插件配置解析失败: {plugins_config}")
                
                logger.info(f"商品 {item_id} 的插件配置: {self.cur_plugins_config}")
            else:
                logger.warning("未提取到 itemId，请检查正则表达式是否正确。")

    async def handle_request(self, request):
        # 不记录HTTP请求日志
        # 只处理特定的请求
        
        # 处理获取商品介绍的请求
        if "mtop.taobao.idle.item.detail.wireless.get" in request.url:
            await self.handle_request_get_context(request)
        # 添加对闲鱼PC端消息头信息的处理
        elif "mtop.idle.trade.pc.message.headinfo" in request.url:
            await self.handle_request_get_context(request)
        # 可以添加更多请求处理逻辑
        else:
            # 调试模式下才记录未处理的请求
            if False:  # 设置为False关闭HTTP请求日志
                logger.debug(f"未匹配到任何处理逻辑的请求: {request.url}")

    async def handle_response(self, response):
        # 不记录HTTP响应日志
        # 只有在调试模式下才记录响应信息
        if False:  # 设置为False关闭HTTP响应日志
            logger.debug(f"Response: {response.status} {response.url}")
        # 如果需要，可以查看响应内容
        # response.text().then(print)

    async def search_resource(self, keyword):
        """搜索资源
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果
        """
        # 这个方法已经移动到resource_search_plugin插件中
        logger.warning("search_resource方法已废弃，请使用resource_search_plugin插件")
        return False
        
    async def process_keyword_detection(self, message):
        """处理关键字检测
        
        Args:
            message: 用户消息
            
        Returns:
            是否触发了关键字
        """
        # 这个方法已经移动到keyword_plugin插件中
        logger.warning("process_keyword_detection方法已废弃，请使用keyword_plugin插件")
        return False

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
            logger.info(f"执行插件 {plugin_name}")
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
        # 插件目录
        plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
        if not os.path.exists(plugins_dir):
            logger.warning(f"插件目录不存在: {plugins_dir}")
            os.makedirs(plugins_dir)
            
        # 加载文件夹式插件（插件目录下的子文件夹）
        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)
            if os.path.isdir(item_path) and not item.startswith("__"):
                try:
                    # 检查是否有__init__.py文件
                    init_file = os.path.join(item_path, "__init__.py")
                    if not os.path.exists(init_file):
                        logger.warning(f"插件文件夹 {item} 缺少 __init__.py 文件")
                        continue
                    
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

    async def handle_new_messages(self):
        """处理新消息"""
        logger.debug('开始处理新消息...')
        messages = await self.extract_messages()
        
        # 如果需要自动发货
        if self.auto_ship_required:
            logger.info('检测到需要自动发货')
            if self.cur_shop_buy_success_replies:
                ship_text = f"【自动发货】: \n{self.cur_shop_buy_success_replies}"
                await self.send_message(ship_text)
                logger.info(f"已自动发货: {ship_text}")
            else:
                logger.warning('未设置自动发货内容')
                
        # 如果需要转人工
        if self.auto_notice_required:
            logger.info('检测到需要转人工客服')
            await self.send_message(f"已为您通知人工客服，请稍等...")
            asyncio.create_task(self.send_notice_msg(f"客户：{self.cur_user_name}:需要转人工"))
        
        # 检查是否有新消息需要处理
        if messages and len(messages) > 0:
            last_message = messages[-1]
            if last_message['role'] == 'user':
                # 使用插件链处理消息
                logger.info('检测到新的买家消息，准备处理')
                context = {
                    "messages": messages,
                    "is_payed": self.auto_ship_required,
                    "is_ship": False,  # 这里可以根据实际情况设置
                    "auto_ship_required": self.auto_ship_required,
                    "auto_notice_required": self.auto_notice_required
                }
                
                # 执行插件链
                message_handled = await self.execute_plugins_chain(last_message['content'], context)
                
                # 如果没有插件处理消息，且配置了AI回复，则使用AI回复
                if not message_handled and self.cur_plugins_config and "ai_reply" in self.cur_plugins_config:
                    logger.info('没有插件处理消息，使用AI回复')
                    reply = await self.get_gpt_reply(messages)
                    if reply:
                        await self.send_message(reply)
        
        logger.debug('消息处理完成')

    async def send_notice_msg(self, message):
        """发送通知消息
        
        Args:
            message: 通知消息内容
        """
        try:
            # 这里可以实现发送通知的逻辑，比如发送到钉钉、微信等
            logger.info(f"发送通知消息: {message}")
            # 示例：使用wxpusher发送通知
            if 'wxpusher' in sys.modules:
                try:
                    from wxpusher import WxPusher
                    WxPusher.send_message(message, uids=["UID_xxx"])
                    logger.info("通知消息已发送到WxPusher")
                except Exception as e:
                    logger.error(f"发送WxPusher通知失败: {e}")
        except Exception as e:
            logger.error(f"发送通知消息失败: {e}")


async def init_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS xianyu_shop (
            item_id TEXT PRIMARY KEY,
            shop_name TEXT,
            shop_price TEXT,
            shop_desc TEXT,
            shop_other TEXT,
            buy_success_replies TEXT,
            plugins_config TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成")


async def main():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch_persistent_context(
            headless=False,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled'],
            user_data_dir=user_data_dir,
            executable_path=executable_path,
        )
        page = await browser.new_page()

        # 监听请求
        chat_bot = ChatBot(page)
        
        # 异步加载插件
        try:
            await chat_bot.load_plugins()
            logger.info(f"插件加载成功，共 {len(chat_bot.plugins)} 个插件")
        except Exception as e:
            logger.error(f"加载插件失败: {e}")

        # 监听请求
        page.on("request", chat_bot.handle_request)
        page.on("response", chat_bot.handle_response)

        # 打开闲鱼
        await page.goto("https://www.goofish.com/im", wait_until="networkidle")

        # 初始化数据库
        await init_database()

        # 主循环
        last_refresh_time = time.time()
        refresh_interval = 12 * 60 * 60  # 12小时，单位：秒

        while True:
            try:
                current_time = time.time()
                if current_time - last_refresh_time >= refresh_interval:
                    logger.info('已运行12小时，准备刷新页面...')
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
                    logger.info('正在处理或回复消息，等待5秒后继续循环')
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
