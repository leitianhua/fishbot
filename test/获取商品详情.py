from playwright.sync_api import sync_playwright

def extract_element_content(url, selector):
    """
    使用 Playwright 访问目标网址并提取指定元素的内容。

    :param url: 目标网址
    :param selector: 目标元素的选择器（XPath 或 CSS 选择器）
    """
    with sync_playwright() as p:
        # 启动浏览器（无头模式）
        browser = p.chromium.launch(headless=False)  # headless=True 表示无头模式
        page = browser.new_page()

        # 设置用户代理
        page.context.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })

        # 访问目标网址
        print(f"正在访问目标网址: {url}")
        page.goto(url)

        # 等待页面加载完成
        print("等待页面加载完成...")
        page.wait_for_load_state("networkidle")  # 等待网络空闲

        # 等待目标元素加载完成
        page.wait_for_load_state("networkidle")  # 等待网络空闲

        # 使用 XPath 定位目标元素
        try:
            element = page.query_selector(xpath)
            if element:
                text_content = element.text_content()
                print("获取到的文本内容:", text_content)
            else:
                print("未找到目标元素，请检查 XPath 是否正确。")
        except Exception as e:
            print("获取元素时出错:", e)

        # 关闭浏览器
        browser.close()

if __name__ == "__main__":
    # 目标网址和目标元素的选择器
    target_url = "https://www.goofish.com/item?id=799378236525&categoryId=0"
    xpath = '//*[@id="content"]/div[1]/div[2]/div[2]/div[3]/div[1]/div/span'

    # 调用函数提取内容
    extract_element_content(target_url, xpath)