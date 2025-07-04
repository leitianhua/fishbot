#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
夸克网盘功能测试脚本
"""

import os
import sys
import toml
from loguru import logger
from utils.quark import Quark

def main():
    """测试夸克网盘功能的主函数"""
    # 设置日志级别
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 读取配置文件
    config_path = os.path.join(current_dir, 'config.toml')
    if os.path.exists(config_path):
        conf = toml.load(config_path)
    else:
        conf = {}
        logger.warning(f"配置文件不存在: {config_path}")
    
    # 初始化夸克网盘操作类
    q = Quark(conf)
    
    # 测试转存功能
    test_url = "https://pan.quark.cn/s/0140a6cc5956"
    logger.info(f"测试转存链接: {test_url}")
    result = q.store(test_url)
    
    if result[0]:
        logger.info(f"转存成功: {result[1]} -> {result[2]}")
    else:
        if result[1]:
            logger.info(f"文件已存在: {result[1]} -> {result[2]}")
        else:
            logger.error("转存失败")

if __name__ == '__main__':
    main() 