#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闲鱼助手 - 插件与关键字管理工具
用于管理每个商品的关键字检测规则
"""

import sqlite3
import os
import json

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
            enable_ai_reply INTEGER DEFAULT 0,
            enable_keyword_detection INTEGER DEFAULT 0,
            keyword_rules TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("数据库初始化完成")

def list_all_items():
    """列出所有商品及其关键字检测状态"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT item_id, shop_name, enable_keyword_detection FROM xianyu_shop ORDER BY item_id")
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        print("数据库中没有商品信息")
        return
    
    print("\n=== 商品列表 ===")
    print(f"{'商品ID':<15} {'商品名称':<30} {'关键字检测':<10}")
    print("-" * 55)
    for item_id, shop_name, enable_keyword_detection in items:
        status = "开启" if enable_keyword_detection else "关闭"
        shop_name_display = shop_name[:28] + ".." if shop_name and len(shop_name) > 30 else shop_name or "未知"
        print(f"{item_id:<15} {shop_name_display:<30} {status:<10}")

def toggle_keyword_detection(item_id):
    """切换指定商品的关键字检测开关"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 先查询当前状态
    cursor.execute("SELECT enable_keyword_detection, shop_name FROM xianyu_shop WHERE item_id = ?", (item_id,))
    result = cursor.fetchone()
    
    if not result:
        print(f"未找到商品ID: {item_id}")
        conn.close()
        return
    
    current_status, shop_name = result
    new_status = 0 if current_status else 1
    
    # 更新状态
    cursor.execute("UPDATE xianyu_shop SET enable_keyword_detection = ? WHERE item_id = ?", (new_status, item_id))
    conn.commit()
    conn.close()
    
    status_text = "开启" if new_status else "关闭"
    print(f"商品 '{shop_name}' (ID: {item_id}) 的关键字检测已{status_text}")

def set_keyword_detection(item_id, enable):
    """设置指定商品的关键字检测开关"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 先查询商品是否存在
    cursor.execute("SELECT shop_name FROM xianyu_shop WHERE item_id = ?", (item_id,))
    result = cursor.fetchone()
    
    if not result:
        print(f"未找到商品ID: {item_id}")
        conn.close()
        return
    
    shop_name = result[0]
    
    # 更新状态
    cursor.execute("UPDATE xianyu_shop SET enable_keyword_detection = ? WHERE item_id = ?", (enable, item_id))
    conn.commit()
    conn.close()
    
    status_text = "开启" if enable else "关闭"
    print(f"商品 '{shop_name}' (ID: {item_id}) 的关键字检测已设置为{status_text}")

def batch_set_keyword_detection(enable):
    """批量设置所有商品的关键字检测开关"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE xianyu_shop SET enable_keyword_detection = ?", (enable,))
    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()
    
    status_text = "开启" if enable else "关闭"
    print(f"已批量{status_text} {affected_rows} 个商品的关键字检测")

def view_keyword_rules(item_id):
    """查看指定商品的关键字规则"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT shop_name, keyword_rules FROM xianyu_shop WHERE item_id = ?", (item_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print(f"未找到商品ID: {item_id}")
        return
    
    shop_name, keyword_rules = result
    
    print(f"\n=== 商品 '{shop_name}' (ID: {item_id}) 的关键字规则 ===")
    
    if not keyword_rules:
        print("该商品未设置关键字规则")
        return
    
    try:
        rules = json.loads(keyword_rules)
        for i, rule in enumerate(rules):
            print(f"\n规则 {i+1}:")
            print(f"  关键字: {', '.join(rule.get('keywords', []))}")
            print(f"  插件名: {rule.get('plugin', '未设置')}")
            params = rule.get('params', {})
            if params:
                print(f"  参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
    except json.JSONDecodeError:
        print(f"关键字规则解析失败: {keyword_rules}")

def set_keyword_rules(item_id):
    """设置指定商品的关键字规则"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT shop_name, keyword_rules FROM xianyu_shop WHERE item_id = ?", (item_id,))
    result = cursor.fetchone()
    
    if not result:
        print(f"未找到商品ID: {item_id}")
        conn.close()
        return
    
    shop_name, current_rules = result
    
    print(f"\n=== 设置商品 '{shop_name}' (ID: {item_id}) 的关键字规则 ===")
    
    # 显示当前规则
    if current_rules:
        try:
            rules = json.loads(current_rules)
            print("\n当前规则:")
            for i, rule in enumerate(rules):
                print(f"  规则 {i+1}:")
                print(f"    关键字: {', '.join(rule.get('keywords', []))}")
                print(f"    插件名: {rule.get('plugin', '未设置')}")
                params = rule.get('params', {})
                if params:
                    print(f"    参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
        except json.JSONDecodeError:
            print(f"当前关键字规则解析失败: {current_rules}")
            rules = []
    else:
        rules = []
        print("当前没有设置关键字规则")
    
    # 编辑规则
    while True:
        print("\n=== 编辑关键字规则 ===")
        print("1. 添加规则")
        print("2. 删除规则")
        print("3. 清空所有规则")
        print("0. 保存并返回")
        
        choice = input("请选择操作 (0-3): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            # 添加规则
            keywords_input = input("请输入关键字，多个关键字用逗号分隔: ").strip()
            if not keywords_input:
                print("关键字不能为空")
                continue
                
            keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
            
            plugin = input("请输入插件名称: ").strip()
            if not plugin:
                print("插件名称不能为空")
                continue
                
            params_input = input("请输入插件参数 (JSON格式，可选): ").strip()
            if params_input:
                try:
                    params = json.loads(params_input)
                except json.JSONDecodeError:
                    print("参数格式错误，请使用正确的JSON格式")
                    continue
            else:
                params = {}
                
            new_rule = {
                "keywords": keywords,
                "plugin": plugin,
                "params": params
            }
            
            rules.append(new_rule)
            print("规则添加成功")
            
        elif choice == '2':
            # 删除规则
            if not rules:
                print("没有可删除的规则")
                continue
                
            for i, rule in enumerate(rules):
                print(f"{i+1}. 关键字: {', '.join(rule.get('keywords', []))}, 插件: {rule.get('plugin', '未设置')}")
                
            rule_index = input("请输入要删除的规则序号: ").strip()
            try:
                index = int(rule_index) - 1
                if 0 <= index < len(rules):
                    del rules[index]
                    print("规则删除成功")
                else:
                    print("无效的规则序号")
            except ValueError:
                print("请输入有效的数字")
                
        elif choice == '3':
            # 清空所有规则
            confirm = input("确认要清空所有规则吗？(y/N): ").strip().lower()
            if confirm == 'y':
                rules = []
                print("所有规则已清空")
        else:
            print("无效的选择，请重新输入")
    
    # 保存规则
    rules_json = json.dumps(rules, ensure_ascii=False) if rules else None
    cursor.execute("UPDATE xianyu_shop SET keyword_rules = ? WHERE item_id = ?", (rules_json, item_id))
    conn.commit()
    conn.close()
    
    print(f"商品 '{shop_name}' (ID: {item_id}) 的关键字规则已保存")

def show_menu():
    """显示菜单"""
    print("\n=== 闲鱼助手 插件与关键字管理工具 ===")
    print("1. 查看所有商品")
    print("2. 切换指定商品的关键字检测")
    print("3. 开启指定商品的关键字检测")
    print("4. 关闭指定商品的关键字检测")
    print("5. 查看指定商品的关键字规则")
    print("6. 设置指定商品的关键字规则")
    print("7. 批量开启所有商品关键字检测")
    print("8. 批量关闭所有商品关键字检测")
    print("0. 退出")
    print("=" * 40)

def main():
    """主函数"""
    init_database()
    
    while True:
        show_menu()
        choice = input("请选择操作 (0-8): ").strip()
        
        if choice == '0':
            print("退出程序")
            break
        elif choice == '1':
            list_all_items()
        elif choice == '2':
            item_id = input("请输入商品ID: ").strip()
            if item_id:
                toggle_keyword_detection(item_id)
            else:
                print("商品ID不能为空")
        elif choice == '3':
            item_id = input("请输入商品ID: ").strip()
            if item_id:
                set_keyword_detection(item_id, 1)
            else:
                print("商品ID不能为空")
        elif choice == '4':
            item_id = input("请输入商品ID: ").strip()
            if item_id:
                set_keyword_detection(item_id, 0)
            else:
                print("商品ID不能为空")
        elif choice == '5':
            item_id = input("请输入商品ID: ").strip()
            if item_id:
                view_keyword_rules(item_id)
            else:
                print("商品ID不能为空")
        elif choice == '6':
            item_id = input("请输入商品ID: ").strip()
            if item_id:
                set_keyword_rules(item_id)
            else:
                print("商品ID不能为空")
        elif choice == '7':
            confirm = input("确认要批量开启所有商品的关键字检测吗？(y/N): ").strip().lower()
            if confirm == 'y':
                batch_set_keyword_detection(1)
            else:
                print("操作已取消")
        elif choice == '8':
            confirm = input("确认要批量关闭所有商品的关键字检测吗？(y/N): ").strip().lower()
            if confirm == 'y':
                batch_set_keyword_detection(0)
            else:
                print("操作已取消")
        else:
            print("无效的选择，请重新输入")
        
        input("\n按回车键继续...")

if __name__ == '__main__':
    main() 