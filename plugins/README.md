# 闲鱼助手 - 插件系统

闲鱼助手使用基于文件夹的插件架构，每个插件都有自己独立的目录，包含所有需要的文件。

## 插件目录结构

插件应按以下目录结构组织：

```
plugins/
  ├── plugin_base.py              # 插件基类
  ├── plugin_name1/               # 第一个插件目录
  │   ├── __init__.py             # 插件入口文件
  │   ├── main.py                 # 插件主程序
  │   ├── config.toml             # 插件配置文件
  │   └── ...                     # 其他插件相关文件
  └── plugin_name2/               # 第二个插件目录
      ├── __init__.py
      ├── main.py
      ├── config.toml
      └── ...
```

## 创建新插件

### 1. 创建插件目录

在 `plugins` 目录下创建一个新的文件夹，以插件名称命名：

```
plugins/my_plugin/
```

### 2. 创建入口文件

在插件目录中创建 `__init__.py`，导入插件类：

```python
"""
闲鱼助手 - 我的插件
"""

from .main import MyPlugin
```

### 3. 创建主程序文件

创建 `main.py`，实现插件的主要逻辑：

```python
"""
闲鱼助手 - 我的插件

插件功能描述
"""

import os
import sys
from loguru import logger

# 导入基类
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(plugin_dir), ".."))
from plugins.plugin_base import PluginBase

class MyPlugin(PluginBase):
    """我的插件类"""
    
    name = "my_plugin"             # 插件名称
    description = "插件功能描述"    # 插件描述
    version = "1.0.0"              # 插件版本
    author = "作者名称"            # 插件作者
    priority = 500                 # 插件优先级，数字越大优先级越高
    
    def __init__(self):
        super().__init__()
        # 初始化代码...
    
    async def handle_message(self, chat_bot, message, context=None, **kwargs):
        """处理消息
        
        Args:
            chat_bot: ChatBot实例
            message: 触发插件的用户消息
            context: 消息上下文
            **kwargs: 额外参数
            
        Returns:
            True 如果消息已处理，False 如果未处理
        """
        logger.info(f"{self.name} 插件被触发: {message}")
        
        # 插件逻辑...
        
        return False  # 返回True表示消息已处理，False表示未处理
```

### 4. 创建配置文件

创建 `config.toml` 配置文件：

```toml
# 我的插件配置文件

[section1]
option1 = "值1"
option2 = 123

[section2]
option3 = true
```

## 插件优先级

插件的优先级由 `priority` 属性决定，数字越大优先级越高。当多个插件都能处理同一条消息时，会按照优先级从高到低依次执行，直到有一个插件返回 `True`。

## 内置插件优先级

- `auto_ship`：900 - 自动发货插件
- `auto_notice`：800 - 自动转人工客服插件
- `resource_search`：500 - 资源搜索插件
- `keyword`：300 - 关键字检测插件
- `ai_reply`：100 - AI回复插件

## 插件配置

每个插件可以有自己的配置文件 `config.toml`，插件应自行负责加载和解析配置文件。

## 插件注册

插件系统会自动扫描 `plugins` 目录下的子目录，加载符合要求的插件。只要插件目录包含正确的 `__init__.py` 和插件类，就会被自动注册到系统中。 