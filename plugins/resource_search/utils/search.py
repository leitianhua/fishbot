import requests
import re
import logging
from typing import List, Dict, Any, Optional
from loguru import logger  # 替换为loguru
from bs4 import BeautifulSoup


class ResourceSearch:
    """资源搜索类，用于从多个来源搜索网盘资源"""

    def __init__(self):
        """初始化资源搜索类
        """
        # 通用请求头
        self.quark_headers = {
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'sec-ch-ua-mobile': '?0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'origin': 'https://pan.quark.cn',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://pan.quark.cn/',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9'
        }
        
        self.waliso_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-length': '147',
            'content-type': 'application/json',
            'origin': 'https://waliso.com',
            'priority': 'u=1, i',
            'referer': 'https://waliso.com/',
            'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }

        self.ppqa_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'referer': 'https://ppqa.cn/',
            'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site'
        }



    def search_source1(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索来源1 - 从kkkob.com获取资源
        Args:
            keyword: 搜索关键词
        Returns:
            list: 搜索结果列表
        """
        url_default = "http://s.kkkob.com"
        items_json = []
        
        try:
            logger.info(f"搜索来源1: {keyword}")
            
            # 获取token
            token_response = requests.get(f"{url_default}/v/api/getToken", headers=self.quark_headers, timeout=5)
            if token_response.status_code != 200:
                logger.warning(f"搜索来源1获取token失败: {token_response.status_code}")
                return items_json
                
            token_data = token_response.json()
            token = token_data.get('token', '')
            
            if not token:
                logger.warning("搜索来源1获取token为空")
                return items_json
                
            logger.info(f"搜索来源1获取token成功: {token[:10]}...")
            
            # 准备搜索数据
            search_data = {
                'name': keyword,
                'token': token
            }
            search_headers = {
                'Content-Type': 'application/json'
            }
            
            # 定义正则表达式模式
            pattern = r'https://pan\.quark\.cn/[^\s]*'
            
            # 尝试线路2
            logger.info("搜索来源1尝试线路2")
            juzi_response = requests.post(
                f"{url_default}/v/api/getJuzi", 
                json=search_data, 
                headers=search_headers, 
                timeout=5
            )
            
            if juzi_response.status_code == 200:
                juzi_data = juzi_response.json()
                if juzi_data.get('list'):
                    for item in juzi_data['list']:
                        if re.search(pattern, item.get('answer', '')):
                            match = re.search(pattern, item['answer'])
                            if match:
                                link = match.group(0)
                                title = re.sub(r'\s*[\(（]?(夸克)?[\)）]?\s*', '', item.get('question', ''))
                                
                                logger.info(f"搜索来源1线路2找到资源: {title}")
                                logger.info(f"搜索来源1线路2找到链接: {link}")
                                
                                items_json.append({
                                    'title': title,
                                    'url': link
                                })
                                break
            
            # 如果线路2没有结果，尝试线路4
            if not items_json:
                logger.info("搜索来源1尝试线路4")
                xiaoyu_response = requests.post(
                    f"{url_default}/v/api/getXiaoyu", 
                    json=search_data, 
                    headers=search_headers, 
                    timeout=5
                )
                
                if xiaoyu_response.status_code == 200:
                    xiaoyu_data = xiaoyu_response.json()
                    if xiaoyu_data.get('list'):
                        for item in xiaoyu_data['list']:
                            if re.search(pattern, item.get('answer', '')):
                                match = re.search(pattern, item['answer'])
                                if match:
                                    link = match.group(0)
                                    title = re.sub(r'\s*[\(（]?(夸克)?[\)）]?\s*', '', item.get('question', ''))
                                    
                                    logger.info(f"搜索来源1线路4找到资源: {title}")
                                    logger.info(f"搜索来源1线路4找到链接: {link}")
                                    
                                    items_json.append({
                                        'title': title,
                                        'url': link
                                    })
                                    break
            
        except Exception as e:
            logger.error(f"搜索来源1失败: {e}")
        
        # 记录最终的有效记录数量和内容
        logger.info(f"搜索来源1过滤后: 得到{len(items_json)}条有效记录")
        for index, item in enumerate(items_json):
            logger.info(f"搜索来源1最终结果[{index}]: 标题={item['title']}, URL={item['url']}")
        
        return items_json

    def search_source2(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索来源2
        Args:
            keyword: 搜索关键词
        Returns:
            list: 搜索结果列表
        """
        url = "https://www.hhlqilongzhu.cn/api/ziyuan_nanfeng.php"
        params = {"keysearch": keyword}
        items_json = []
        
        try:
            logger.info(f"搜索来源2: {keyword}")
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                total_items = len(data.get("data", []))
                logger.info(f"搜索来源2结果: 状态码={response.status_code}, 总共{total_items}条记录")
                
                if data.get("data") and isinstance(data.get("data"), list) and len(data.get("data")) > 0:
                    for index, item in enumerate(data['data']):
                        logger.info(f"搜索来源2原始数据[{index}]: {item}")
                        if ('quark' in str(item) or 'baidu' in str(item)):
                            title = item.get('title', '未知标题').strip()
                            data_url = item.get('data_url', '')
                            url = None
                            
                            # 尝试从百度网盘链接中提取URL
                            if 'pan.baidu.com' in data_url:
                                # 正则表达式匹配百度网盘链接
                                baidu_match = re.search(r'(https?://pan\.baidu\.com/s/[\w-]+)', data_url)
                                if baidu_match:
                                    url = baidu_match.group(1)
                            # 尝试从夸克网盘链接中提取URL
                            elif 'pan.quark.cn' in data_url:
                                # 正则表达式匹配夸克网盘链接
                                quark_match = re.search(r'(https?://pan\.quark\.cn/s/[\w-]+)', data_url)
                                if quark_match:
                                    url = quark_match.group(1)
                            
                            # 检查是否成功提取URL
                            if url and url.startswith('http'):
                                logger.info(f"搜索来源2提取链接[{index}]: {url}")
                                logger.info(f"搜索来源2提取标题[{index}]: {title}")
                                
                                item_dict = {
                                    'title': title,
                                    'url': url
                                }
                                items_json.append(item_dict)
                                if len(items_json) >= 5:
                                    logger.info("搜索来源2已达到5条记录上限，停止处理")
                                    break
                            else:
                                logger.warning(f"搜索来源2记录解析失败[{index}]: 无法提取有效URL")
                        else:
                            logger.info(f"搜索来源2记录不包含夸克或百度链接[{index}]")
            else:
                logger.warning(f"搜索来源2响应状态码异常: {response.status_code}")
        except Exception as e:
            logger.error(f"搜索来源2失败: {e}")
        
        # 记录最终的有效记录数量和内容
        logger.info(f"搜索来源2过滤后: 得到{len(items_json)}条有效记录")
        for index, item in enumerate(items_json):
            logger.info(f"搜索来源2最终结果[{index}]: 标题={item['title']}, URL={item['url']}")
        
        return items_json

    def search_source3(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索来源3
        Args:
            keyword: 搜索关键词
        Returns:
            list: 搜索结果列表
        """
        url = "https://api.upyunso.com/search"
        params = {"keyword": keyword, "page": 1, "s_type": "all"}
        items_json = []
        
        try:
            logger.info(f"搜索来源3: {keyword}")
            # 禁用SSL证书验证
            response = requests.get(url, params=params, timeout=5, verify=False)
            if response.status_code == 200:
                data = response.json()
                total_items = len(data.get("result", {}).get("items", []))
                logger.info(f"搜索来源3结果: 状态码={response.status_code}, 总共{total_items}条记录")
                
                if data.get("result") and data["result"].get("items"):
                    for index, item in enumerate(data["result"]["items"]):
                        logger.info(f"搜索来源3原始数据[{index}]: {item}")
                        if item.get("url") and ('quark' in item["url"] or 'baidu' in item["url"]):
                            title = item.get("title", "未知标题")
                            url = item["url"]
                            logger.info(f"搜索来源3提取链接[{index}]: {url}")
                            logger.info(f"搜索来源3提取标题[{index}]: {title}")
                            
                            item_dict = {
                                'title': title,
                                'url': url
                            }
                            items_json.append(item_dict)
                            if len(items_json) >= 5:
                                logger.info("搜索来源3已达到5条记录上限，停止处理")
                                break
                        else:
                            logger.info(f"搜索来源3记录不包含夸克或百度链接[{index}]")
            else:
                logger.warning(f"搜索来源3响应状态码异常: {response.status_code}")
        except Exception as e:
            logger.error(f"搜索来源3失败: {e}")
        
        # 记录最终的有效记录数量和内容
        logger.info(f"搜索来源3过滤后: 得到{len(items_json)}条有效记录")
        for index, item in enumerate(items_json):
            logger.info(f"搜索来源3最终结果[{index}]: 标题={item['title']}, URL={item['url']}")
        
        return items_json

    def search_source4(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索来源4
        Args:
            keyword: 搜索关键词
        Returns:
            list: 搜索结果列表
        """
        url = "https://www.xiaoso.net/api/search"
        params = {"keyword": keyword}
        items_json = []
        
        try:
            logger.info(f"搜索来源4: {keyword}")
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                total_items = len(data.get("result", {}).get("items", []))
                logger.info(f"搜索来源4结果: 状态码={response.status_code}, 总共{total_items}条记录")
                
                if data.get("result") and data["result"].get("items"):
                    for index, item in enumerate(data["result"]["items"]):
                        logger.info(f"搜索来源4原始数据[{index}]: {item}")
                        if item.get("url") and ('quark' in item["url"] or 'baidu' in item["url"]):
                            title = item.get("title", "未知标题")
                            url = item["url"]
                            logger.info(f"搜索来源4提取链接[{index}]: {url}")
                            logger.info(f"搜索来源4提取标题[{index}]: {title}")
                            
                            item_dict = {
                                'title': title,
                                'url': url
                            }
                            items_json.append(item_dict)
                            if len(items_json) >= 5:
                                logger.info("搜索来源4已达到5条记录上限，停止处理")
                                break
                        else:
                            logger.info(f"搜索来源4记录不包含夸克或百度链接[{index}]")
            else:
                logger.warning(f"搜索来源4响应状态码异常: {response.status_code}")
        except Exception as e:
            logger.error(f"搜索来源4失败: {e}")
        
        # 记录最终的有效记录数量和内容
        logger.info(f"搜索来源4过滤后: 得到{len(items_json)}条有效记录")
        for index, item in enumerate(items_json):
            logger.info(f"搜索来源4最终结果[{index}]: 标题={item['title']}, URL={item['url']}")
        
        return items_json

    def search_source5(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索来源5 - 瓦力搜索
        Args:
            keyword: 搜索关键词
        Returns:
            list: 搜索结果列表
        """
        url = "https://api.waliso.com/api/search/resources"
        payload = {
            "keyword": keyword,
            "page": 1,
            "size": 10,
            "site": "",
            "format": "",
            "time": "",
            "accurate": False
        }
        items_json = []
        
        try:
            logger.info(f"搜索来源5: {keyword}")
            response = requests.post(url, json=payload, headers=self.waliso_headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200 and data.get("data") and data["data"].get("list"):
                    total_items = len(data["data"]["list"])
                    logger.info(f"搜索来源5结果: 状态码={response.status_code}, 总共{total_items}条记录")
                    
                    for index, item in enumerate(data["data"]["list"]):
                        logger.info(f"搜索来源5原始数据[{index}]: {item}")
                        if item.get("url") and ('quark' in item["url"] or 'baidu' in item["url"]):
                            title = item.get("name", "未知标题")
                            url = item["url"]
                            logger.info(f"搜索来源5提取链接[{index}]: {url}")
                            logger.info(f"搜索来源5提取标题[{index}]: {title}")
                            
                            item_dict = {
                                'title': title,
                                'url': url
                            }
                            items_json.append(item_dict)
                            if len(items_json) >= 5:
                                logger.info("搜索来源5已达到5条记录上限，停止处理")
                                break
                        else:
                            logger.info(f"搜索来源5记录不包含夸克或百度链接[{index}]")
                else:
                    logger.warning(f"搜索来源5响应数据异常: {data.get('message', '未知错误')}")
            else:
                logger.warning(f"搜索来源5响应状态码异常: {response.status_code}")
        except Exception as e:
            logger.error(f"搜索来源5失败: {e}")
        
        # 记录最终的有效记录数量和内容
        logger.info(f"搜索来源5过滤后: 得到{len(items_json)}条有效记录")
        for index, item in enumerate(items_json):
            logger.info(f"搜索来源5最终结果[{index}]: 标题={item['title']}, URL={item['url']}")
        
        return items_json

    def search_source6(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索来源6 - PPQA搜索
        Args:
            keyword: 搜索关键词
        Returns:
            list: 搜索结果列表
        """
        url = "https://api.ppqa.cn/api/pan/search"
        params = {
            "keyword": keyword,
            "ckey": "I66IONQVOWDF8YG68AF8",
            "type": "夸克网盘",
            "fromSite": "kk短剧2"
        }
        items_json = []
        
        try:
            logger.info(f"搜索来源6: {keyword}")
            response = requests.get(url, params=params, headers=self.ppqa_headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    total_items = len(data["data"])
                    logger.info(f"搜索来源6结果: 状态码={response.status_code}, 总共{total_items}条记录")
                    
                    for index, item in enumerate(data["data"]):
                        logger.info(f"搜索来源6原始数据[{index}]: {item}")
                        if item.get("url"):
                            # 修正URL中可能存在的问题（移除结尾的 >）
                            url = item["url"].replace('\">', '')
                            title = item.get("name", "未知标题")
                            pwd = item.get("pwd", "")  # 获取提取码
                            
                            logger.info(f"搜索来源6提取链接[{index}]: {url}")
                            logger.info(f"搜索来源6提取标题[{index}]: {title}")
                            logger.info(f"搜索来源6提取码[{index}]: {pwd}")
                            
                            item_dict = {
                                'title': title,
                                'url': url
                            }
                            
                            # 如果有提取码，添加到结果中
                            if pwd:
                                item_dict['pwd'] = pwd
                                
                            items_json.append(item_dict)
                            if len(items_json) >= 5:
                                logger.info("搜索来源6已达到5条记录上限，停止处理")
                                break
                        else:
                            logger.info(f"搜索来源6记录不包含有效URL[{index}]")
                else:
                    logger.warning(f"搜索来源6响应数据异常: {data.get('message', '未知错误')}")
            else:
                logger.warning(f"搜索来源6响应状态码异常: {response.status_code}")
        except Exception as e:
            logger.error(f"搜索来源6失败: {e}")
        
        # 记录最终的有效记录数量和内容
        logger.info(f"搜索来源6过滤后: 得到{len(items_json)}条有效记录")
        for index, item in enumerate(items_json):
            pwd_info = f", 提取码={item.get('pwd', '无')}" if 'pwd' in item else ""
            logger.info(f"搜索来源6最终结果[{index}]: 标题={item['title']}, URL={item['url']}{pwd_info}")
        
        return items_json 