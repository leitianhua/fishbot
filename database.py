#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
闲鱼助手 - 数据库操作模块
"""

import sqlite3
import json
from loguru import logger
from config import DB_PATH

async def init_database():
    """初始化数据库，创建必要的表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建商品表
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

def get_shop_info(item_id):
    """获取商品信息
    
    Args:
        item_id (str): 商品ID
        
    Returns:
        dict: 商品信息字典，如果不存在则返回None
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT shop_name, shop_price, shop_desc, shop_other, buy_success_replies, plugins_config FROM xianyu_shop WHERE item_id = ?", 
        (item_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "shop_name": result[0],
            "shop_price": result[1],
            "shop_desc": result[2],
            "shop_other": result[3],
            "buy_success_replies": result[4],
            "plugins_config": json.loads(result[5]) if result[5] else []
        }
    return None

def save_shop_info(item_id, shop_info):
    """保存商品信息
    
    Args:
        item_id (str): 商品ID
        shop_info (dict): 商品信息字典
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 准备数据
    shop_name = shop_info.get("shop_name", "")
    shop_price = shop_info.get("shop_price", "")
    shop_desc = shop_info.get("shop_desc", "")
    shop_other = shop_info.get("shop_other", "")
    buy_success_replies = shop_info.get("buy_success_replies", "")
    plugins_config = json.dumps(shop_info.get("plugins_config", []))
    
    # 插入或更新数据
    cursor.execute("""
        INSERT INTO xianyu_shop (item_id, shop_name, shop_price, shop_desc, shop_other, buy_success_replies, plugins_config) 
        VALUES (?, ?, ?, ?, ?, ?, ?) 
        ON CONFLICT(item_id) 
        DO UPDATE SET 
            shop_name = excluded.shop_name, 
            shop_price = excluded.shop_price,
            shop_desc = excluded.shop_desc,
            shop_other = excluded.shop_other,
            buy_success_replies = excluded.buy_success_replies,
            plugins_config = excluded.plugins_config
    """, (item_id, shop_name, shop_price, shop_desc, shop_other, buy_success_replies, plugins_config))
    
    conn.commit()
    conn.close()
    logger.info(f"商品信息已保存: {item_id}")