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
    @llm_tool(name="get_categories")
    async def get_categories(self, event: AstrMessageEvent) -> str:
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

    @llm_tool(name="get_category_dramas")
    async def get_category_dramas(self, event: AstrMessageEvent, category_id: int, page: int = 1) -> str:
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

    @llm_tool(name="get_recommendations")
    async def get_recommendations(self, event: AstrMessageEvent, category_id: Optional[int] = None, size: int = 10) -> str:
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
    async def get_drama_episodes(self, event: AstrMessageEvent, drama_id: int, episode: Optional[int] = None) -> str:
        """获取短剧的剧集播放地址。
        
        Args:
            drama_id(number): 短剧ID
            episode(number): 可选的指定集数，不指定则获取全部集数
            
        Returns:
            包含剧集播放信息的JSON字符串
        """
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
        result = await self.get_categories(event)
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

    @filter.command("短剧帮助", "duanju_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示短剧插件帮助信息"""
        help_text = """📖 短剧搜索插件使用帮助

🎬 **可用命令：**

1️⃣ `/短剧分类` 或 `/duanju_categories`
   - 获取所有短剧分类列表

2️⃣ `/搜索短剧 剧名`
   - 根据名称搜索短剧
   - 示例：/搜索短剧 霸道总裁

3️⃣ `/短剧推荐` 或 `/duanju_recommend`
   - 获取随机推荐的短剧

4️⃣ `/最新短剧` 或 `/duanju_latest`
   - 获取最新上线的短剧

5️⃣ `/分类短剧 分类ID [页码]`
   - 获取指定分类的热门短剧
   - 示例：/分类短剧 1 2

6️⃣ `/获取剧集 短剧ID [集数]`
   - 获取短剧播放地址
   - 示例：/获取剧集 123 5 (获取第5集)
   - 示例：/获取剧集 123 (获取全集)

💡 **小贴士：**
- 短剧ID可从搜索结果中获取
- 分类ID可从分类列表中获取
- 支持LLM智能对话调用这些功能

❓ 如有问题，请联系插件作者 Sugayoiya"""
        
        yield event.plain_result(help_text)

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

    @filter.command("短剧帮助", "duanju_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示短剧插件帮助信息"""
        help_text = """📖 短剧搜索插件使用帮助

🎬 **可用命令：**

1️⃣ `/短剧分类` 或 `/duanju_categories`
   - 获取所有短剧分类列表

2️⃣ `/搜索短剧 剧名`
   - 根据名称搜索短剧
   - 示例：/搜索短剧 霸道总裁

3️⃣ `/短剧推荐` 或 `/duanju_recommend`
   - 获取随机推荐的短剧

4️⃣ `/最新短剧` 或 `/duanju_latest`
   - 获取最新上线的短剧

5️⃣ `/分类短剧 分类ID [页码]`
   - 获取指定分类的热门短剧
   - 示例：/分类短剧 1 2

6️⃣ `/获取剧集 短剧ID [集数]`
   - 获取短剧播放地址
   - 示例：/获取剧集 123 5 (获取第5集)
   - 示例：/获取剧集 123 (获取全集)

💡 **小贴士：**
- 短剧ID可从搜索结果中获取
- 分类ID可从分类列表中获取
- 支持LLM智能对话调用这些功能

❓ 如有问题，请联系插件作者 Sugayoiya"""
        
        yield event.plain_result(help_text)

    @filter.command("短剧推荐", "duanju_recommend")
    async def cmd_recommend(self, event: AstrMessageEvent):
        """获取推荐短剧"""
        result = await self.get_recommendations(event, size=5)
        
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

    @filter.command("短剧帮助", "duanju_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示短剧插件帮助信息"""
        help_text = """📖 短剧搜索插件使用帮助

🎬 **可用命令：**

1️⃣ `/短剧分类` 或 `/duanju_categories`
   - 获取所有短剧分类列表

2️⃣ `/搜索短剧 剧名`
   - 根据名称搜索短剧
   - 示例：/搜索短剧 霸道总裁

3️⃣ `/短剧推荐` 或 `/duanju_recommend`
   - 获取随机推荐的短剧

4️⃣ `/最新短剧` 或 `/duanju_latest`
   - 获取最新上线的短剧

5️⃣ `/分类短剧 分类ID [页码]`
   - 获取指定分类的热门短剧
   - 示例：/分类短剧 1 2

6️⃣ `/获取剧集 短剧ID [集数]`
   - 获取短剧播放地址
   - 示例：/获取剧集 123 5 (获取第5集)
   - 示例：/获取剧集 123 (获取全集)

💡 **小贴士：**
- 短剧ID可从搜索结果中获取
- 分类ID可从分类列表中获取
- 支持LLM智能对话调用这些功能

❓ 如有问题，请联系插件作者 Sugayoiya"""
        
        yield event.plain_result(help_text)

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

    @filter.command("短剧帮助", "duanju_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示短剧插件帮助信息"""
        help_text = """📖 短剧搜索插件使用帮助

🎬 **可用命令：**

1️⃣ `/短剧分类` 或 `/duanju_categories`
   - 获取所有短剧分类列表

2️⃣ `/搜索短剧 剧名`
   - 根据名称搜索短剧
   - 示例：/搜索短剧 霸道总裁

3️⃣ `/短剧推荐` 或 `/duanju_recommend`
   - 获取随机推荐的短剧

4️⃣ `/最新短剧` 或 `/duanju_latest`
   - 获取最新上线的短剧

5️⃣ `/分类短剧 分类ID [页码]`
   - 获取指定分类的热门短剧
   - 示例：/分类短剧 1 2

6️⃣ `/获取剧集 短剧ID [集数]`
   - 获取短剧播放地址
   - 示例：/获取剧集 123 5 (获取第5集)
   - 示例：/获取剧集 123 (获取全集)

💡 **小贴士：**
- 短剧ID可从搜索结果中获取
- 分类ID可从分类列表中获取
- 支持LLM智能对话调用这些功能

❓ 如有问题，请联系插件作者 Sugayoiya"""
        
        yield event.plain_result(help_text)

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
        
        result = await self.get_category_dramas(event, category_id, page)
        
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

    @filter.command("短剧帮助", "duanju_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示短剧插件帮助信息"""
        help_text = """📖 短剧搜索插件使用帮助

🎬 **可用命令：**

1️⃣ `/短剧分类` 或 `/duanju_categories`
   - 获取所有短剧分类列表

2️⃣ `/搜索短剧 剧名`
   - 根据名称搜索短剧
   - 示例：/搜索短剧 霸道总裁

3️⃣ `/短剧推荐` 或 `/duanju_recommend`
   - 获取随机推荐的短剧

4️⃣ `/最新短剧` 或 `/duanju_latest`
   - 获取最新上线的短剧

5️⃣ `/分类短剧 分类ID [页码]`
   - 获取指定分类的热门短剧
   - 示例：/分类短剧 1 2

6️⃣ `/获取剧集 短剧ID [集数]`
   - 获取短剧播放地址
   - 示例：/获取剧集 123 5 (获取第5集)
   - 示例：/获取剧集 123 (获取全集)

💡 **小贴士：**
- 短剧ID可从搜索结果中获取
- 分类ID可从分类列表中获取
- 支持LLM智能对话调用这些功能

❓ 如有问题，请联系插件作者 Sugayoiya"""
        
        yield event.plain_result(help_text)

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
        
        result = await self.get_drama_episodes(event, drama_id, episode)
        
        try:
            data = json.loads(result)
            if "error" in data:
                text = f"❌ {data['error']}"
            elif episode is not None:
                # 单集结果
                if "url" in data:
                    text = f"🎬 短剧ID {drama_id} 第 {episode} 集播放地址：\n\n"
                    text += f"📺 播放链接: {data['url']}\n"
                    if "title" in data:
                        text += f"📝 标题: {data['title']}\n"
                else:
                    text = f"😔 未找到短剧ID {drama_id} 第 {episode} 集的播放地址"
            else:
                # 全集结果
                if "episodes" in data and data["episodes"]:
                    text = f"🎬 短剧ID {drama_id} 全集播放地址：\n\n"
                    for ep_info in data["episodes"][:10]:  # 只显示前10集
                        text += f"第 {ep_info.get('episode', 'N/A')} 集: {ep_info.get('url', 'N/A')}\n"
                    
                    if len(data["episodes"]) > 10:
                        text += f"\n... 还有 {len(data['episodes']) - 10} 集"
                elif "url" in data:
                    text = f"🎬 短剧ID {drama_id} 播放地址：\n\n"
                    text += f"📺 播放链接: {data['url']}\n"
                else:
                    text = f"😔 未找到短剧ID {drama_id} 的播放地址"
        except:
            text = result
        
        yield event.plain_result(text)

    @filter.command("短剧帮助", "duanju_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示短剧插件帮助信息"""
        help_text = """📖 短剧搜索插件使用帮助

🎬 **可用命令：**

1️⃣ `/短剧分类` 或 `/duanju_categories`
   - 获取所有短剧分类列表

2️⃣ `/搜索短剧 剧名`
   - 根据名称搜索短剧
   - 示例：/搜索短剧 霸道总裁

3️⃣ `/短剧推荐` 或 `/duanju_recommend`
   - 获取随机推荐的短剧

4️⃣ `/最新短剧` 或 `/duanju_latest`
   - 获取最新上线的短剧

5️⃣ `/分类短剧 分类ID [页码]`
   - 获取指定分类的热门短剧
   - 示例：/分类短剧 1 2

6️⃣ `/获取剧集 短剧ID [集数]`
   - 获取短剧播放地址
   - 示例：/获取剧集 123 5 (获取第5集)
   - 示例：/获取剧集 123 (获取全集)

💡 **小贴士：**
- 短剧ID可从搜索结果中获取
- 分类ID可从分类列表中获取
- 支持LLM智能对话调用这些功能

❓ 如有问题，请联系插件作者 Sugayoiya"""
        
        yield event.plain_result(help_text)