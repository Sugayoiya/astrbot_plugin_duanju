import json
from typing import Dict, List, Optional, Any
import aiohttp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register("duanju_search", "Sugayoiya", "短剧搜索工具，支持LLM函数调用", "1.0.0", "https://github.com/Sugayoiya/astrbot_plugin_duanju.git")
class DuanjuSearchPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_base = "https://api.r2afosne.dpdns.org"
        self.session = None

    async def initialize(self):
        """初始化HTTP客户端"""
        self.session = aiohttp.ClientSession()
        logger.info("短剧搜索插件初始化完成")

    async def terminate(self):
        """清理资源"""
        if self.session:
            await self.session.close()
        logger.info("短剧搜索插件已关闭")

    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发起API请求的通用方法"""
        try:
            url = f"{self.api_base}{endpoint}"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API请求失败: {response.status}")
                    return {"error": f"API请求失败: {response.status}"}
        except Exception as e:
            logger.error(f"请求异常: {str(e)}")
            return {"error": f"请求异常: {str(e)}"}

    # LLM 函数工具定义
    async def get_categories(self) -> str:
        """获取短剧分类列表"""
        result = await self._make_request("/vod/categories")
        if "error" in result:
            return f"获取分类失败: {result['error']}"
        
        categories_info = []
        for cat in result.get("categories", []):
            categories_info.append({
                "id": cat.get("type_id"),
                "name": cat.get("type_name")
            })
        
        return json.dumps({
            "categories": categories_info,
            "total": result.get("total", 0)
        }, ensure_ascii=False)

    async def search_dramas(self, name: str) -> str:
        """根据名称搜索短剧"""
        result = await self._make_request("/vod/search", {"name": name})
        if "error" in result:
            return f"搜索失败: {result['error']}"
        
        dramas = []
        for drama in result.get("list", []):
            dramas.append({
                "id": drama.get("id"),
                "name": drama.get("name"),
                "cover": drama.get("cover"),
                "update_time": drama.get("update_time"),
                "score": drama.get("score")
            })
        
        return json.dumps({
            "total": result.get("total", 0),
            "dramas": dramas
        }, ensure_ascii=False)

    async def get_category_dramas(self, category_id: int, page: int = 1) -> str:
        """获取指定分类的热门短剧"""
        result = await self._make_request("/vod/list", {
            "categoryId": str(category_id),
            "page": str(page)
        })
        if "error" in result:
            return f"获取分类短剧失败: {result['error']}"
        
        dramas = []
        for drama in result.get("list", []):
            dramas.append({
                "id": drama.get("id"),
                "name": drama.get("name"),
                "cover": drama.get("cover"),
                "update_time": drama.get("update_time"),
                "score": drama.get("score")
            })
        
        return json.dumps({
            "total": result.get("total", 0),
            "current_page": result.get("currentPage", page),
            "total_pages": result.get("totalPages", 1),
            "dramas": dramas
        }, ensure_ascii=False)

    async def get_recommendations(self, category_id: Optional[int] = None, size: int = 10) -> str:
        """获取推荐短剧"""
        params = {"size": str(size)}
        if category_id is not None:
            params["categoryId"] = str(category_id)
            
        result = await self._make_request("/vod/recommend", params)
        if "error" in result:
            return f"获取推荐失败: {result['error']}"
        
        return json.dumps(result, ensure_ascii=False)

    async def get_latest_dramas(self, page: int = 1) -> str:
        """获取最新短剧"""
        result = await self._make_request("/vod/latest", {"page": str(page)})
        if "error" in result:
            return f"获取最新短剧失败: {result['error']}"
        
        return json.dumps(result, ensure_ascii=False)

    async def get_drama_episodes(self, drama_id: int, episode: Optional[int] = None) -> str:
        """获取短剧剧集播放地址"""
        if episode is not None:
            # 获取单集地址
            result = await self._make_request("/vod/parse/single", {
                "id": str(drama_id),
                "episode": episode
            })
        else:
            # 获取全集地址
            result = await self._make_request("/vod/parse/all", {
                "id": drama_id
            })
        
        if "error" in result:
            return f"获取剧集信息失败: {result['error']}"
        
        return json.dumps(result, ensure_ascii=False)

    # 命令处理器
    @filter.command("短剧分类", "duanju_categories")
    async def cmd_categories(self, event: AstrMessageEvent):
        """获取短剧分类列表"""
        result = await self.get_categories()
        try:
            data = json.loads(result)
            if "categories" in data:
                text = "📺 短剧分类列表：\n\n"
                for cat in data["categories"]:
                    text += f"🎬 {cat['name']} (ID: {cat['id']})\n"
                text += f"\n共 {data['total']} 个分类"
            else:
                text = result
        except:
            text = result
        
        yield event.plain_result(text)

    @filter.command("搜索短剧")
    async def cmd_search(self, event: AstrMessageEvent):
        """搜索短剧 - 使用方法: /搜索短剧 剧名"""
        args = event.message_str.split(" ", 1)
        if len(args) < 2:
            yield event.plain_result("❌ 请提供要搜索的短剧名称\n使用方法: /搜索短剧 剧名")
            return
        
        drama_name = args[1].strip()
        result = await self.search_dramas(drama_name)
        
        try:
            data = json.loads(result)
            if "dramas" in data and data["dramas"]:
                text = f"🔍 搜索 '{drama_name}' 的结果：\n\n"
                for drama in data["dramas"][:5]:  # 只显示前5个结果
                    text += f"🎬 {drama['name']}\n"
                    text += f"   📊 评分: {drama['score']}\n"
                    text += f"   🆔 ID: {drama['id']}\n"
                    text += f"   📅 更新: {drama['update_time']}\n\n"
                
                if data["total"] > 5:
                    text += f"... 还有 {data['total'] - 5} 个结果"
            else:
                text = f"😔 没有找到包含 '{drama_name}' 的短剧"
        except:
            text = result
        
        yield event.plain_result(text)

    @filter.command("短剧推荐", "duanju_recommend")
    async def cmd_recommend(self, event: AstrMessageEvent):
        """获取推荐短剧"""
        result = await self.get_recommendations(size=5)
        
        try:
            data = json.loads(result)
            text = "🌟 为您推荐的短剧：\n\n"
            text += json.dumps(data, ensure_ascii=False, indent=2)
        except:
            text = result
        
        yield event.plain_result(text)

    @filter.command("最新短剧", "duanju_latest")
    async def cmd_latest(self, event: AstrMessageEvent):
        """获取最新短剧"""
        result = await self.get_latest_dramas()
        
        try:
            data = json.loads(result)
            text = "🆕 最新短剧：\n\n"
            text += json.dumps(data, ensure_ascii=False, indent=2)
        except:
            text = result
        
        yield event.plain_result(text)

    @filter.command("分类短剧")
    async def cmd_category_dramas(self, event: AstrMessageEvent):
        """获取分类短剧 - 使用方法: /分类短剧 分类ID [页码]"""
        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result("❌ 请提供分类ID\n使用方法: /分类短剧 分类ID [页码]")
            return
        
        try:
            category_id = int(args[1])
            page = int(args[2]) if len(args) > 2 else 1
        except ValueError:
            yield event.plain_result("❌ 参数格式错误，分类ID和页码必须是数字")
            return
        
        result = await self.get_category_dramas(category_id, page)
        
        try:
            data = json.loads(result)
            if "dramas" in data and data["dramas"]:
                text = f"📂 分类 {category_id} 的短剧 (第 {data['current_page']}/{data['total_pages']} 页)：\n\n"
                for drama in data["dramas"]:
                    text += f"🎬 {drama['name']}\n"
                    text += f"   📊 评分: {drama['score']}\n"
                    text += f"   🆔 ID: {drama['id']}\n"
                    text += f"   📅 更新: {drama['update_time']}\n\n"
                
                text += f"共 {data['total']} 部短剧"
            else:
                text = f"😔 分类 {category_id} 下暂无短剧"
        except:
            text = result
        
        yield event.plain_result(text)

    # 注册LLM工具函数
    def get_llm_tools(self) -> List[Dict[str, Any]]:
        """返回可供LLM使用的工具函数定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_categories",
                    "description": "获取短剧分类列表，返回所有可用的短剧分类",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_dramas",
                    "description": "根据短剧名称搜索短剧",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "要搜索的短剧名称"
                            }
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_category_dramas",
                    "description": "获取指定分类的热门短剧列表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category_id": {
                                "type": "integer",
                                "description": "短剧分类ID"
                            },
                            "page": {
                                "type": "integer",
                                "description": "页码，默认为1",
                                "default": 1
                            }
                        },
                        "required": ["category_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recommendations",
                    "description": "获取推荐短剧",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category_id": {
                                "type": "integer",
                                "description": "可选的分类ID，不指定则获取全部分类的推荐"
                            },
                            "size": {
                                "type": "integer",
                                "description": "推荐数量，默认10个",
                                "default": 10
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_latest_dramas",
                    "description": "获取最新短剧列表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page": {
                                "type": "integer",
                                "description": "页码，默认为1",
                                "default": 1
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_drama_episodes",
                    "description": "获取短剧的剧集播放地址",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drama_id": {
                                "type": "integer",
                                "description": "短剧ID"
                            },
                            "episode": {
                                "type": "integer",
                                "description": "可选的指定集数，不指定则获取全部集数"
                            }
                        },
                        "required": ["drama_id"]
                    }
                }
            }
        ]

    # LLM工具调用处理
    async def handle_llm_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """处理LLM的工具调用"""
        try:
            if tool_name == "get_categories":
                return await self.get_categories()
            elif tool_name == "search_dramas":
                return await self.search_dramas(arguments["name"])
            elif tool_name == "get_category_dramas":
                return await self.get_category_dramas(
                    arguments["category_id"], 
                    arguments.get("page", 1)
                )
            elif tool_name == "get_recommendations":
                return await self.get_recommendations(
                    arguments.get("category_id"), 
                    arguments.get("size", 10)
                )
            elif tool_name == "get_latest_dramas":
                return await self.get_latest_dramas(arguments.get("page", 1))
            elif tool_name == "get_drama_episodes":
                return await self.get_drama_episodes(
                    arguments["drama_id"], 
                    arguments.get("episode")
                )
            else:
                return f"未知的工具函数: {tool_name}"
        except Exception as e:
            logger.error(f"工具调用异常: {str(e)}")
            return f"工具调用异常: {str(e)}"