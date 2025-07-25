import os
from time import sleep

from playwright.async_api import async_playwright
import logging
import requests
from urllib.parse import unquote
import re
import sqlite3
from collections import deque
import time
import aiohttp
import asyncio
from wxpusher import WxPusher

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(asctime)s - %(message)s')
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger()

# 是否开启Ai回复
open_chatai = False
# chatAi配置
API_KEY = '0e1ec3fdad241a16189b54ef6de10e96.P951D07Cn2Cw7lIu'
API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'

# 用户数据目录和浏览器路径
# user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data","可爱尼")
user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data", "大号")
executable_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 数据库路径
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fishbot.db")

# 自动发货内容匹配
auto_ship_text = '【自动发货】'

# 自动转人工客服
auto_notice_text = '转人工客服'

# 开启消息通知
open_notice_msg = True

# 钉钉机器人webhook
open_dingding = True
dingding_webhook = 'https://oapi.dingtalk.com/robot/send?access_token=5c22c63ba1a742a9a09eee52b551a02c6059230a777835e89e237b87306c63b4'
dingding_keyword = "【闲鱼助手】"

# 微信WxPusher 消息平台
open_wxpusher = True
wxpusher_uids = ["UID_DebxzN3NJVgefxEhL7FLq5tzPWbg"]
wxpusher_token = "AT_jQkJqc1f9R13kVVdjwxFNcG4pWLNerOq"


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
            log.debug(f"消息已发送过且未过期，跳过重复发送")
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
                log.info(f"钉钉机器人: {response_data}")  # 打印发送结果，但不阻塞后续逻辑

    # 微信wxpusher
    if open_wxpusher:
        response_data = WxPusher.send_message(f'{pre}\n {message}', uids=wxpusher_uids, token=wxpusher_token)
        log.info(f"微信wxpusher: {response_data}")  # 打印发送结果，但不阻塞后续逻辑

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
        self.cur_shop_name = None
        self.cur_shop_desc = None
        self.cur_shop_buy_success_replies = None
        # 当前商品是否开启AI回复
        self.cur_shop_enable_ai_reply = True
        self.is_processing_message = False
        self.current_conversation_id = None

    async def wait_for_messages(self):
        log.debug('等待消息加载...')
        for _ in range(10):
            # message_rows = await self.page.query_selector_all('[class^="message-row"]')
            message_rows = await self.page.query_selector_all('[class^="ant-dropdown-trigger"]')
            if message_rows:
                log.debug('消息已加载')
                return True
            await asyncio.sleep(1)
        log.debug('等待消息加载超时')
        return False

    async def check_and_reply_new_messages(self):
        if self.is_replying or self.is_processing_message:
            log.debug('正在处理或回复消息，跳过本次检查')
            return

        if not await self.wait_for_messages():
            log.debug('无法加载消息，跳过本次回复')
            return

        # 当前用户
        cur_user = await self.page.query_selector('[class^="text1"]')
        if not cur_user:
            log.debug('未找到当前用户信息，跳过本次回复')
            return
        self.cur_user_name = await cur_user.text_content()

        # 异步获取商品信息，设置超时时间为5秒
        try:
            async with asyncio.timeout(5):
                while not self.is_get_shop:
                    log.debug("等待获取商品信息...")
                    await asyncio.sleep(1)
        except asyncio.TimeoutError:
            log.warning("获取商品信息超时，跳过本次回复")
            return

        if not self.cur_shop_desc:
            log.debug("未获取到商品信息，跳过本次回复")
            return

        self.is_processing_message = True
        self.is_replying = True

        # 开始提取消息内容
        messages = await self.extract_messages()
        if messages:
            last_message = messages[-1]
            if last_message['role'] == 'user':
                # ai回复 如果是自动发货则不需要回复
                if self.cur_shop_enable_ai_reply and not self.auto_ship_required:
                    log.info('检测到新的买家消息，准备回复')
                    reply = await self.get_gpt_reply(messages)
                    await self.send_message(reply)

                # 钉钉通知闲鱼消息
                if open_notice_msg:
                    asyncio.create_task(send_notice_msg(pre=f"客户：{self.cur_user_name}\n", message=messages))

        # 是否需要自动发货
        # if True:
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
            log.info('正在处理或回复消息，跳过本次检查')
            return

        log.info('开始监控新消息...')
        chat_container = await self.page.query_selector('div.message-list--tD5r4eck#message-list-scrollable')
        if not chat_container:
            log.info('未找到聊天容器，无法监控新消息')
            return

        self.current_conversation_id = await self.get_current_conversation_id()
        log.info(f'新消息监控已成功启动，当前对话ID: {self.current_conversation_id}')

        # 立即检查一次，以防有未回复的消息
        await self.check_and_reply_new_messages()

    async def check_new_message_badge(self):
        if self.is_replying or self.is_processing_message:
            log.info('正在处理或回复消息，跳过检查新消息角标')
            return False

        log.debug('检查新消息角标...')
        # 标签.标签下的 类class1.类class2
        # <span class="ant-scroll-number-only-unit current">4</span>
        # span.ant-scroll-number-only-unit.current
        # unread_badge = await self.page.query_selector('span.ant-scroll-number-only-unit.current') # 已过时
        # 找到角标元素 右击元素 复制 -> 复制selector
        # unread_badge = await self.page.query_selector('#conv-list-scrollable > div > div.rc-virtual-list-holder > div > div > div:nth-child(1) > div > div > div.ant-dropdown-trigger > div:nth-child(1) > div:nth-child(1) > span > sup')
        unread_badge = await self.page.query_selector('#conv-list-scrollable .rc-virtual-list-holder div.ant-dropdown-trigger span sup')
        if unread_badge:
            log.debug(f'找到消息角标，待回复消息数量: {await unread_badge.text_content()}')
            if await unread_badge.text_content() != '0':
                log.info('检测到新消息，尝试点击角标...')
                await self.click_badge(unread_badge)
                return True
        else:
            log.debug('未找到消息角标元素')
        return False

    async def click_badge(self, badge):
        clickable_element = await badge.query_selector('a, button, *')
        # clickable_element = await badge.query_selector(f'xpath=/html/body/div[2]/div[2]/div/div/aside/div/div[2]/div/div[1]/div/div/div[1]/div/div/div[1]/div[1]/div[2]')
        if clickable_element:
            log.debug('找到可点击元素，模拟点击...')
            await clickable_element.click()
            log.debug('已模拟点击操作')
            await asyncio.sleep(2)
            await self.check_and_reply_new_messages()
        else:
            log.warning('未找到与角标关联的可点击元素')



    async def extract_messages(self):
        log.debug('开始提取消息内容...')
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
        log.info('开始发送消息...')
        textarea = await self.page.query_selector('textarea.ant-input')
        if not textarea:
            log.warning('未找到消息输入框')
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

        log.info(f'已尝试发送消息: {message}')

    async def get_gpt_reply(self, messages):
        log.debug('调用 GPT 接口获取回复...')
        system_message = {
            "role": "system",
            "content": f"""不需要引导语句。不需要任何前缀。
            你现在的身份是闲鱼二手交易平台的卖家，你需要尽可能模仿真实的人回答客户的问题，并吸引客户下单，你需要根据商品介绍回答问题，需要简洁的回答
            商品价格：{self.cur_shop_price}
            商品介绍：{self.cur_shop_desc}
            其他说明：{self.cur_shop_other}
            """
        }
        all_messages = [system_message, *messages]

        try:
            response = requests.post(
                API_URL,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {API_KEY}'
                },
                json={
                    "model": "GLM-4-Flash",
                    "messages": all_messages
                }
            )
            response.raise_for_status()  # 检查请求是否成功
            data = response.json()
            reply = data.get('choices', [{}])[0].get('message', {}).get('content', '无法获取回复')
            log.info(f'GPT 回复: {reply}')
            return reply
        except requests.RequestException as e:
            log.error(f'请求 GPT 接口失败: {e}')
            return "无法获取回复"

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
                log.warning("未找到目标元素，请检查 XPath 是否正确。")
                return None, None, None
        except Exception as e:
            log.error(f"获取元素时出错: {e}")
            return None, None, None
        finally:
            await page.close()

    async def handle_request_get_context(self, request):
        log.debug("获取商品介绍")
        if request.method == "POST" and request.post_data:
            decoded_post_data = unquote(request.post_data)
            log.debug(f"POST URL: {request.url} 请求参数: {decoded_post_data}")

            # 使用正则表达式提取 itemId
            match = re.search(r'"itemId":(\d+)', decoded_post_data)
            if match:
                item_id = match.group(1)  # 提取匹配到的数字部分
                log.debug(f"提取到的 itemId: {item_id}")
                self.cur_item_id = item_id

                # 检查数据库中是否有该商品信息
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT shop_name, shop_price, shop_desc, shop_other, buy_success_replies, enable_ai_reply FROM xianyu_shop WHERE item_id = ?", (item_id,))
                result = cursor.fetchone()
                conn.close()

                shop_name, shop_price, shop_desc, shop_other, buy_success_replies, enable_ai_reply = None, None, None, None, None, 1
                if result:
                    shop_name, shop_price, shop_desc, shop_other, buy_success_replies, enable_ai_reply = result
                    log.info(f"从数据库中获取到的商品信息：{shop_name}, {shop_desc}, AI回复：{'开启' if enable_ai_reply else '关闭'}")
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
                            logging.info(f"打开详情页 id：{item_id} 商品：{shop_name} 商品介绍：{shop_desc}")
                        else:
                            log.error(f"获取商品信息失败：id：{item_id} 无法获取商品详情")
                            shop_name, shop_price, shop_desc, shop_other = None, None, None, None
                    except Exception as e:
                        log.error(f"获取商品信息失败：id：{item_id}  error:{e}")
                        shop_name, shop_price, shop_desc, shop_other = None, None, None, None

                    # 保存到数据库中
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                            INSERT INTO xianyu_shop (item_id, shop_name, shop_price, shop_desc, enable_ai_reply) 
                            VALUES (?, ?, ?, ?, ?) 
                            ON CONFLICT(item_id) 
                            DO UPDATE SET shop_name = excluded.shop_name, shop_desc = excluded.shop_desc
                        """, (item_id, shop_name, shop_price, shop_desc, 1))
                    conn.commit()
                    conn.close()
                    log.info(f"商品信息已保存到数据库：id={item_id}, 名称={shop_name}, 描述={shop_desc}")

                self.is_get_shop = True
                self.cur_shop_name = shop_name
                self.cur_shop_price = shop_price
                self.cur_shop_desc = shop_desc
                self.cur_shop_other = shop_other
                self.cur_shop_buy_success_replies = buy_success_replies
                self.cur_shop_enable_ai_reply = bool(enable_ai_reply)
            else:
                log.warning("未提取到 itemId，请检查正则表达式是否正确。")

    async def handle_request(self, request):
        request_handlers = {
            "mtop.idle.trade.pc.message.headinfo": self.handle_request_get_context,
            # "another_request_feature": handle_request_B,
        }

        for feature, handler in request_handlers.items():
            if feature in request.url:
                await handler(request)  # 调用对应的处理方法
                break
        else:
            log.debug(f"未匹配到任何处理逻辑的请求: {request.url}")

    async def handle_response(self, response):
        # 打印响应信息
        log.info(f"Response: {response.status} {response.url}")
        # 如果需要，可以查看响应内容
        # response.text().then(print)


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
            enable_ai_reply INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    log.info("数据库初始化完成")


async def main():
    await init_database()  # 初始化数据库

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            headless=False,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled'],
            user_data_dir=user_data_dir,
            executable_path=executable_path,
        )
        page = await browser.new_page()

        chat_bot = ChatBot(page)

        # 监听请求
        page.on("request", chat_bot.handle_request)
        # page.on("response", chat_bot.handle_response)

        # 记录上次刷新时间
        last_refresh_time = time.time()
        # 12小时的秒数
        refresh_interval = 12 * 60 * 60
        # refresh_interval = 0

        await page.goto('https://www.goofish.com/im')
        # await page.goto('https://www.goofish.com/login')

        while True:
            try:
                # 检查是否需要刷新页面
                current_time = time.time()
                if current_time - last_refresh_time >= refresh_interval:
                    log.info('已运行12小时，准备刷新页面...')
                    # 模拟按下 F5 键
                    await page.evaluate("location.reload()")
                    await asyncio.sleep(10)  # 等待页面加载完成
                    last_refresh_time = current_time

                    # # 自动登录
                    # # 尝试等待登录弹窗中的登录按钮
                    # async def click_login_button(page):
                    #     try:
                    #         # 这里可能需要调整选择器以匹配实际的登录按钮
                    #         await page.wait_for_selector('#login .fm-btn button', timeout=2000)
                    #         clickable_element = await page.query_selector('#login .fm-btn button')
                    #
                    #         if clickable_element:
                    #             log.debug('找到登录按钮，模拟点击...')
                    #             await clickable_element.click()
                    #
                    #             # 等待页面加载完成
                    #             await page.wait_for_load_state('networkidle')
                    #             log.debug('已模拟点击登录操作')
                    #         else:
                    #             log.warning('未找到与登录可点击元素')
                    #     except Exception as e:
                    #         log.error(f'捕获元素超时或发生错误: {e}')
                    #         raise  # 重新抛出异常以便外层捕获
                    #
                    # max_retries = 3  # 最大重试次数
                    # retries = 0
                    #
                    # while retries < max_retries:
                    #     try:
                    #         await click_login_button(page)
                    #         break  # 如果成功点击，则退出循环
                    #     except Exception as e:
                    #         retries += 1
                    #         log.warning(f'第 {retries} 次重试失败，尝试重新点击登录按钮')
                    #         await asyncio.sleep(1)  # 等待1秒后重试
                    #
                    # if retries == max_retries:
                    #     log.error('达到最大重试次数，无法完成登录操作')
                    #

                    log.info('页面刷新完成')
                    continue

                log.debug('开始新的检查循环')
                if chat_bot.is_replying or chat_bot.is_processing_message:
                    log.info('正在处理或回复消息，等待5秒后继续循环')
                    await asyncio.sleep(5)
                    continue

                try:
                    conversation_open = await page.query_selector('#message-list-scrollable')
                    if conversation_open:
                        log.debug('检测到打开的对话框')
                        await chat_bot.check_and_reply_new_messages()

                        if not chat_bot.is_replying and not chat_bot.is_processing_message:
                            log.debug('当前对话没有新消息，检查其他对话的红点')
                            await chat_bot.check_new_message_badge()
                    else:
                        log.debug('当前没有打开的对话框，检查新消息红点')
                        await chat_bot.check_new_message_badge()
                except Exception as e:
                    log.error(f"处理消息时发生错误: {e}")
                    await asyncio.sleep(3)  # 出错后等待一小段时间
                    continue

            except Exception as e:
                log.error(f"主循环发生错误: {e}")
                await asyncio.sleep(5)  # 发生错误时等待较长时间
                continue

            log.debug('等待3秒后继续下一次循环')
            await asyncio.sleep(3)


if __name__ == '__main__':
    asyncio.run(main())
