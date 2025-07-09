#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
闲鱼助手 - 配置管理模块
"""

import os
import sys
from pathlib import Path
from loguru import logger

# 初始化路径
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "main_config.toml"
DB_PATH = BASE_DIR / "fishbot.db"
LOGS_DIR = BASE_DIR / "logs"
PLUGINS_DIR = BASE_DIR / "plugins"

# 确保日志目录存在
LOGS_DIR.mkdir(exist_ok=True)

def load_config():
    """加载主配置文件
    
    Returns:
        dict: 配置字典
    """
    try:
        import tomllib
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "rb") as f:
                config = tomllib.load(f)
                logger.info(f"已加载配置文件: {CONFIG_PATH}")
                return config
        else:
            logger.warning(f"配置文件不存在: {CONFIG_PATH}，使用默认配置")
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
    return {}

# 全局配置
config = load_config()

# 配置日志
def setup_logging():
    """配置日志系统"""
    logger.remove()  # 移除默认处理器
    LOG_LEVEL = config.get("logging", {}).get("level", "INFO")
    logger.add(sys.stderr, level=LOG_LEVEL, 
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    logger.add(LOGS_DIR / "autofish_{time:YYYY-MM-DD}.log", rotation="00:00", 
            retention=config.get("logging", {}).get("retention_days", 7), level=LOG_LEVEL, encoding="utf-8")
    logger.info(f"日志级别设置为: {LOG_LEVEL}")

# 浏览器配置
USER_DATA_DIR = BASE_DIR / config.get("browser", {}).get("user_data_dir", "user_data/大号")
EXECUTABLE_PATH = config.get("browser", {}).get("executable_path", r"C:\Program Files\Google\Chrome\Application\chrome.exe")

# 设置日志
setup_logging()