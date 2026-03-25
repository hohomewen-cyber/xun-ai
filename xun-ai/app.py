import streamlit as st
import requests
import webbrowser
import tempfile
import re
import time
from urllib.parse import quote
from openai import OpenAI
import os
from typing import List, Dict, Optional, Tuple
import json

# =========================
# 页面配置（必须在最前面）
# =========================
st.set_page_config(
    page_title="熏赔惨AI全能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# 初始化session state
# =========================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "api_key" not in st.session_state:
    st.session_state.api_key = None
if "client" not in st.session_state:
    st.session_state.client = None
if "mode" not in st.session_state:
    st.session_state.mode = "chat"
if "messages" not in st.session_state:
    st.session_state.messages = []  # 存储显示的消息
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []  # 存储对话上下文
if "current_music_url" not in st.session_state:
    st.session_state.current_music_url = None
if "current_music_name" not in st.session_state:
    st.session_state.current_music_name = ""
if "current_bilibili_url" not in st.session_state:
    st.session_state.current_bilibili_url = None
if "music_player" not in st.session_state:
    st.session_state.music_player = None
if "youtube_player" not in st.session_state:
    st.session_state.youtube_player = None
if "video_player" not in st.session_state:
    st.session_state.video_player = None
if "last_search_results" not in st.session_state:
    st.session_state.last_search_results = []
if "pending_response" not in st.session_state:
    st.session_state.pending_response = None


# =========================
# 登录页面
# =========================
def login_page():
    """显示登录页面"""
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 40px 20px;
            text-align: center;
        }
        .login-title {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 20px;
            color: #1f1f1f;
        }
        .login-subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🤖 熏赔惨AI全能助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">请输入您的API密钥开始使用</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        api_key = st.text_input(
            "DashScope API Key",
            type="password",
            placeholder="密钥：",
            help="请输入您的阿里云DashScope API密钥"
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            submitted = st.form_submit_button("🔑 登录", use_container_width=True)
        with col2:
            st.markdown("[获取API密钥](https://dashscope.console.aliyun.com/apiKey)", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        if api_key and api_key.strip():
            try:
                test_client = OpenAI(
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    api_key=api_key.strip()
                )
                test_response = test_client.chat.completions.create(
                    model="qwen-plus",
                    messages=[{"role": "user", "content": "测试"}],
                    max_tokens=10
                )
                st.session_state.api_key = api_key.strip()
                st.session_state.client = test_client
                st.session_state.authenticated = True

                st.session_state.music_player = NeteaseMusicPlayer()
                st.session_state.youtube_player = YouTubeMusicPlayer()
                st.session_state.video_player = VideoParserPlayer()

                st.rerun()
            except Exception as e:
                st.error(f"❌ API密钥验证失败：{str(e)}\n请检查密钥是否正确")
        else:
            st.warning("⚠️ 请输入API密钥")


# =========================
# 初始化OpenAI客户端
# =========================
def get_client():
    """获取OpenAI客户端"""
    if st.session_state.client is None and st.session_state.api_key:
        st.session_state.client = OpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=st.session_state.api_key
        )
    return st.session_state.client


# =========================
# 缓存装饰器
# =========================
def cache_result(ttl=300):
    """简单的缓存装饰器"""
    cache = {}

    def decorator(func):
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            current_time = time.time()

            if key in cache and current_time - cache[key]['time'] < ttl:
                return cache[key]['value']

            result = func(*args, **kwargs)
            cache[key] = {'value': result, 'time': current_time}
            return result

        return wrapper

    return decorator


# =========================
# 网易云音乐播放器
# =========================
class NeteaseMusicPlayer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.163.com/',
            'Accept': 'application/json, text/plain, */*'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    @cache_result(ttl=180)
    def search_song(self, song_name: str) -> List[Dict]:
        """搜索歌曲"""
        try:
            url = "https://music.163.com/api/search/get/web"
            resp = self.session.post(
                url,
                data={"s": song_name, "type": 1, "limit": 5},
                timeout=5
            )
            resp.raise_for_status()

            songs = resp.json().get("result", {}).get("songs", [])
            results = []
            for s in songs[:3]:
                results.append({
                    "id": s["id"],
                    "name": s["name"],
                    "artist": " / ".join([a["name"] for a in s["artists"]]),
                    "duration": s.get("duration", 0),
                    "album": s.get("album", {}).get("name", "未知专辑")
                })
            return results
        except Exception as e:
            return []

    def get_music_url(self, song_id: int) -> str:
        """获取音乐播放链接"""
        return f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"

    def get_bilibili_url(self, song_name: str, artist: str) -> Optional[str]:
        """获取B站搜索链接"""
        try:
            query = f"{song_name} {artist} 原版"
            search_url = f"https://www.bilibili.com/search?keyword={quote(query)}"
            return search_url
        except Exception:
            return None

    def play_music(self, song_id: int, song_name: str, artist: str) -> Tuple[str, str, Optional[str]]:
        """播放音乐"""
        music_url = self.get_music_url(song_id)
        bilibili_url = self.get_bilibili_url(song_name, artist)

        msg = f"🎵 正在播放：{song_name} - {artist}"
        if bilibili_url:
            msg += f"\n\n💡 **想听原版MV？** [点击在B站观看]({bilibili_url})"

        return music_url, msg, bilibili_url


# =========================
# 视频解析播放器
# =========================
class VideoParserPlayer:
    def __init__(self):
        self.jx_list = [
            "https://jx.xmflv.com/?url=",
            "https://jx.m3u8.tv/jiexi/?url=",
            "https://www.8090g.cn/jiexi/?url=",
            "https://api.17lai.site/?url="
        ]
        self.search_platforms = {
            "腾讯视频": "https://v.qq.com/x/search/?q=",
            "爱奇艺": "https://www.iqiyi.com/search?q=",
            "优酷": "https://www.youku.com/search_video/q_"
        }

    def search_video_links(self, video_name: str) -> Dict[str, str]:
        """搜索视频"""
        links = {}
        for platform, base_url in self.search_platforms.items():
            links[platform] = f"{base_url}{quote(video_name)}"
        return links

    def play_video(self, video_url: str) -> Tuple[str, Optional[str]]:
        """播放视频"""
        if not video_url.startswith("http"):
            return "❌ 请输入正确的视频链接", None

        jx_url = self.jx_list[0] + quote(video_url)
        html_content = self._generate_player_html(jx_url)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(html_content)
            path = f.name

        webbrowser.open_new_tab("file://" + path)
        return f"🎬 正在播放视频（已在浏览器打开）\n\n📺 播放地址：{video_url}", path

    def _generate_player_html(self, video_url: str) -> str:
        """生成播放器HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>视频播放器</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ margin: 0; padding: 0; overflow: hidden; background: #000; }}
                .player-container {{ width: 100%; height: 100vh; position: relative; }}
                iframe {{ width: 100%; height: 100%; border: none; }}
            </style>
        </head>
        <body>
            <div class="player-container">
                <iframe src="{video_url}" allowfullscreen allow="autoplay; fullscreen"></iframe>
            </div>
        </body>
        </html>
        """

    def play_by_name(self, video_name: str) -> str:
        """通过视频名称搜索"""
        search_urls = self.search_video_links(video_name)

        result = f"🔍 搜索到以下平台链接：\n\n"
        for i, (platform, url) in enumerate(search_urls.items(), 1):
            result += f"{i}. **{platform}**：{url}\n"

        result += "\n💡 **使用方法**：直接粘贴你想看的电视完整链接即可播放\n"
        result += f"🎬 **已自动打开腾讯视频搜索页面**"

        webbrowser.open_new_tab(search_urls["腾讯视频"])
        return result


# =========================
# YouTube音乐播放器
# =========================
class YouTubeMusicPlayer:
    def __init__(self):
        self.search_url = "https://www.youtube.com/results?search_query="

    @cache_result(ttl=300)
    def get_first_video(self, query: str) -> Optional[str]:
        """获取第一个YouTube视频ID"""
        headers = {"User-Agent": "Mozilla/5.0"}
        url = self.search_url + quote(query + " official audio")
        try:
            res = requests.get(url, headers=headers, timeout=3)
            res.raise_for_status()
            html = res.text
            video_ids = re.findall(r"watch\?v=(\S{11})", html)
            if video_ids:
                return video_ids[0]
            return None
        except Exception:
            return None

    def play_music(self, song_name: str, artist: str = "") -> Tuple[str, Optional[str]]:
        """播放YouTube音乐"""
        query = f"{song_name} {artist} official audio" if artist else f"{song_name} official audio"
        video_id = self.get_first_video(query)
        if video_id:
            play_url = f"https://www.youtube.com/watch?v={video_id}"
            webbrowser.open_new_tab(play_url)
            return f"🎵 正在YouTube播放：{song_name}（已在浏览器打开）", play_url
        return "❌ 未找到该歌曲", None


# =========================
# 聊天模型（带记忆功能）
# =========================
def call_model_with_memory(user_message: str) -> str:
    """调用千问大模型，带上下文记忆"""
    client = get_client()
    if client is None:
        return "❌ API密钥未配置，请重新登录"

    try:
        messages = []

        system_prompt = """你是一个友好的AI助手，名叫"熏赔惨"。你需要记住之前的对话内容，保持对话的连贯性。
请用中文回答，语气亲切自然，像朋友一样聊天。如果用户提到之前说过的话题，要能够回忆起相关内容。"""
        messages.append({"role": "system", "content": system_prompt})

        recent_history = st.session_state.conversation_history[-10:] if st.session_state.conversation_history else []
        for msg in recent_history:
            messages.append(msg)

        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="qwen-plus",
            messages=messages,
            max_tokens=800,
            temperature=0.7,
            timeout=10
        )

        reply = response.choices[0].message.content

        st.session_state.conversation_history.append({"role": "user", "content": user_message})
        st.session_state.conversation_history.append({"role": "assistant", "content": reply})

        if len(st.session_state.conversation_history) > 20:
            st.session_state.conversation_history = st.session_state.conversation_history[-20:]

        return reply

    except Exception as e:
        return f"模型调用失败: {e}\n请检查API Key配置"


# =========================
# 处理音乐命令
# =========================
def handle_music_command(command: str) -> str:
    """处理音乐相关命令"""
    if st.session_state.music_player is None:
        st.session_state.music_player = NeteaseMusicPlayer()

    command_lower = command.lower()

    if "搜索" in command_lower:
        keyword = command.replace("搜索", "").strip()
        if keyword:
            results = st.session_state.music_player.search_song(keyword)
            if results:
                st.session_state.last_search_results = results
                result_text = f"🎵 找到 {len(results)} 首歌曲：\n\n"
                for i, song in enumerate(results[:3], 1):
                    result_text += f"{i}. **{song['name']}** - {song['artist']}\n"
                    result_text += f"   📀 {song['album']} | ⏱️ {song['duration'] // 1000}秒\n\n"
                result_text += "\n💡 **提示**：输入序号（如：1）即可播放"
                return result_text
            return f"❌ 未找到歌曲：{keyword}"
        return "请输入要搜索的歌曲名，例如：搜索 稻香"

    elif "b站" in command_lower or "bilibili" in command_lower:
        keyword = command.replace("B站", "").replace("b站", "").replace("bilibili", "").strip()
        if keyword:
            bilibili_url = f"https://www.bilibili.com/search?keyword={quote(keyword + ' 原版')}"
            webbrowser.open_new_tab(bilibili_url)
            return f"🎬 已在B站打开「{keyword}」的搜索结果\n\n🔗 链接：{bilibili_url}"
        return "请输入要搜索的内容，例如：B站 稻香"

    elif command_lower.isdigit() or (
            command_lower.startswith("播放") and command_lower.replace("播放", "").strip().isdigit()):
        numbers = re.findall(r'\d+', command)
        if numbers and st.session_state.last_search_results:
            idx = int(numbers[0]) - 1
            if 0 <= idx < len(st.session_state.last_search_results):
                song = st.session_state.last_search_results[idx]
                music_url, msg, bilibili_url = st.session_state.music_player.play_music(
                    song["id"], song["name"], song["artist"]
                )
                st.session_state.current_music_url = music_url
                st.session_state.current_music_name = song["name"]
                st.session_state.current_bilibili_url = bilibili_url
                return msg

    elif "播放" in command_lower:
        song_name = command.replace("播放", "").strip()
        if song_name:
            results = st.session_state.music_player.search_song(song_name)
            if results:
                song = results[0]
                music_url, msg, bilibili_url = st.session_state.music_player.play_music(
                    song["id"], song["name"], song["artist"]
                )
                st.session_state.current_music_url = music_url
                st.session_state.current_music_name = song["name"]
                st.session_state.current_bilibili_url = bilibili_url
                return msg
            return f"❌ 未找到歌曲：{song_name}"

    elif command_lower and st.session_state.last_search_results:
        try:
            idx = int(command_lower) - 1
            if 0 <= idx < len(st.session_state.last_search_results):
                song = st.session_state.last_search_results[idx]
                music_url, msg, bilibili_url = st.session_state.music_player.play_music(
                    song["id"], song["name"], song["artist"]
                )
                st.session_state.current_music_url = music_url
                st.session_state.current_music_name = song["name"]
                st.session_state.current_bilibili_url = bilibili_url
                return msg
        except ValueError:
            pass

    return "💡 **音乐模式使用说明**：\n- 输入「搜索 歌曲名」查找歌曲\n- 输入序号（如：1）播放搜索结果\n- 输入「B站 歌曲名」在B站搜索原版，熏醅惨在左侧给你提供了直接搜索功能，尽情听歌吧！"


# =========================
# 处理视频命令
# =========================
def handle_video_command(command: str) -> str:
    """处理视频相关命令"""
    if st.session_state.video_player is None:
        st.session_state.video_player = VideoParserPlayer()

    command_lower = command.lower()

    if "搜索" in command_lower:
        keyword = command.replace("搜索", "").strip()
        if keyword:
            result = st.session_state.video_player.play_by_name(keyword)
            return result
        return "请输入要搜索的视频名，例如：搜索 逐玉"

    elif command.startswith("http://") or command.startswith("https://"):
        result, html_path = st.session_state.video_player.play_video(command)
        return result

    elif "播放" in command_lower:
        video_name = command.replace("播放", "").strip()
        if video_name:
            return st.session_state.video_player.play_by_name(video_name)

    elif command.strip():
        return st.session_state.video_player.play_by_name(command.strip())

    return "💡 **视频模式使用说明**：\n- 直接粘贴链接即可播放\n- 输入「搜索 视频名」打开各平台搜索页面\n- 或直接输入视频名自动搜索获取到相关完整链接复制到聊天框复制即可！"


# =========================
# 处理聊天命令
# =========================
def handle_chat_command(message: str) -> str:
    """处理聊天命令"""
    return call_model_with_memory(message)


# =========================
# 主应用
# =========================
def main_app():
    """主应用界面"""
    # 侧边栏
    with st.sidebar:
        st.title("熏醅惨🤖 AI全能助手")
        st.markdown("---")

        st.success(f"✅ 已登录")
        st.markdown("---")

        # 模式选择
        st.markdown("### 🎮 选择模式")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("💬 聊天", use_container_width=True, key="btn_chat"):
                st.session_state.mode = "chat"
                st.rerun()

        with col2:
            if st.button("🎵 音乐", use_container_width=True, key="btn_music"):
                st.session_state.mode = "music"
                st.rerun()

        with col3:
            if st.button("🎬 视频", use_container_width=True, key="btn_video"):
                st.session_state.mode = "video"
                st.rerun()

        st.markdown("---")

        # 显示当前模式
        mode_icons = {"chat": "💬", "music": "🎵", "video": "🎬"}
        mode_names = {"chat": "聊天模式", "music": "音乐模式", "video": "视频模式"}
        st.success(f"{mode_icons[st.session_state.mode]} **当前：{mode_names[st.session_state.mode]}**")

        st.markdown("---")

        # 音乐播放器
        if st.session_state.mode == "music":
            st.markdown("### 🎧 音乐播放器")
            if st.session_state.current_music_url:
                st.markdown(f"**🎵 {st.session_state.current_music_name}**")
                st.audio(st.session_state.current_music_url)
                if st.session_state.current_bilibili_url:
                    st.markdown(f"[📺 在B站观看原版MV]({st.session_state.current_bilibili_url})")
            else:
                st.info("暂无播放音乐")

            st.markdown("---")
            st.markdown("### 🔍 快捷搜索")
            quick_search = st.text_input("输入歌曲名", key="quick_search", label_visibility="collapsed",
                                         placeholder="输入歌曲名快速搜索")
            if quick_search and st.session_state.music_player:
                results = st.session_state.music_player.search_song(quick_search)
                if results:
                    for i, song in enumerate(results[:2]):
                        with st.container():
                            st.markdown(f"**{song['name']}**")
                            st.caption(f"{song['artist']} | {song['album']}")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"▶️ 播放", key=f"quick_play_{i}"):
                                    music_url, msg, bilibili_url = st.session_state.music_player.play_music(
                                        song["id"], song["name"], song["artist"]
                                    )
                                    st.session_state.current_music_url = music_url
                                    st.session_state.current_music_name = song["name"]
                                    st.session_state.current_bilibili_url = bilibili_url
                                    st.rerun()
                            with col2:
                                if st.button(f"📺 B站", key=f"quick_bili_{i}"):
                                    bilibili_url = f"https://www.bilibili.com/search?keyword={quote(song['name'] + ' ' + song['artist'] + ' 原版')}"
                                    webbrowser.open_new_tab(bilibili_url)
                                    st.success("已在浏览器打开B站搜索页面")

        # 视频播放器提示
        elif st.session_state.mode == "video":
            st.markdown("### 🎬 视频播放说明")
            st.info("""
            **📖 使用方法：**
            - 直接粘贴链接即可播放（支持腾讯、爱奇艺、优酷）
            - 输入「搜索 视频名」获取各平台链接
            - 直接输入视频名自动搜索
    例如：仙逆133集的完整链接：https://v.qq.com/x/cover/mzc00200aaogpgh/q4102uru4gc.html
            --复制到聊天框发送即可！

            **✨ 功能特点：**
            - 自动获取腾讯、爱奇艺、优酷平台链接
            - 支持多解析源，提高成功率
            - 无需会员即可观看
            """)

        # 聊天模式
        else:
            st.markdown("### 💬 聊天说明")
            st.info("直接输入任何内容，熏醅惨会智能回复你！")

            if st.session_state.conversation_history:
                st.markdown("---")
                st.markdown("### 📝 对话统计")
                st.caption(f"已记录 {len(st.session_state.conversation_history) // 2} 轮对话")

                if st.button("🗑️ 清空对话记忆", use_container_width=True):
                    st.session_state.conversation_history = []
                    st.rerun()

        st.markdown("---")

        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.api_key = None
            st.session_state.client = None
            st.session_state.conversation_history = []
            st.session_state.messages = []
            st.rerun()

        if st.button("🗑️ 清空聊天记录", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # 主界面
    st.markdown(f"### {mode_icons[st.session_state.mode]} {mode_names[st.session_state.mode]}")
    st.markdown("---")

    # 显示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 输入框
    placeholder_texts = {
        "chat": "💬 请输入消息... (熏醅惨祝您使用愉快！)",
        "music": "🎵 输入「搜索 稻香」或输入序号（如：1）播放...",
        "video": "🎬 直接粘贴链接或输入视频名..."
    }

    # 处理用户输入
    if prompt := st.chat_input(placeholder_texts[st.session_state.mode]):
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 生成响应
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                try:
                    if st.session_state.mode == "music":
                        response = handle_music_command(prompt)
                    elif st.session_state.mode == "video":
                        response = handle_video_command(prompt)
                    else:
                        response = handle_chat_command(prompt)

                    st.markdown(response)

                except Exception as e:
                    response = f"⚠️ 处理失败：{str(e)}\n请稍后重试"
                    st.markdown(response)

        # 添加助手消息
        st.session_state.messages.append({"role": "assistant", "content": response})

        # 限制消息数量
        if len(st.session_state.messages) > 30:
            st.session_state.messages = st.session_state.messages[-30:]

        st.rerun()

    # 底部提示
    st.markdown("---")
    if st.session_state.mode == "chat":
        st.caption("💡 **提示**：我会记住我们之前的对话内容，你可以随时引用之前说过的话题！")
    else:
        st.caption(
            "欢迎进入熏醅惨AI智障小助手！💡 **提示**：音乐模式支持网易云音乐播放和B站原版MV搜索，视频模式支持直接粘贴链接播放")


# =========================
# 入口
# =========================
if st.session_state.authenticated:
    main_app()
else:
    login_page()
