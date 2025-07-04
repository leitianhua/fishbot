#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
资源搜索核心模块
"""

import os
import re
import time
import threading
import tomllib
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

# 导入工具类（使用绝对导入）
from utils.search import ResourceSearch
from utils.quark import Quark
from utils.baidu import Baidu
from utils.database import get_db_instance

class ResourceCore:
    """资源搜索核心类"""
    
    def __init__(self, plugin_dir=None):
        """初始化核心类
        
        Args:
            plugin_dir: 插件目录路径，默认为None（自动获取）
        """
        # 获取当前模块所在目录
        self.utils_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 获取插件目录
        if plugin_dir is None:
            self.plugin_dir = os.path.dirname(self.utils_dir)
        else:
            self.plugin_dir = plugin_dir
            
        # 初始化配置
        self.conf = None
        
        # 初始化数据库管理器
        self.db = get_db_instance()
        
        # 加载配置
        self._load_config()
        
        # 如果配置加载成功，初始化清理线程
        if self.conf:
            # 从配置中获取过期时间
            general_conf = self.conf.get("general", {})
            self.expired_time = general_conf.get("expired_time", 30)
            
            # 开启一个线程每分钟清除过期资源
            self.clear_expired_resources_thread = threading.Thread(target=self.clear_expired_resources)
            self.clear_expired_resources_thread.daemon = True  # 设置为守护线程
            self.clear_expired_resources_thread.start()
            
            logger.info("资源搜索核心初始化成功")
        else:
            logger.error("资源搜索核心初始化失败，配置未加载")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 获取配置文件路径 - 改为从utils目录下加载
            config_path = os.path.join(self.utils_dir, "config.toml")
            logger.debug(f"加载配置文件: {config_path}")
            
            # 读取配置文件
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                
            # 验证配置
            if not config:
                logger.error("配置文件为空")
                return
                
            # 获取并验证夸克账号配置
            quark_accounts = config.get("accounts", {}).get("quark", [])
            if not quark_accounts:
                logger.error("未配置夸克账号，插件无法正常工作")
                return
                
            # 验证每个夸克账号
            valid_quark_accounts = []
            for account in quark_accounts:
                cookie = account.get("cookie")
                if not cookie:
                    logger.warning("夸克账号缺少cookie")
                    continue
                    
                if self._verify_quark_account(cookie):
                    valid_quark_accounts.append(account)
                else:
                    logger.warning("夸克账号验证失败")
            
            if not valid_quark_accounts:
                logger.error("没有有效的夸克账号，插件无法正常工作")
                return
                
            # 更新配置中的有效账号
            config["accounts"]["quark"] = valid_quark_accounts
            
            # 保存配置
            self.conf = config
            logger.info("资源搜索配置加载成功")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    def _verify_quark_account(self, cookie):
        """验证夸克网盘账号是否有效
        
        Args:
            cookie: 夸克网盘cookie
            
        Returns:
            bool: 账号是否有效
        """
        try:
            # 构建请求头
            headers = {
                'authority': 'pan.quark.cn',
                'accept': 'application/json, text/plain, */*',
                'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Microsoft Edge";v="114"',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.67',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-site': 'same-site',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'referer': 'https://pan.quark.cn/',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'zh-CN,zh;q=0.9',
                'cookie': cookie
            }
            
            # 调用获取账户信息的API
            import requests
            url = "https://pan.quark.cn/account/info"
            params = {"fr": "pc", "platform": "pc"}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            account_info = response.json()
            
            # 检查响应中是否包含账户信息
            if account_info and account_info.get("data"):
                nickname = account_info["data"].get("nickname", "")
                logger.info(f"夸克网盘账号: {nickname}")
                return True
            else:
                logger.error(f"夸克网盘账号验证失败: {account_info.get('message', '未知错误')}")
                return False
        except Exception as e:
            logger.error(f"验证夸克账号时发生错误: {str(e)}")
            return False
    
    # 每分钟清除过期资源
    def clear_expired_resources(self):
        """清除过期资源的线程函数"""
        while True:
            try:
                quark = Quark(self.conf)
                quark.del_expired_resources(self.expired_time)
                time.sleep(60)  # 每分钟执行一次
            except Exception as e:
                logger.error(f"清除过期资源失败: {e}")
                time.sleep(60)
    
    def search_and_store(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索资源并转存到网盘
        
        Args:
            keyword: 搜索关键词
            limit: 最大结果数量，默认为5
            
        Returns:
            包含转存后资源信息的列表，每项包含:
            - title: 资源标题
            - url: 资源链接
            - is_time: 是否为临时资源(1为是)
        """
        if not self.conf:
            logger.error("配置未加载，无法执行搜索")
            return []
            
        # 获取配置
        general_conf = self.conf.get("general", {})
        search_timeout = general_conf.get("search_timeout", 10)  # 默认10秒超时
        max_threads = general_conf.get("max_search_threads", 0)  # 默认不限制线程数
        
        logger.info(f'搜索关键字: {keyword}，最大结果数: {limit}，超时: {search_timeout}秒')
        start_time = time.time()
        
        # 创建资源搜索对象
        rs = ResourceSearch()
        
        # 自动获取所有搜索方法（以search_source开头的方法）
        all_search_methods = []
        for method_name in dir(rs):
            if method_name.startswith('search_source') and callable(getattr(rs, method_name)):
                all_search_methods.append(method_name)
        
        # 根据配置启用或禁用搜索源
        sources_config = self.conf.get("sources", {})
        enabled_methods = []
        
        for method in all_search_methods:
            # 提取源编号（例如从search_source1中提取1）
            source_num = method.replace("search_source", "")
            # 检查配置是否启用该源
            if sources_config.get(f"source{source_num}", True):
                enabled_methods.append(method)
            else:
                logger.info(f"搜索源{source_num}已禁用: {method}")
        
        logger.info(f"检测到{len(all_search_methods)}个搜索源，启用{len(enabled_methods)}个: {', '.join(enabled_methods)}")
        
        # 使用线程池并行搜索，支持最大线程数控制
        thread_count = max_threads if max_threads > 0 else None
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # 创建带超时的任务
            future_to_method = {
                executor.submit(self._search_with_timeout, rs, method, keyword, search_timeout): method
                for method in enabled_methods
            }
            
            # 收集结果
            all_results = []
            for future in ThreadPoolExecutor().map(lambda f: (f, f.result()), future_to_method):
                future_obj, results = future
                method = future_to_method[future_obj]
                if isinstance(results, Exception):
                    logger.error(f"搜索源 {method} 发生错误: {results}")
                    continue
                if results:
                    logger.info(f"搜索源 {method} 返回 {len(results)} 条结果")
                    all_results.extend(results)
                else:
                    logger.debug(f"搜索源 {method} 未返回结果")
        
        # 创建转存工具
        quark = Quark(self.conf)
        baidu = Baidu(self.conf)
        
        # 存储结果
        unique_results = []
        count = 0
        
        # 处理搜索结果
        for item in all_results:
            # 限制结果数量
            if count >= limit:
                logger.debug(f"结果已达到{limit}条上限，停止处理")
                break
                
            url = item.get('url')
            if not url:
                logger.debug(f"跳过没有URL的项: {item}")
                continue
            
            logger.debug(f"处理搜索结果: {item.get('title', '未知')} - {url}")
                
            try:
                file_not_exist = False
                file_name = ''
                share_link = ''
                
                # 根据链接类型选择相应的网盘处理
                if 'quark' in url:
                    logger.info(f"转存夸克链接: {url}")
                    file_not_exist, file_name, share_link = quark.store(url)
                elif 'baidu' in url:
                    logger.info(f"转存百度链接: {url}")
                    # 如果需要支持百度网盘
                    # file_not_exist, file_name, share_link = baidu.store(url)
                    continue
                else:
                    logger.warning(f"未知链接类型，跳过: {url}")
                    continue
                    
                # 如果成功处理，添加到结果
                if file_name and share_link:
                    logger.info(f'{"新转存" if file_not_exist else "已存在"}: {file_name} - {share_link}')
                    item['title'] = file_name
                    item['url'] = share_link
                    item['is_time'] = 1
                    unique_results.append(item)
                    count += 1
                else:
                    logger.warning(f"链接处理结果不完整: file_name={file_name}, share_link={share_link}")
                    
            except Exception as e:
                logger.error(f'转存失败 "{item.get("title", "未知")}" {url}: {e}')
                continue
        
        # 记录搜索历史
        self.db.record_search(keyword, len(unique_results))
        
        # 记录执行时间
        execution_time = time.time() - start_time
        logger.info(f"搜索执行耗时: {execution_time:.2f} 秒, 找到结果: {len(unique_results)}")
        
        return unique_results
    
    def _search_with_timeout(self, search_obj, method_name, keyword, timeout):
        """带超时控制的搜索方法
        
        Args:
            search_obj: 搜索对象
            method_name: 方法名
            keyword: 搜索关键词
            timeout: 超时秒数
            
        Returns:
            搜索结果或异常
        """
        import concurrent.futures
        
        method = getattr(search_obj, method_name)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(method, keyword)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                logger.warning(f"搜索源 {method_name} 超时 ({timeout}秒)")
                return []
            except Exception as e:
                logger.error(f"搜索源 {method_name} 发生错误: {e}")
                return e
    
    @staticmethod
    def format_results(results: List[Dict[str, Any]], keyword: str) -> str:
        """格式化搜索结果为可读文本
        
        Args:
            results: 搜索结果列表
            keyword: 原始搜索关键词
            
        Returns:
            格式化后的文本
        """
        if not results:
            return f"搜索内容：{keyword}\n⚠未找到，可换个关键词尝试哦\n————————————\n⚠搜索指令：搜:XXX 或 搜索:XXX"
            
        reply = f"搜索内容：{keyword}\n————————————"
        for item in results:
            reply += f"\n🌐️{item.get('title', '未知标题')}"
            reply += f"\n{item.get('url', '未知URL')}"
            reply += "\n————————————"
            
        if any(item.get('is_time', 0) == 1 for item in results):
            reply += "\n⚠资源来源网络，30分钟后删除"
            reply += "\n⚠避免失效，请及时保存~💾"
            
        return reply
    
    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取搜索历史记录
        
        Args:
            limit: 返回的历史记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 搜索历史记录列表
        """
        if not self.db:
            logger.error("数据库未初始化，无法获取搜索历史")
            return []
            
        try:
            records = self.db.get_search_history(limit)
            results = []
            for record in records:
                results.append({
                    'id': record[0],
                    'keyword': record[1],
                    'result_count': record[2],
                    'search_time': record[3]
                })
            return results
        except Exception as e:
            logger.error(f"获取搜索历史失败: {e}")
            return [] 