# 闲鱼助手

闲鱼助手是一个自动化工具，用于管理闲鱼商品消息、自动回复、资源搜索等功能。

## 特点

- **插件化架构**：所有功能都通过插件实现，可以灵活配置
- **商品独立配置**：每个商品可以单独配置启用哪些插件
- **优先级控制**：插件有优先级，可以控制插件的执行顺序
- **多种功能**：支持AI回复、自动发货、资源搜索等功能

## 安装

1. 克隆仓库
```bash
git clone https://github.com/yourusername/xianyu-assistant.git
cd xianyu-assistant
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 安装Playwright
```bash
pip install playwright
playwright install
```

## 使用方法

### 启动程序

```bash
python autoFish.py
```

### 管理插件配置

```bash
python manage_plugins_config.py
```

## 日志控制

可以通过环境变量或.env文件控制日志级别：

1. 使用环境变量：
```bash
# Windows
set LOG_LEVEL=WARNING
python autoFish.py

# Linux/Mac
LOG_LEVEL=WARNING python autoFish.py
```

2. 使用.env文件：
创建一个.env文件，内容如下：
```
LOG_LEVEL=WARNING
```

可用的日志级别（从低到高）：
- TRACE: 最详细的日志
- DEBUG: 调试信息
- INFO: 一般信息
- SUCCESS: 成功信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误信息

默认日志级别为INFO。设置为更高级别（如WARNING）可以减少日志输出。

## 插件系统

详细的插件系统说明请参考 [README_插件系统.md](README_插件系统.md)。

## 内置插件

1. **auto_ship_plugin**：自动发货插件（优先级：10）
2. **auto_notice_plugin**：自动转人工客服插件（优先级：20）
3. **resource_search_plugin**：资源搜索插件（优先级：100）
4. **keyword_plugin**：关键字检测插件（优先级：500）
5. **ai_reply_plugin**：AI回复插件（优先级：900）

## 许可证

MIT 