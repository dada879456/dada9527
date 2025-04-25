#!/usr/bin/env python3
from flask import Flask, request, jsonify
from app.astrbot.new_api import add_provider_config, add_platform_config, setup_config
# import docker_start
from app.astrbot import docker_start  # 使用绝对导入路径
import logging
import re  # 添加re模块导入
import json
import os
import threading
import requests
import time
import docker
from app import app, logger
import subprocess
from app.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_CHARSET
from app.astrbot.new_api import restart_core_service,get_qrcode_url_from_logs
import pymysql


PORT_RANGE = list(range(9111, 9200))
PORT_FILE = 'port_status.json'
lock = threading.Lock()

def init_port_file():
    """初始化端口文件（仅首次运行时调用）"""
    if not os.path.exists(PORT_FILE):
        data = {
            "used_ports": [],
            "unused_ports": PORT_RANGE
        }
        with open(PORT_FILE, 'w') as f:
            json.dump(data, f)

def load_ports():
    with open(PORT_FILE, 'r') as f:
        data = json.load(f)
        return set(data["used_ports"]), set(data["unused_ports"])

def save_ports(used_ports, unused_ports):
    data = {
        "used_ports": list(used_ports),
        "unused_ports": list(unused_ports)
    }
    with open(PORT_FILE, 'w') as f:
        json.dump(data, f)

def allocate_port():
    with lock:
        used_ports, unused_ports = load_ports()
        if not unused_ports:
            raise Exception("没有可用端口")
        port = unused_ports.pop()
        used_ports.add(port)
        save_ports(used_ports, unused_ports)
        return str(port)

def release_port(port):
    with lock:
        used_ports, unused_ports = load_ports()
        port = int(port)
        if port in used_ports:
            used_ports.remove(port)
            unused_ports.add(port)
            save_ports(used_ports, unused_ports)

# 程序启动时初始化端口文件
init_port_file()

# 链接MySQL数据库的xiaorui_wen库wechat表
def get_db_connection(user_id, create_time, wechat_url, user_gewe, user_astrbot, user_astrbot_port):
    """
    表结构:
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL,
        carate_time BIGINT NOT NULL,
        user_gewe VARCHAR(100) NOT NULL,
        user_astrbot VARCHAR(100) NOT NULL,
        user_astrbot_port VARCHAR(100) NOT NULL,
        wechat_url VARCHAR(100),
    此接口用于储存用户微信登录二维码的url
    """
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset=MYSQL_CHARSET
        )
        cursor = conn.cursor()
        cursor.execute("INSERT INTO wechat (user_id, create_time, wechat_url, user_gewe, user_astrbot, user_astrbot_port) VALUES (%s, %s, %s, %s, %s, %s)", (user_id, create_time, wechat_url, user_gewe, user_astrbot, user_astrbot_port))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"用户{user_id}的微信登录二维码url已储存，create_time: {create_time}, wechat_url: {wechat_url}")
        return {"code": 200, "message": "Wechat url stored successfully"}
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return {"code": 500, "message": "Database connection error"}

def get_container_ip_addresses(network_name, astrbot_name, gewe_name):
    """
    获取容器在指定网络中的IP地址
    
    参数:
        network_name: Docker网络名称
        astrbot_name: AstrBot容器名称
        gewe_name: Gewechat容器名称
        
    返回:
        dict: 包含astrbot和gewe容器IP地址的字典
    """
    try:
        # 使用Docker SDK检查网络并获取容器信息
        docker_client = docker.from_env()
        network_info = docker_client.api.inspect_network(network_name)
        containers = network_info.get("Containers", {})
        
        # 初始化IP地址
        astrbot_ip = None
        gewe_ip = None
        
        # 遍历容器查找匹配的名称
        for container_id, container_info in containers.items():
            container_name = container_info.get("Name", "")
            if container_name == astrbot_name:
                # 提取IP地址，去掉子网掩码部分
                ip_with_subnet = container_info.get("IPv4Address", "")
                astrbot_ip = re.match(r"([^/]+)", ip_with_subnet).group(1)
            elif container_name == gewe_name:
                # 提取IP地址，去掉子网掩码部分
                ip_with_subnet = container_info.get("IPv4Address", "")
                gewe_ip = re.match(r"([^/]+)", ip_with_subnet).group(1)
        
        return {
            "astrbot_ip": astrbot_ip,
            "gewe_ip": gewe_ip
        }
    except Exception as e:
        logger.error(f"获取容器IP地址失败: {str(e)}")
        return None

@app.route('/start_docker', methods=['POST'])
def start_docker():
    """
    启动Docker容器的API接口，设置提供商和平台配置，并返回微信登录二维码URL
    
    请求参数:
        network_name: Docker网络名称，默认为aibot
        astrbot_name: AstrBot容器名称，默认为astrbot
        gewe_name: Gewechat容器名称，默认为gewe
        port: AstrBot的主端口，默认为6185
        provider_id: 提供商ID，默认为dify_app_default2
        platform_id: 平台ID，默认为gwchat
        skip_config: 是否跳过配置步骤，默认为false
        wait_for_qrcode: 是否等待获取微信登录二维码，默认为true
        api_host: API主机地址，默认为127.0.0.1
    
    返回:
        JSON格式的容器启动和配置结果，包含微信登录二维码URL（如果有）
    """
    try:
        # 获取请求参数
        data = request.json or {}
        
        user_id = data.get('user_id', '12')
        provider_id = data.get('provider_id', 'dify_app_default2')
        platform_id = data.get('platform_id', 'gwchat')
        skip_config = data.get('skip_config', False)
        api_host = data.get('api_host', '127.0.0.1')  # 默认使用本地地址

        # 分配端口
        try:
            port = allocate_port()
        except Exception as e:
            logger.error(f"端口分配失败: {str(e)}")
            return jsonify({
                "code": 500,
                "message": "没有可用端口"
            }), 500


        # 获取当前时间戳
        # timestamp = int(time.time())
        timestamp = 1749999999
        # 生成网络名称、AstrBot名称和Gewechat名称
        network_name = f"{user_id}_network_{timestamp}"
        # AstrBot容器名称
        astrbot_name = f"{user_id}_astrbot_{timestamp}"
        # Gewechat容器名称
        gewe_name = f"{user_id}_gewe_{timestamp}"
        
        # 启动Docker环境
        docker_result = docker_start.start_docker_environment(
            network_name=network_name,
            astrbot_name=astrbot_name,
            gewe_name=gewe_name,
            port=port
        )
        
        # 检查Docker是否启动成功
        if "error" in docker_result or not docker_result.get("success", False):
            logger.error(f"Docker启动失败: {docker_result.get('error', '未知错误')}")
            return jsonify({
                "code": 500,
                "message": "Docker启动失败",
                "data": docker_result
            }), 500
        
        # 获取容器IP地址
        ip_addresses = get_container_ip_addresses(network_name, astrbot_name, gewe_name)
        if not ip_addresses or not ip_addresses.get("astrbot_ip") or not ip_addresses.get("gewe_ip"):
            logger.warning("无法获取容器IP地址，将使用默认IP地址配置")
            gewe_base_url = "http://172.27.0.3:2531"
            astrbot_host = "172.27.0.2"
        else:
            # 使用获取到的IP地址
            gewe_ip = ip_addresses.get("gewe_ip")
            astrbot_ip = ip_addresses.get("astrbot_ip")
            gewe_base_url = f"http://{gewe_ip}:2531"
            astrbot_host = astrbot_ip
            logger.info(f"获取到容器IP地址 - Gewechat: {gewe_ip}, AstrBot: {astrbot_ip}")
            
        # 如果要求跳过配置，则直接返回成功
        if skip_config:
            logger.info("按请求跳过配置步骤")
            return jsonify({
                "code": 200,
                "message": "Docker启动成功，已跳过配置步骤",
                "data": {
                    "docker": docker_result,
                    "ip_addresses": ip_addresses
                }
            }), 200
        
        # Docker启动成功，继续设置配置
        logger.info("Docker启动成功，开始设置提供商和平台配置...")
        
        # 添加一个延迟，等待容器服务完全启动
        logger.info("等待5秒，确保Docker容器服务完全启动...")
        time.sleep(5)
        
        try:
            # 首先设置提供商配置
            provider_result = add_provider_config(
                port=port,
                provider_id=provider_id,
                provider_type="dify",
                api_host=api_host
            )
            
            # 检查提供商配置是否成功
            if provider_result.get("status") == "ok":
                # 提供商配置成功，设置平台配置，使用获取到的IP地址
                platform_result = add_platform_config(
                    port=port,
                    platform_id=platform_id,
                    platform_type="gewechat",
                    base_url=gewe_base_url,
                    host=astrbot_host,
                    api_host=api_host
                )
                
                # 根据平台配置结果返回响应
                if platform_result.get("status") == "ok":
                    logger.info("配置设置成功")
                    try:
                        # 使用new_api中的函数检查并执行更新
                        from app.astrbot.new_api import check_and_perform_update
                        update_result = check_and_perform_update(port=port, api_host=api_host)
                        
                        if update_result and update_result.get("status") == "updated":
                            logger.info(update_result.get("message"))

                            return jsonify({
                                "code": 200,
                                "message": "Docker启动和配置设置成功"
                            }), 200
                        else:  # 没有更新或已是最新版本
                            logger.info("当前已是最新版本或不需要更新，跳过更新步骤")
                            return jsonify({
                                "code": 200,
                                "message": "Docker启动和配置设置成功，当前已是最新版本"
                            }), 200
                    except Exception as update_error:
                        # 更新检查失败，记录错误并跳过更新步骤
                        logger.error(f"检查更新失败: {str(update_error)}，跳过更新步骤")
                        # 仍然需要重启服务
                        
                        return jsonify({
                            "code": 209,
                            "message": "服务器错误"
                        }), 209
                else:
                    # 平台配置失败
                    logger.warning(f"Docker启动和提供商配置成功，但平台配置失败: {platform_result.get('message')}")
                    return jsonify({
                        "code": 208,  # 部分成功
                        "message": "服务器错误"
                    }), 208
            else:
                # 提供商配置失败
                logger.warning(f"Docker启动成功，但提供商配置失败: {provider_result.get('message')}")
                return jsonify({
                    "code": 207,  # 部分成功
                    "message": "服务器错误"
                }), 207
        except Exception as e:
            # 连接错误或其他异常处理
            logger.error(f"API连接失败: {str(e)}")
            return jsonify({
                "code": 206,  # 部分成功
                "message": f"服务器错误"
            }), 206
            
    except Exception as e:
        logger.error(f"处理请求失败: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"服务器错误: {str(e)}",
            "data": None
        }), 500

@app.route('/docker_status/<container_name>', methods=['GET'])
def get_docker_status(container_name):
    """
    获取指定容器的状态
    
    URL参数:
        container_name: 容器名称
    
    返回:
        JSON格式的容器状态信息
    """
    try:
        details = docker_start.get_container_details(container_name)
        if not details:
            return jsonify({
                "code": 500,
                "message": "服务器错误",
                "data": None
            }), 500
        
        details["name"] = container_name
        return jsonify({
            "code": 200,
            "message": "成功",
            "data": details
        }), 200
    except Exception as e:
        logger.error(f"获取容器状态失败: {str(e)}")
        return jsonify({
            "code": 500,
            "message": "服务器错误", 
            "data": None
        }), 500

@app.route('/get_wechat_qrcode_url', methods=['POST'])
def get_wechat_qrcode_url():
    """
    获取微信登录二维码URL
    请求参数:
        container_name: 容器名称（POST参数，必填）
        port: AstrBot服务端口（POST参数，必填）
        api_host: API主机地址（POST参数，可选，默认127.0.0.1）
    返回:
        JSON格式，包含重启结果和二维码URL
    """
    try:
        data = request.json or {}
        container_name = data.get('container_name')
        port = data.get('port')
        api_host = data.get('api_host', '127.0.0.1')
        if not container_name or not port:
            return jsonify({
                "code": 400,
                "message": "参数 container_name 和 port 必填"
            }), 400
        # 1. 清空指定docker日志
        # 2. 重启核心服务
        restart_result = restart_core_service(port=port, api_host=api_host)
        if restart_result.get('status') != 'ok':
            return jsonify({
                "code": 500,
                "message": f"核心服务重启失败: {restart_result.get('message')}",
                "data": restart_result
            }), 500

        # 3. 获取二维码URL
        qrcode_url = get_qrcode_url_from_logs(container_name)
        if qrcode_url:
            return jsonify({
                "code": 200,
                "message": "获取二维码成功",
                "qrcode_url": qrcode_url
            }), 200
        else:
            return jsonify({
                "code": 404,
                "message": "未能从日志中获取到二维码URL，请稍后重试"
            }), 404
    except Exception as e:
        logger.error(f"获取微信二维码接口异常: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"服务器错误: {str(e)}"
        }), 500


