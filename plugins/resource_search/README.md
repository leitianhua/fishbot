# 资源搜索插件

## 功能简介

本插件用于搜索网络资源并转存到网盘，提供以下功能：

1. 从多个来源搜索网盘资源
2. 自动转存资源到夸克网盘
3. 生成临时分享链接
4. 自动清理过期资源

## 目录结构

```
resource_search/
├── __init__.py              # 插件初始化文件
├── main.py                  # 插件主入口，负责消息处理
├── README.md                # 说明文档
├── utils/                   # 核心工具目录
│   ├── __init__.py          # 工具包初始化
│   ├── core.py              # 核心业务逻辑
│   ├── database.py          # 数据库管理
│   ├── search.py            # 资源搜索实现
│   ├── quark.py             # 夸克网盘操作
│   ├── baidu.py             # 百度网盘操作
│   ├── config.toml          # 配置文件
│   └── panDB.db             # 资源数据库
```

## 使用方法

### 插件使用

发送"搜索+关键词"即可触发搜索，例如：

```
搜索三体
```

### 代码调用

如果需要在其他应用中调用搜索功能，可以直接导入核心类：

```python
from plugins.resource_search.utils.core import ResourceCore

# 初始化核心类
core = ResourceCore()

# 搜索资源
results = core.search_and_store("关键词", limit=5)

# 格式化结果
formatted_text = core.format_results(results, "关键词")
```

## 配置说明

配置文件位于 `utils/config.toml`，主要配置项包括：

1. 过期时间设置
2. 广告过滤设置
3. 夸克网盘账号设置
4. 百度网盘账号设置

示例：

```toml
[general]
expired_time = 30  # 资源过期时间（分钟）

[accounts]
# 夸克网盘账号配置
[[accounts.quark]]
enable = true
cookie = "你的夸克网盘cookie"
save_dir = "你的夸克网盘保存目录ID"
```

## 数据库结构

插件使用SQLite数据库存储资源记录，主要表结构如下：

### pan_files 表
- file_id: 文件ID (主键)
- file_name: 文件名
- file_type: 文件类型 (0为文件夹，1为文件)
- share_link: 分享链接
- pan_type: 网盘类型 (quark或baidu)
- created_at: 创建时间

### search_history 表
- id: 自增主键
- keyword: 搜索关键词
- result_count: 结果数量
- search_time: 搜索时间

## 扩展开发

如需添加新的搜索源，在 `search.py` 中添加新的搜索方法，并在 `core.py` 中的 `search_methods` 列表中添加该方法名。

如需支持新的网盘，创建对应的网盘操作类，并在 `core.py` 中的 `search_and_store` 方法中添加对应的处理逻辑。 