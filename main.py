import json
from typing import Dict, List, Optional, Any
import aiohttp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, llm_tool


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
    @llm_tool(name="get_drama_categories")
    async def get_drama_categories(self, event: AstrMessageEvent) -> str:
        """获取短剧分类列表。
        
        Returns:
            包含所有短剧分类信息的JSON字符串
        """
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

    @llm_tool(name="search_dramas")
    async def search_dramas(self, event: AstrMessageEvent, name: str) -> str:
        """根据名称搜索短剧。
        
        Args:
            name(string): 要搜索的短剧名称
            
        Returns:
            包含搜索结果的JSON字符串
        """
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

    @llm_tool(name="get_category_hot_dramas")
    async def get_category_hot_dramas(self, event: AstrMessageEvent, category_id: int, page: int = 1) -> str:
        """获取指定分类的热门短剧列表。
        
        Args:
            category_id(number): 短剧分类ID
            page(number): 页码，默认为1
            
        Returns:
            包含分类短剧列表的JSON字符串
        """
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

    @llm_tool(name="get_drama_recommendations")
    async def get_drama_recommendations(self, event: AstrMessageEvent, category_id: Optional[int] = None, size: int = 10) -> str:
        """获取推荐短剧。
        
        Args:
            category_id(number): 可选的分类ID，不指定则获取全部分类的推荐
            size(number): 推荐数量，默认10个
            
        Returns:
            包含推荐短剧的JSON字符串
        """
        params = {"size": str(size)}
        if category_id is not None:
            params["categoryId"] = str(category_id)
            
        result = await self._make_request("/vod/recommend", params)
        if "error" in result:
            return f"获取推荐失败: {result['error']}"
        
        return json.dumps(result, ensure_ascii=False)

    @llm_tool(name="get_latest_dramas")
    async def get_latest_dramas(self, event: AstrMessageEvent, page: int = 1) -> str:
        """获取最新短剧列表。
        
        Args:
            page(number): 页码，默认为1
            
        Returns:
            包含最新短剧列表的JSON字符串
        """
        result = await self._make_request("/vod/latest", {"page": str(page)})
        if "error" in result:
            return f"获取最新短剧失败: {result['error']}"
        
        return json.dumps(result, ensure_ascii=False)

    @llm_tool(name="get_drama_episodes")
    async def get_drama_episodes(self, event: AstrMessageEvent, drama_id: int, episode: int) -> str:
        """获取短剧指定集数的播放地址。注意：此函数只支持获取单集地址，如需获取全集地址请提示用户使用命令 /获取剧集 短剧ID。
        
        Args:
            drama_id(number): 短剧ID
            episode(number): 指定集数（从1开始）
            
        Returns:
            包含单集播放信息的JSON字符串，如果用户想要全集地址则提示使用命令
        """
        # 只支持单集获取
        result = await self._make_request("/vod/parse/single", {
            "id": str(drama_id),
            "episode": episode - 1  # API使用0基索引
        })
        
        if "error" in result:
            return f"获取剧集信息失败: {result['error']}"
        
        return json.dumps(result, ensure_ascii=False)

    # 命令处理器
    @filter.command("短剧分类", "duanju_categories")
    async def cmd_categories(self, event: AstrMessageEvent):
        """获取短剧分类列表"""
        result = await self.get_drama_categories(event)
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
        result = await self.search_dramas(event, drama_name)
        
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
        result = await self.get_drama_recommendations(event, size=5)
        
        try:
            data = json.loads(result)
            if "list" in data and data["list"]:
                text = "🌟 为您推荐的短剧：\n\n"
                for drama in data["list"]:
                    text += f"🎬 {drama.get('name', '未知')}\n"
                    text += f"   📊 评分: {drama.get('score', 'N/A')}\n"
                    text += f"   🆔 ID: {drama.get('id', 'N/A')}\n"
                    text += f"   📅 更新: {drama.get('update_time', 'N/A')}\n\n"
            elif "error" in data:
                text = f"❌ {data['error']}"
            else:
                text = "😔 暂无推荐短剧"
        except:
            text = result
        
        yield event.plain_result(text)


    @filter.command("最新短剧", "duanju_latest")
    async def cmd_latest(self, event: AstrMessageEvent):
        """获取最新短剧"""
        result = await self.get_latest_dramas(event)
        
        try:
            data = json.loads(result)
            if "list" in data and data["list"]:
                text = "🆕 最新短剧：\n\n"
                for drama in data["list"]:
                    text += f"🎬 {drama.get('name', '未知')}\n"
                    text += f"   📊 评分: {drama.get('score', 'N/A')}\n"
                    text += f"   🆔 ID: {drama.get('id', 'N/A')}\n"
                    text += f"   📅 更新: {drama.get('update_time', 'N/A')}\n\n"
                
                # 显示分页信息（如果有）
                if "totalPages" in data and "currentPage" in data:
                    text += f"第 {data.get('currentPage', 1)}/{data.get('totalPages', 1)} 页，共 {data.get('total', 0)} 部短剧"
            elif "error" in data:
                text = f"❌ {data['error']}"
            else:
                text = "😔 暂无最新短剧"
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
        
        result = await self.get_category_hot_dramas(event, category_id, page)
        
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


    @filter.command("获取剧集")
    async def cmd_get_episodes(self, event: AstrMessageEvent):
        """获取剧集播放地址 - 使用方法: /获取剧集 短剧ID [集数]"""
        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result("❌ 请提供短剧ID\n使用方法: /获取剧集 短剧ID [集数]\n不指定集数则获取全集")
            return
        
        try:
            drama_id = int(args[1])
            episode = int(args[2]) if len(args) > 2 else None
        except ValueError:
            yield event.plain_result("❌ 参数格式错误，短剧ID和集数必须是数字")
            return
        
        # 直接调用API而不是通过LLM工具函数
        try:
            if episode is not None:
                # 获取单集地址
                result = await self._make_request("/vod/parse/single", {
                    "id": str(drama_id),
                    "episode": episode - 1  # API使用0基索引
                })
            else:
                # 获取全集地址
                result = await self._make_request("/vod/parse/all", {
                    "id": str(drama_id)
                })
        except Exception as e:
            yield event.plain_result(f"❌ 请求失败: {str(e)}")
            return
        
        if "error" in result:
            yield event.plain_result(f"❌ {result['error']}")
            return
        
        try:
            if episode is not None:
                # 单集结果解析
                video_name = result.get("videoName", "未知短剧")
                episode_info = result.get("episode", {})
                
                text = f"🎬 {video_name} - 第 {episode} 集\n\n"
                
                if "parsedUrl" in episode_info:
                    text += f"📺 播放链接: {episode_info['parsedUrl']}\n"
                    text += f"🏷️ 集数标签: {episode_info.get('label', f'第{episode}集')}\n"
                    
                    parse_info = episode_info.get("parseInfo", {})
                    if "type" in parse_info:
                        text += f"📄 文件类型: {parse_info['type']}\n"
                
                total_episodes = result.get("totalEpisodes")
                if total_episodes:
                    text += f"📊 总集数: {total_episodes}\n"
                
                # 添加短剧描述（截取前100字符）
                description = result.get("description", "")
                if description:
                    desc_short = description[:100] + "..." if len(description) > 100 else description
                    text += f"\n📝 简介: {desc_short}"
                else:
                    text += "\n😔 未找到播放地址"
            else:
                # 全集结果解析
                video_name = result.get("videoName", "未知短剧")
                results = result.get("results", [])
                total_episodes = result.get("totalEpisodes", 0)
                successful_count = result.get("successfulCount", 0)
                failed_count = result.get("failedCount", 0)
                
                text = f"🎬 {video_name} - 全集播放地址\n\n"
                text += f"📊 总集数: {total_episodes}\n"
                text += f"✅ 成功解析: {successful_count} 集\n"
                text += f"❌ 解析失败: {failed_count} 集\n\n"
                
                # 显示前10集的播放地址
                success_episodes = [ep for ep in results if ep.get("status") == "success"]
                display_episodes = success_episodes[:10]
                
                for ep_info in display_episodes:
                    label = ep_info.get("label", f"第{ep_info.get('index', 0) + 1}集")
                    text += f"📺 {label}: {ep_info.get('parsedUrl', 'N/A')}\n"
                
                if len(success_episodes) > 10:
                    text += f"\n... 还有 {len(success_episodes) - 10} 集成功解析的地址\n"
                
                if failed_count > 0:
                    text += f"\n⚠️ 注意: {failed_count} 集解析失败，可能暂时无法播放"
                
                # 添加短剧描述（截取前100字符）
                description = result.get("description", "")
                if description:
                    desc_short = description[:100] + "..." if len(description) > 100 else description
                    text += f"\n\n📝 简介: {desc_short}"
                    
        except Exception as e:
            text = f"❌ 解析响应失败: {str(e)}\n原始数据: {json.dumps(result, ensure_ascii=False)[:200]}..."
        
        yield event.plain_result(text)
        