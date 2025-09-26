# 短剧搜索插件

AstrBot 短剧搜索插件，支持 LLM 函数调用功能

## 功能特性

- 🎬 **短剧搜索**: 根据名称搜索短剧
- 📂 **分类浏览**: 获取分类列表和分类下的短剧
- 🌟 **智能推荐**: 获取推荐短剧
- 🆕 **最新短剧**: 获取最新上线的短剧
- 🎥 **剧集播放**: 获取短剧的播放地址
- 🤖 **LLM 集成**: 支持大语言模型函数调用

## 使用方法

### 命令使用

- `/短剧分类` 或 `/duanju_categories` - 获取所有分类列表
- `/搜索短剧 剧名` - 搜索指定名称的短剧
- `/短剧推荐` 或 `/duanju_recommend` - 获取推荐短剧
- `/最新短剧` 或 `/duanju_latest` - 获取最新短剧
- `/分类短剧 分类ID [页码]` - 获取指定分类的短剧

### LLM 函数调用

插件提供以下函数供 LLM 调用：

1. `get_categories()` - 获取短剧分类列表
2. `search_dramas(name)` - 根据名称搜索短剧
3. `get_category_dramas(category_id, page)` - 获取分类短剧
4. `get_recommendations(category_id, size)` - 获取推荐短剧
5. `get_latest_dramas(page)` - 获取最新短剧
6. `get_drama_episodes(drama_id, episode)` - 获取剧集播放地址

## 示例

### 搜索短剧
```
用户: /搜索短剧 霸道总裁
机器人: 🔍 搜索 '霸道总裁' 的结果：

🎬 霸道总裁的小娇妻
   📊 评分: 85
   🆔 ID: 12345
   📅 更新: 2024-01-15
```

### 获取分类
```
用户: /短剧分类
机器人: 📺 短剧分类列表：

🎬 都市情感 (ID: 1)
🎬 古装穿越 (ID: 2)
🎬 悬疑推理 (ID: 3)
...
```

## API 数据源

本插件使用的 API 接口: `https://api.r2afosne.dpdns.org`

## 依赖

- aiohttp>=3.8.0

## 安装

1. 将插件文件夹放置到 AstrBot 的 `data/plugins/` 目录下
2. 重启 AstrBot 或在 WebUI 中重载插件
3. 插件将自动安装依赖并开始工作

## 支持

- [AstrBot 官方文档](https://docs.astrbot.app)
- [插件开发指南](https://docs.astrbot.app/dev/star/plugin.html)
