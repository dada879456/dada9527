import requests
import logging
from astrbot.api import logger
import astrbot.api.message_components as Comp

class VideoService:
    @staticmethod
    async def get_video_url():
        '''获取/上传跳舞视频到tos'''
        try:
            response = requests.post("https://s.xiaorui-ai.cn:8000/api/v1/tos", data={
                "link": "https://api.yuafeng.cn/API/ly/sjxl.php"
            })
            response.raise_for_status()
            response_json = response.json()
            video_url = response_json.get('data', {}).get('url')
            video_thumb_Url = f'{video_url}?x-tos-process=video/snapshot,t_26000,w_400,h_800,f_jpg'
            return video_url, video_thumb_Url
        except requests.RequestException as e:
            logger.error(f"Failed to get video URL: {e}")
            raise

class ImageService:
    @staticmethod
    async def fetch_and_reply_image(event, api_url: str):
        '''通用的图片API请求和回复逻辑'''
        user_name = event.get_sender_name()
        message_str = event.message_str
        logger.info(f"Received message: {message_str} from {user_name}")

        try:
            response = requests.get(api_url, headers={
                'User-Agent': 'xiaoxiaoapi/1.0.0 (https://xxapi.cn)'
            })
            response.raise_for_status()
            response_json = response.json()
            image_data = response_json.get('data')
            logger.info(f"Image data received: {image_data}")
            yield event.make_result().url_image(image_data)
        except requests.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            yield event.plain_result("Failed to retrieve image data.")

    @staticmethod
    async def fetch_and_reply_image_with_params(event, api_url: str, params: dict, img_key: str = "img"):
        '''通用的带参数图片API请求和回复逻辑'''
        user_name = event.get_sender_name()
        message_str = event.message_str
        logger.info(f"Received message: {message_str} from {user_name}")

        try:
            response = requests.get(api_url, params=params, headers={
                'Content-Type': 'application/x-www-form-urlencoded;charset:utf-8;',
                'User-Agent': 'xiaoxiaoapi/1.0.0 (https://xxapi.cn)'
            })
            response.raise_for_status()
            
            logger.info(f"API response status: {response.status_code}")
            logger.info(f"API response content type: {response.headers.get('content-type', 'unknown')}")
            
            try:
                response_json = response.json()
                image_data = response_json.get(img_key)
                logger.info(f"Image data received: {image_data}")
                if image_data:
                    yield event.make_result().url_image(image_data)
                else:
                    error_msg = response_json.get('msg', '无图片数据')
                    logger.error(f"API error: {error_msg}")
                    yield event.plain_result(f"接口返回异常: {error_msg}")
            except ValueError as e:
                logger.error(f"Invalid JSON response: {e}")
                logger.error(f"Response content (first 200 chars): {response.text[:200]}")
                yield event.plain_result("获取数据失败: API未返回有效JSON数据")
        except requests.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            yield event.plain_result("获取战绩数据失败，请稍后再试。")

class WangZheService:
    @staticmethod
    async def fetch_player_basic_info(player_id, api_key):
        '''获取玩家基本信息'''
        api_url = "https://api.t1qq.com/api/tool/wzrr/wzzl"
        params = {
            "key": api_key,
            "id": player_id
        }
        
        try:
            response = requests.get(api_url, params=params, headers={
                'Content-Type': 'application/x-www-form-urlencoded;charset:utf-8;'
            })
            response.raise_for_status()
            
            logger.info(f"Basic info API response status: {response.status_code}")
            logger.info(f"Basic info API response content type: {response.headers.get('content-type', 'unknown')}")
            
            response_json = response.json()
            if response_json.get('code') == 200:
                return response_json.get('data')
            else:
                logger.error(f"Basic info API error: {response_json.get('msg')}")
                return None
        except Exception as e:
            logger.error(f"Error fetching player basic info: {e}")
            return None

    @staticmethod
    async def fetch_recent_battles(player_id, api_key, option="0"):
        '''获取玩家最近战绩'''
        api_url = "https://api.t1qq.com/api/tool/wzrr/morebattle"
        params = {
            "key": api_key,
            "id": player_id,
            "option": option  # 默认为全部比赛
        }
        
        try:
            response = requests.get(api_url, params=params, headers={
                'Content-Type': 'application/x-www-form-urlencoded;charset:utf-8;'
            })
            response.raise_for_status()
            
            logger.info(f"Recent battles API response status: {response.status_code}")
            
            response_json = response.json()
            if response_json.get('code') == 200:
                return response_json.get('data', {}).get('list', [])
            else:
                logger.error(f"Recent battles API error: {response_json.get('msg')}")
                return []
        except Exception as e:
            logger.error(f"Error fetching recent battles: {e}")
            return []

    @staticmethod
    def format_player_stats(basic_info, recent_battles):
        '''将API数据格式化为易读的文本'''
        if not basic_info:
            return "无法获取玩家信息"
        
        # 提取玩家基本信息
        yd_info = basic_info.get('ydzl', {})
        role_card = basic_info.get('roleCard', {})
        
        nickname = yd_info.get('nickname', '未知')
        user_id = yd_info.get('userId', '未知')
        
        role_name = role_card.get('roleName', '未知')
        server_name = role_card.get('serverName', '未知')
        role_job_name = role_card.get('roleJobName', '未知')
        level = role_card.get('level', 0)
        
        # 提取战斗数据
        fight_power = role_card.get('fightPowerItem', {}).get('value1', '未知')
        total_battle = role_card.get('totalBattleCountItem', {}).get('value1', '未知')
        mvp_num = role_card.get('mvpNumItem', {}).get('value1', '未知')
        win_rate = role_card.get('winRateItem', {}).get('value1', '未知')
        hero_num = role_card.get('heroNumItem', {}).get('value1', '未知')
        skin_num = role_card.get('skinNumItem', {}).get('value1', '未知')
        
        # 构建基本信息文本
        result = [
            f"📊 【{role_name}】的王者荣耀战绩",
            f"🔹 段位: {role_job_name} (Lv.{level})",
            f"🔹 服务器: {server_name}",
            f"🔹 战力: {fight_power}",
            f"🔹 总场次: {total_battle}",
            f"🔹 MVP次数: {mvp_num}",
            f"🔹 胜率: {win_rate}",
            f"🔹 英雄数: {hero_num}",
            f"🔹 皮肤数: {skin_num}",
            "\n⚔️ 最近战绩:",
        ]
        
        # 添加最近战绩信息（最多5场）
        for i, battle in enumerate(recent_battles[:5]):
            try:
                game_time = battle.get('gametime', '未知')
                map_name = battle.get('mapName', '未知')
                hero_id = battle.get('heroId', 0)
                
                kill = battle.get('killcnt', 0)
                dead = battle.get('deadcnt', 0)
                assist = battle.get('assistcnt', 0)
                
                result_type = "胜利" if battle.get('gameresult') == 1 else "失败"
                kda = f"{kill}/{dead}/{assist}"
                
                result.append(f"{i+1}. {game_time} {map_name} - {result_type} KDA: {kda}")
            except Exception as e:
                logger.error(f"Error formatting battle data: {e}")
                continue
        
        return "\n".join(result) 