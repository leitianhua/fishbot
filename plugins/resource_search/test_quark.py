#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
夸克网盘功能测试脚本
"""

import os
import sys
import toml
from loguru import logger
from .utils.quark import Quark

def main():
    """测试夸克网盘功能的主函数"""
    # 设置日志级别
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 读取配置文件 - 修改为utils目录下的配置文件
    config_path = os.path.join(current_dir, 'utils', 'config.toml')
    if os.path.exists(config_path):
        conf = toml.load(config_path)
        logger.info(f"配置文件已加载: {config_path}")
        
        # 检查配置文件中是否包含夸克网盘账号信息
        if "accounts" in conf and "quark" in conf["accounts"]:
            quark_accounts = conf["accounts"]["quark"]
            logger.info(f"找到夸克账号配置: {len(quark_accounts)}个账号")
            
            # 检查第一个启用的账号
            quark_account = next((acc for acc in quark_accounts if acc.get("enable", True)), None)
            if quark_account:
                # 检查cookie是否存在但不打印完整cookie（安全考虑）
                if "cookie" in quark_account and quark_account["cookie"]:
                    cookie_preview = quark_account["cookie"][:20] + "..." if len(quark_account["cookie"]) > 20 else ""
                    logger.info(f"找到cookie配置: {cookie_preview}")
                else:
                    logger.warning("未找到cookie配置或cookie为空")
                
                # 检查保存目录配置
                if "save_dir" in quark_account:
                    logger.info(f"保存目录配置: {quark_account['save_dir']}")
            else:
                logger.warning("未找到启用的夸克账号")
        else:
            logger.warning("配置文件中缺少夸克账号配置")
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