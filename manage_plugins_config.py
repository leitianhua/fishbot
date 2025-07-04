#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闲鱼助手 - 插件配置管理工具
用于管理每个商品的插件配置
"""

import os
import sys
import json
import sqlite3
import importlib.util
from loguru import logger

# 配置loguru
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add("logs/plugins_config_{time:YYYY-MM-DD}.log", rotation="00:00", retention="7 days", level="INFO", encoding="utf-8")

# 数据库路径
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "items.db")

def init_database():
    """初始化数据库"""
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
            plugins_config TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("数据库初始化完成")

def list_all_items():
    """列出所有商品及其插件配置状态"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT item_id, shop_name, plugins_config FROM xianyu_shop ORDER BY item_id")
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        print("数据库中没有商品信息")
        return
    
    print("\n=== 商品列表 ===")
    print(f"{'商品ID':<15} {'商品名称':<30} {'已启用插件':<30}")
    print("-" * 75)
    for item_id, shop_name, plugins_config in items:
        enabled_plugins = []
        if plugins_config:
            try:
                enabled_plugins = json.loads(plugins_config)
                if not isinstance(enabled_plugins, list):
                    enabled_plugins = ["配置格式错误：不是数组"]
            except json.JSONDecodeError:
                enabled_plugins = ["配置解析失败"]
        
        plugins_str = ", ".join(enabled_plugins) if enabled_plugins else "无"
        shop_name_display = shop_name[:28] + ".." if shop_name and len(shop_name) > 30 else shop_name or "未知"
        print(f"{item_id:<15} {shop_name_display:<30} {plugins_str[:30]}")

def get_available_plugins():
    """获取可用的插件列表"""
    plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
    if not os.path.exists(plugins_dir):
        print(f"创建插件目录: {plugins_dir}")
        os.makedirs(plugins_dir)
    
    available_plugins = []
    
    # 遍历插件目录中的所有Python文件
    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            plugin_name = filename[:-3]  # 去掉.py后缀
            plugin_path = os.path.join(plugins_dir, filename)
            
            try:
                # 动态导入插件模块
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                if spec is not None:
                    plugin_module = importlib.util.module_from_spec(spec)
                    sys.modules[plugin_name] = plugin_module
                    spec.loader.exec_module(plugin_module)
                    
                    # 获取插件信息
                    plugin_info = {
                        "name": plugin_name,
                        "description": plugin_module.__doc__ or "无描述",
                        "priority": getattr(plugin_module, "priority", 100)
                    }
                    available_plugins.append(plugin_info)
            except Exception as e:
                print(f"加载插件 {plugin_name} 失败: {e}")
    
    return available_plugins

def view_item_plugins_config(item_id):
    """查看指定商品的插件配置"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT shop_name, plugins_config FROM xianyu_shop WHERE item_id = ?", (item_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print(f"未找到商品ID: {item_id}")
        return
    
    shop_name, plugins_config = result
    
    print(f"\n=== 商品 '{shop_name}' (ID: {item_id}) 的插件配置 ===")
    
    if not plugins_config:
        print("该商品未设置插件配置")
        return
    
    try:
        enabled_plugins = json.loads(plugins_config)
        
        if not isinstance(enabled_plugins, list):
            print(f"插件配置格式错误(不是数组): {plugins_config}")
            return
        
        print("\n已启用的插件:")
        if not enabled_plugins:
            print("  无")
        else:
            for i, plugin_name in enumerate(enabled_plugins):
                print(f"  {i+1}. {plugin_name}")
    except json.JSONDecodeError:
        print(f"插件配置解析失败: {plugins_config}")

def edit_item_plugins_config(item_id):
    """编辑指定商品的插件配置"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT shop_name, plugins_config FROM xianyu_shop WHERE item_id = ?", (item_id,))
    result = cursor.fetchone()
    
    if not result:
        print(f"未找到商品ID: {item_id}")
        conn.close()
        return
    
    shop_name, plugins_config = result
    
    print(f"\n=== 编辑商品 '{shop_name}' (ID: {item_id}) 的插件配置 ===")
    
    # 解析当前配置
    enabled_plugins = []
    if plugins_config:
        try:
            enabled_plugins = json.loads(plugins_config)
            if not isinstance(enabled_plugins, list):
                print(f"当前插件配置格式错误(不是数组): {plugins_config}")
                enabled_plugins = []
        except json.JSONDecodeError:
            print(f"当前插件配置解析失败: {plugins_config}")
    
    # 获取可用插件
    available_plugins = get_available_plugins()
    available_plugin_names = [p["name"] for p in available_plugins]
    
    while True:
        print("\n=== 插件配置编辑 ===")
        print("1. 查看已启用的插件")
        print("2. 添加插件")
        print("3. 移除插件")
        print("4. 查看可用插件")
        print("0. 保存并返回")
        
        choice = input("请选择操作 (0-4): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            # 查看已启用的插件
            print("\n已启用的插件:")
            if not enabled_plugins:
                print("  无")
            else:
                for i, plugin_name in enumerate(enabled_plugins):
                    print(f"  {i+1}. {plugin_name}")
        elif choice == '2':
            # 添加插件
            print("\n可用的插件:")
            for i, plugin_info in enumerate(available_plugins):
                print(f"  {i+1}. {plugin_info['name']} - {plugin_info['description']}")
            
            plugin_index = input("\n请输入要添加的插件序号 (0取消): ").strip()
            try:
                index = int(plugin_index) - 1
                if index < 0:
                    continue
                if 0 <= index < len(available_plugins):
                    plugin_name = available_plugins[index]["name"]
                    if plugin_name in enabled_plugins:
                        print(f"插件 {plugin_name} 已启用")
                    else:
                        enabled_plugins.append(plugin_name)
                        print(f"插件 {plugin_name} 已添加")
                else:
                    print("无效的插件序号")
            except ValueError:
                print("请输入有效的数字")
        elif choice == '3':
            # 移除插件
            if not enabled_plugins:
                print("没有已启用的插件")
                continue
                
            print("\n已启用的插件:")
            for i, plugin_name in enumerate(enabled_plugins):
                print(f"  {i+1}. {plugin_name}")
                
            plugin_index = input("\n请输入要移除的插件序号 (0取消): ").strip()
            try:
                index = int(plugin_index) - 1
                if index < 0:
                    continue
                if 0 <= index < len(enabled_plugins):
                    plugin_name = enabled_plugins[index]
                    enabled_plugins.remove(plugin_name)
                    print(f"插件 {plugin_name} 已移除")
                else:
                    print("无效的插件序号")
            except ValueError:
                print("请输入有效的数字")
        elif choice == '4':
            # 查看可用插件
            print("\n可用的插件:")
            for i, plugin_info in enumerate(available_plugins):
                status = "已启用" if plugin_info["name"] in enabled_plugins else "未启用"
                print(f"  {i+1}. {plugin_info['name']} - {plugin_info['description']} ({status})")
        else:
            print("无效的选择，请重新输入")
    
    # 保存配置 - 直接保存插件名称数组
    plugins_config_json = json.dumps(enabled_plugins, ensure_ascii=False)
    
    cursor.execute("UPDATE xianyu_shop SET plugins_config = ? WHERE item_id = ?", (plugins_config_json, item_id))
    conn.commit()
    conn.close()
    
    print(f"商品 '{shop_name}' (ID: {item_id}) 的插件配置已保存")

def show_menu():
    """显示菜单"""
    print("\n=== 闲鱼助手 插件配置管理工具 ===")
    print("1. 查看所有商品")
    print("2. 查看指定商品的插件配置")
    print("3. 编辑指定商品的插件配置")
    print("4. 查看可用插件")
    print("0. 退出")
    print("=" * 40)

def main():
    """主函数"""
    init_database()
    
    while True:
        show_menu()
        choice = input("请选择操作 (0-4): ").strip()
        
        if choice == '0':
            print("退出程序")
            break
        elif choice == '1':
            list_all_items()
        elif choice == '2':
            item_id = input("请输入商品ID: ").strip()
            if item_id:
                view_item_plugins_config(item_id)
            else:
                print("商品ID不能为空")
        elif choice == '3':
            item_id = input("请输入商品ID: ").strip()
            if item_id:
                edit_item_plugins_config(item_id)
            else:
                print("商品ID不能为空")
        elif choice == '4':
            available_plugins = get_available_plugins()
            print("\n=== 可用插件列表 ===")
            for i, plugin_info in enumerate(available_plugins):
                print(f"{i+1}. {plugin_info['name']} - {plugin_info['description']}")
                print(f"   优先级: {plugin_info['priority']}")
        else:
            print("无效的选择，请重新输入")
        
        input("\n按回车键继续...")

if __name__ == '__main__':
    main() 