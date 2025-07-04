from playwright.async_api import async_playwright
import os
import asyncio
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger()

# 配置
API_KEY = '0e1ec3fdad241a16189b54ef6de10e96.P951D07Cn2Cw7lIu'
API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'

# 用户数据目录和浏览器路径
user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")
executable_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 数据库路径
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "items.db")


async def send_message(page, message):
    log.info('开始发送消息...')

    # 无限循环直到找到文本区域
    while True:
        try:
            # 等待文本区域出现，设置超时时间为10秒
            textarea = await page.wait_for_selector('textarea.ant-input', timeout=10000)
            break  # 找到文本区域，跳出循环
        except asyncio.TimeoutError:
            log.info("未找到消息输入框，继续等待...")
            await asyncio.sleep(1)  # 等待1秒后再次尝试



    # 聚焦输入框
    await textarea.focus()

    # 处理字符串中的每个字符
    for char in message:
        if char == '\n':
            # 模拟 Shift + Enter
            await page.keyboard.down('Shift')
            await textarea.press('Enter')
            await page.keyboard.up('Shift')
        else:
            # 输入普通字符
            await textarea.type(char,delay=500)

    # 模拟最后的 Enter 键
    await textarea.press('Enter')

    # 模拟按下 Enter 键
    # await textarea.press('Enter')

    log.info(f'已尝试发送消息: {message}')



async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            headless=False,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled'],
            user_data_dir=user_data_dir,
            executable_path=executable_path,
        )
        page = await browser.new_page()
        await page.goto('https://www.goofish.com/im')  # 替换为实际的URL

        # 调用函数发送消息
        message = '''222
33333'''
        await send_message(page, message)



        # 防止退出
        input("123")
        # await browser.close()


asyncio.run(main())