#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
资源搜索功能测试脚本

此脚本展示了如何使用核心功能和数据库
"""

import os
import sys
import time
from loguru import logger

# 添加父目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 导入核心工具类和数据库（使用绝对导入）
from utils.core import ResourceCore
from utils.database import get_db_instance

def test_search(keyword):
    """测试搜索功能"""
    logger.info("测试搜索功能")
    
    # 初始化核心类
    core = ResourceCore()
    
    if not core.conf:
        logger.error("配置加载失败，请检查config.toml文件")
        return
    
    # 设置最大结果数量
    limit = 30
    
    # 开始搜索
    logger.info(f"开始搜索: {keyword}, 最大结果数: {limit}")
    print(f"正在搜索 \"{keyword}\"，请稍候...")
    
    start_time = time.time()
    results = core.search_and_store(keyword, limit=limit)
    end_time = time.time()
    
    # 显示搜索结果
    print(f"\n搜索耗时: {end_time - start_time:.2f} 秒\n")
    print(core.format_results(results, keyword))

def test_database():
    """测试数据库功能"""
    logger.info("测试数据库功能")
    
    # 获取数据库实例
    db = get_db_instance()
    
    # 测试插入文件记录
    file_id = f"test_{int(time.time())}"
    file_name = f"测试文件_{int(time.time())}"
    file_type = 1
    share_link = f"https://pan.quark.cn/s/{file_id}"
    
    logger.info(f"插入测试记录: {file_name}")
    result = db.insert_file(file_id, file_name, file_type, share_link, "quark")
    print(f"插入记录结果: {result}")
    
    # 测试查询文件
    logger.info(f"查询文件: {file_name}")
    link = db.find_share_link_by_name(file_name)
    print(f"查询结果: {link}")
    
    # 测试查询历史记录
    logger.info("查询最近5条搜索历史")
    history = db.get_search_history(5)
    print("搜索历史:")
    for record in history:
        print(f"  - {record[1]} (结果数: {record[2]}, 时间: {record[3]})")
    
    # 测试删除记录
    logger.info(f"删除测试记录: {file_id}")
    result = db.delete_file(file_id)
    print(f"删除记录结果: {result}")

if __name__ == "__main__":
    logger.add("test_log.log", rotation="10 MB", level="INFO")
    test_search("斗破苍穹")