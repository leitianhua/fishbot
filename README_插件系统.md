# 闲鱼助手插件系统

闲鱼助手现已支持插件系统，可以通过插件扩展功能，每个商品可以单独配置启用哪些插件。

## 插件系统特点

1. **商品独立配置**：每个商品可以单独配置启用哪些插件
2. **插件优先级**：插件有优先级，可以控制插件的执行顺序
3. **插件链执行**：按优先级依次执行插件，直到有插件处理了消息
4. **简单的插件开发**：只需实现一个函数和注册函数即可

## 内置插件

闲鱼助手内置了以下插件：

1. **auto_ship_plugin**：自动发货插件，检测付款信息并自动发货（优先级：900）
2. **auto_notice_plugin**：自动转人工客服插件，检测转人工客服请求并通知（优先级：800）
3. **resource_search_plugin**：资源搜索插件，搜索网盘资源并返回结果（优先级：500）
4. **keyword_plugin**：关键字检测插件，检测消息中的关键字并触发相应操作（优先级：300）
5. **ai_reply_plugin**：AI回复插件，使用AI模型回复客户消息（优先级：100）

## 插件配置管理

使用 `manage_plugins_config.py` 工具可以管理每个商品的插件配置：

```bash
python manage_plugins_config.py
```

功能包括：
- 查看所有商品
- 查看指定商品的插件配置
- 编辑指定商品的插件配置
- 查看可用插件

## 插件配置格式

插件配置**必须**采用数组格式，只包含要启用的插件名称：

```json
["auto_ship", "auto_notice", "ai_reply"]
```

数组中出现的插件名称表示该插件已启用。系统不兼容其他格式，如果配置不是数组格式，将被视为无效配置。

## 插件开发指南

### 1. 创建插件文件

在 `plugins` 目录下创建一个 Python 文件，如 `my_plugin.py`：

```python
"""
插件描述
"""

import logging

# 获取日志记录器
log = logging.getLogger()

async def my_plugin(chat_bot, message, context=None, **params):
    """插件主函数
    
    Args:
        chat_bot: ChatBot实例
        message: 触发插件的用户消息
        context: 消息上下文
        
    Returns:
        True 如果消息已处理，False 如果未处理
    """
    log.info(f"我的插件被触发: {message}")
    
    # 插件逻辑
    # ...
    
    # 发送消息
    await chat_bot.send_message("插件回复")
    
    # 返回True表示消息已处理，后续插件不会执行
    return True

def register(chat_bot):
    """注册插件
    
    Args:
        chat_bot: ChatBot实例
    """
    # 注册插件，设置优先级
    chat_bot.register_plugin("my_plugin", my_plugin, priority=300)
    log.info("我的插件注册成功")
```

### 2. 插件函数说明

插件主函数必须是异步函数，接收以下参数：

- **chat_bot**：ChatBot实例，可以调用其方法
- **message**：触发插件的用户消息
- **context**：消息上下文，包含消息历史、是否付款等信息

返回值：
- **True**：表示消息已处理，后续插件不会执行
- **False**：表示消息未处理，继续执行后续插件

### 3. 插件注册

插件必须提供一个 `register` 函数，用于注册插件：

```python
def register(chat_bot):
    chat_bot.register_plugin("插件名称", 插件函数, priority=优先级)
```

优先级说明：
- 数字越大，优先级越高
- 默认优先级为100
- 建议优先级范围：10-1000

### 4. 上下文信息

插件可以通过 `context` 参数获取以下信息：

```python
{
    "messages": [消息历史],
    "is_payed": 是否已付款,
    "is_ship": 是否已发货,
    "auto_ship_required": 是否需要自动发货,
    "auto_notice_required": 是否需要转人工客服
}
```

## 常见问题

1. **插件加载失败**
   - 检查插件文件是否有语法错误
   - 检查插件是否有 `register` 函数

2. **插件不执行**
   - 检查商品是否启用了该插件
   - 检查插件优先级是否被更高优先级的插件阻断

3. **如何调试插件**
   - 查看日志输出
   - 在插件中添加 `log.debug()` 语句 