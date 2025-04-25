from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.core.platform.sources.gewechat.client import SimpleGewechatClient
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import requests
import time
import astrbot.api.message_components as Comp
from .zhuanzai import fetch_jisilu_cb_list
from .services import VideoService, ImageService, WangZheService

@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("黑丝")
    async def heisi_xxapi(self, event: AstrMessageEvent):
        '''获取黑丝图片'''
        async for result in ImageService.fetch_and_reply_image(event, "https://v2.xxapi.cn/api/heisi"):
            yield result

    @filter.command("白丝")
    async def baisi_xxapi(self, event: AstrMessageEvent):
        '''获取白丝图片'''
        async for result in ImageService.fetch_and_reply_image(event, "https://v2.xxapi.cn/api/baisi"):
            yield result

    @filter.command("jk", ignore_case=True)
    async def jk_xxapi(self, event: AstrMessageEvent):
        '''获取jk图片'''
        async for result in ImageService.fetch_and_reply_image(event, "https://v2.xxapi.cn/api/jk"):
            yield result

    @filter.command("原神", ignore_case=True)
    async def yuanshen_xxapi(self, event: AstrMessageEvent):
        '''获取原神cosplay图片'''
        async for result in ImageService.fetch_and_reply_image(event, "https://v2.xxapi.cn/api/yscos"):
            yield result
    
    @filter.command("转债", ignore_case=True)
    async def jls_zz(self, event: AstrMessageEvent):
        '''获取集思录转债信息'''
        result_json = fetch_jisilu_cb_list()
        yield event.plain_result(result_json)

    @filter.command("视频")
    async def video_shipin(self, event: AstrMessageEvent):
        '''获取跳舞视频'''
        video_url, video_thumb_Url = await VideoService.get_video_url()
        chain = [
            Comp.Video.fromURL(url=video_url, cover=video_thumb_Url)
        ]
        yield event.chain_result(chain)
        logger.info(f" video_url={video_url}, thumb_url={video_thumb_Url}, video_duration=20")

    @filter.command("王者战绩", ignore_case=True)
    async def wz_jilu(self, event: AstrMessageEvent):
        '''获取王者荣耀营地战绩信息，格式：/王者战绩 你的id'''
        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("请在指令后输入你的王者营地id，例如：/王者战绩 8888888")
            return
        
        wz_id = args[1]
        logger.info(f"Processing 王者战绩 request for ID: {wz_id}")
        
        # 使用两个API获取王者战绩详细信息
        api_key = "ApdxOeFz7mXSmf6T7QqWvV6qwC"  # 此API密钥可能需要更新
        
        # 获取基本信息和战绩概览
        basic_info = await WangZheService.fetch_player_basic_info(wz_id, api_key)
        if not basic_info:
            yield event.plain_result("获取战绩信息失败，请检查ID是否正确或稍后再试")
            return
            
        # 获取最近战绩
        recent_battles = await WangZheService.fetch_recent_battles(wz_id, api_key)
        
        # 将两个API数据组合成文本信息
        result_text = WangZheService.format_player_stats(basic_info, recent_battles)
        yield event.plain_result(result_text)

    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''



