import random
import re
import time
import requests
import logging
import os
import json
from loguru import logger

# 导入数据库管理模块（使用绝对导入）
from utils.database import get_db_instance


def get_id_from_url(url):
    """从夸克网盘分享链接中提取分享ID
    Args:
        url: 分享链接，如 https://pan.quark.cn/s/3a1b2c3d
    Returns:
        str: 分享ID, 密码, 父目录ID
    """
    url = url.replace("https://pan.quark.cn/s/", "")
    pattern = r"(\w+)(\?pwd=(\w+))?(#/list/share.*/(\w+))?"
    match = re.search(pattern, url)
    if match:
        pwd_id = match.group(1)
        passcode = match.group(3) if match.group(3) else ""
        pdir_fid = match.group(5) if match.group(5) else 0
        return pwd_id, passcode, pdir_fid
    else:
        return None


def generate_timestamp(length):
    """生成指定长度的时间戳
    Args:
        length: 需要的时间戳长度
    Returns:
        int: 指定长度的时间戳
    """
    timestamps = str(time.time() * 1000)
    return int(timestamps[0:length])


def ad_check(file_name: str, ad_keywords: list) -> bool:
    """检查文件名是否包含广告关键词
    Args:
        file_name: 需要检查的文件名
        ad_keywords: 广告关键词列表
    Returns:
        bool: True表示是广告文件，False表示不是广告文件
    """
    # 将文件名转换为小写进行检查
    file_name_lower = file_name.lower()

    # 检查文件名是否包含广告关键词
    for keyword in ad_keywords:
        if keyword.lower() in file_name_lower:
            return True

    return False


class Quark:
    """夸克网盘操作类，用于自动化处理网盘文件"""

    def __init__(self, conf) -> None:
        """初始化夸克网盘操作类
        Args:
            conf: 配置信息
        """
        # 获取夸克账号配置
        try:
            if "accounts" in conf and "quark" in conf["accounts"]:
                quark_accounts = conf["accounts"]["quark"]
                quark_account = next((acc for acc in quark_accounts if acc.get("enable", True)), None)
            else:
                quark_account = None
            
            # 获取账号信息
            cookie = quark_account.get("cookie", "") if quark_account else ""
            save_dir = quark_account.get("save_dir", "") if quark_account else ""
            
            # 获取广告配置
            ad_conf = conf.get("advertisement", {})
            
            # 设置API请求头
            self.headers = {
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'sec-ch-ua-mobile': '?0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'sec-ch-ua-platform': '"Windows"',
                'origin': 'https://pan.quark.cn',
                'sec-fetch-site': 'same-site',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'referer': 'https://pan.quark.cn/',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'zh-CN,zh;q=0.9',
                'cookie': cookie
            }
            # 初始化数据库管理器
            self.db = get_db_instance()
            # 存储目录ID，默认为None表示根目录
            self.parent_dir = save_dir
            
            # 广告相关配置
            self.insert_ad = quark_account.get("insert_ad", False) if quark_account else False
            self.ad_file_ids = quark_account.get("ad_file_ids", []) if quark_account else []
            self.filter_keywords = ad_conf.get("filter_keywords", [])
            
            # 控制反馈消息的显示方式
            self.msg_first = True
            self.msg_time = time.time()
            
            logger.info("夸克网盘操作类初始化成功")
        except Exception as e:
            logger.error(f"夸克网盘操作类初始化失败: {e}")
            raise

    def del_expired_resources(self, expired_time):
        """删除过期资源
        Args:
            expired_time: 过期时间（分钟）
        """
        try:
            # 查询过期资源
            expired_resources = self.db.find_expired_resources(expired_time, "quark")
            if expired_resources:
                logger.info(f"找到{len(expired_resources)}个过期资源，准备删除")
                for resource in expired_resources:
                    file_id = resource[0]
                    file_name = resource[1]
                    logger.info(f"删除过期资源: {file_name}")
                    # 删除网盘中的文件
                    self.del_file(file_id)
                    # 删除数据库记录
                    self.db.delete_file(file_id)
                logger.info(f"过期资源清理完成")
        except Exception as e:
            logger.error(f"删除过期资源失败: {e}")

    def copy_file(self, file_id, to_dir_id):
        """复制文件到指定目录
        Args:
            file_id: 文件ID
            to_dir_id: 目标目录ID
        Returns:
            bool: 是否复制成功
        """
        try:
            url = "https://drive-pc.quark.cn/1/clouddrive/file/copy"
            querystring = {"pr": "ucpro", "fr": "pc"}
            payload = {
                "fid_list": [file_id],
                "to_pdir_fid": to_dir_id
            }

            response = requests.post(url, json=payload, headers=self.headers, params=querystring, timeout=10).json()
            if response.get("code") == 0:
                logger.info(f"文件复制成功")
                return True
            else:
                logger.error(f"文件复制失败: {response}")
                return False
        except Exception as e:
            logger.error(f"文件复制请求失败: {e}")
            return False

    def move_file(self, file_id, to_dir_id):
        """移动文件到指定目录
        Args:
            file_id: 文件ID
            to_dir_id: 目标目录ID
        Returns:
            bool: 是否移动成功
        """
        try:
            url = "https://drive-pc.quark.cn/1/clouddrive/file/move"
            querystring = {"pr": "ucpro", "fr": "pc"}
            payload = {
                "fid_list": [file_id],
                "to_pdir_fid": to_dir_id
            }

            response = requests.post(url, json=payload, headers=self.headers, params=querystring, timeout=10).json()
            if response.get("code") == 0:
                logger.info(f"文件移动成功")
                return True
            else:
                logger.error(f"文件移动失败: {response}")
                return False
        except Exception as e:
            logger.error(f"文件移动请求失败: {e}")
            return False

    def store(self, url: str):
        """保存分享链接中的文件到自己的网盘
        Args:
            url: 分享链接
        Returns:
            tuple: (是否是新文件, 文件名, 分享链接)
        """
        # 获取分享ID和token
        pwd_id, passcode, pdir_fid = get_id_from_url(url)
        is_sharing, stoken = self.get_stoken(pwd_id, passcode)
        detail = self.detail(pwd_id, stoken, pdir_fid)
        file_name = detail.get('title')

        # 检查文件是否已存在
        share_link = self.db.find_share_link_by_name(file_name)
        file_not_exist = share_link is None
        if file_not_exist:
            first_id = detail.get("fid")
            share_fid_token = detail.get("share_fid_token")
            file_type = detail.get("file_type")

            # 设置保存目录
            other_args = {}
            if self.parent_dir:
                other_args['to_pdir_fid'] = self.parent_dir

            # 保存文件并获取新的文件ID
            try:
                task = self.save_task_id(pwd_id, stoken, first_id, share_fid_token, **other_args)
                data = self.task(task)
                file_id = data.get("data").get("save_as").get("save_as_top_fids")[0]
            except Exception as e:
                logger.error(f"转存资源失败: {e}")
                raise

            # 如果是文件夹并且启用了广告过滤，检查并删除广告文件
            if not file_type and self.filter_keywords:
                dir_file_list = self.get_dir_file(file_id)
                self.del_ad_file(dir_file_list)
            
            # 设置分享的文件ID
            share_id = file_id
            
            # 创建分享并获取新的分享链接
            try:
                share_task_id = self.share_task_id(share_id, file_name)
                share_id = self.task(share_task_id).get("data").get("share_id")
                share_link = self.get_share_link(share_id)
            except Exception as e:
                logger.error(f"资源分享失败: {e}")
                raise

            # 保存记录到数据库
            self.db.insert_file(file_id, file_name, file_type, share_link, "quark")
        
        return file_not_exist, file_name, share_link

    def get_stoken(self, pwd_id: str, passcode=""):
        """获取分享文件的stoken
        Args:
            pwd_id: 分享ID
            passcode: 密码
        Returns:
            tuple: (是否成功, stoken值或错误信息)
        """
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token"
        querystring = {"pr": "ucpro", "fr": "pc"}
        payload = {"pwd_id": pwd_id, "passcode": passcode}

        try:
            response = requests.post(url, json=payload, headers=self.headers, params=querystring, timeout=10)
            response_json = response.json()

            if response_json.get("code") == 0 or response_json.get("status") == 200:
                if response_json.get("data") and "stoken" in response_json["data"]:
                    return True, response_json["data"]["stoken"]
                else:
                    return False, "获取stoken失败: 响应中没有stoken"
            else:
                return False, response_json.get("message", "未知错误")
        except Exception as e:
            logger.error(f"获取stoken请求失败: {e}")
            return False, str(e)

    def detail(self, pwd_id, stoken, pdir_fid, _fetch_share=0):
        """获取分享文件详情
        Args:
            pwd_id: 分享ID
            stoken: 分享token
            pdir_fid: 父目录ID
            _fetch_share: 是否获取分享信息
        Returns:
            dict: 文件详情
        """
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": pdir_fid,
            "force": "0",
            "_page": 1,
            "_size": "50",
            "_fetch_banner": "0",
            "_fetch_share": _fetch_share,
            "_fetch_total": "1",
            "_sort": "file_type:asc,updated_at:desc",
        }
        response = requests.request("GET", url=url, headers=self.headers, params=params)
        id_list = response.json().get("data").get("list")[0]
        if id_list:
            return {
                "title": id_list.get("file_name"),
                "file_type": id_list.get("file_type"),
                "fid": id_list.get("fid"),
                "pdir_fid": id_list.get("pdir_fid"),
                "share_fid_token": id_list.get("share_fid_token")
            }

    def save_task_id(self, pwd_id, stoken, first_id, share_fid_token, to_pdir_fid=0):
        """创建保存文件的任务
        Args:
            pwd_id: 分享ID
            stoken: 安全token
            first_id: 文件ID
            share_fid_token: 分享文件token
            to_pdir_fid: 目标文件夹ID，默认为0（根目录）
        Returns:
            str: 任务ID
        """
        url = "https://drive.quark.cn/1/clouddrive/share/sharepage/save"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": generate_timestamp(13),
        }
        data = {
            "fid_list": [first_id],
            "fid_token_list": [share_fid_token],
            "to_pdir_fid": to_pdir_fid,
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "scene": "link"
        }

        try:
            response = requests.request("POST", url, json=data, headers=self.headers, params=params, timeout=10)
            response_json = response.json()

            if response_json.get("code") == 0 or response_json.get("status") == 200:
                if response_json.get("data") and "task_id" in response_json["data"]:
                    logger.info(f"获取任务ID成功: {response_json['data']['task_id']}")
                    return response_json["data"]["task_id"]
                else:
                    logger.error(f"获取任务ID失败: 响应中没有task_id")
                    return None
            else:
                logger.error(f"获取任务ID失败: {response_json.get('message')}")
                return None
        except Exception as e:
            logger.error(f"获取任务ID请求失败: {e}")
            return None

    def task(self, task_id):
        """执行并监控任务状态
        Args:
            task_id: 任务ID
        Returns:
            dict: 任务执行结果
        """
        while True:
            url = f"https://drive-pc.quark.cn/1/clouddrive/task?pr=ucpro&fr=pc&uc_param_str=&task_id={task_id}&retry_index={0}&__dt=21192&__t={generate_timestamp(13)}"
            response = requests.get(url, headers=self.headers).json()
            if response.get('status') != 200:
                raise Exception(f"请求失败，状态码：{response.get('status')}，消息：{response.get('message')}")
            # 状态码2表示任务完成
            if response.get('data').get('status') == 2:
                return response

    def share_task_id(self, file_id, file_name):
        """创建文件分享任务
        Args:
            file_id: 文件ID
            file_name: 文件名
        Returns:
            str: 分享任务ID
        """
        url = "https://drive-pc.quark.cn/1/clouddrive/share?pr=ucpro&fr=pc&uc_param_str="
        
        # 准备文件ID列表
        if isinstance(file_id, list):
            fid_list = file_id
        else:
            fid_list = [file_id]
            
        # 如果启用了广告插入功能，并且有广告文件ID，则添加广告文件到分享列表中
        if self.insert_ad and self.ad_file_ids:
            for ad_id in self.ad_file_ids:
                if ad_id not in fid_list:
                    fid_list.append(ad_id)
        
        data = {
            "fid_list": fid_list,
            "title": file_name,
            "url_type": 1,  # 链接类型
            "expired_type": 1  # 过期类型
        }
        response = requests.request("POST", url=url, json=data, headers=self.headers)
        return response.json().get("data").get("task_id")

    def get_share_link(self, share_id):
        """获取分享链接
        Args:
            share_id: 分享ID
        Returns:
            str: 分享链接
        """
        url = "https://drive-pc.quark.cn/1/clouddrive/share/password?pr=ucpro&fr=pc&uc_param_str="
        data = {"share_id": share_id}
        response = requests.post(url=url, json=data, headers=self.headers)
        return response.json().get("data").get("share_url")

    def get_all_file(self):
        """获取所有文件列表
        Returns:
            list: 文件列表
        """
        logger.debug("正在获取所有文件")
        # 调用get_dir_file方法获取根目录(0)下的所有文件
        return self.get_dir_file(0)

    def get_dir_file(self, dir_id) -> list:
        """获取目录下所有文件
        Args:
            dir_id: 目录ID，0表示根目录
        Returns:
            list: 文件列表
        """
        url = f"https://drive-pc.quark.cn/1/clouddrive/file/sort"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "pdir_fid": dir_id,
            "_page": 1,
            "_size": 50,
            "_fetch_total": 1,
            "_fetch_sub_dirs": 0,
            "_sort": "updated_at:desc"
        }
        response = requests.get(url=url, headers=self.headers, params=params)
        return response.json().get('data').get('list')

    def del_file(self, file_id):
        """删除文件
        Args:
            file_id: 文件ID
        Returns:
            bool: 是否删除成功
        """
        url = "https://drive-pc.quark.cn/1/clouddrive/file/delete"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": ""
        }
        data = {
            "action_type": 2,  # 删除操作类型
            "filelist": [file_id],
            "exclude_fids": []
        }
        response = requests.post(url=url, json=data, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json().get("data").get("task_id")
        return False

    def del_ad_file(self, file_list):
        """删除广告文件
        Args:
            file_list: 文件列表
        Returns:
            bool: 是否成功
        """
        logger.debug("删除可能存在广告的文件")
        try:
            for file in file_list:
                file_name = file.get("file_name", "")
                file_id = file.get("fid", "")

                if ad_check(file_name, self.filter_keywords):
                    logger.info(f"删除广告文件: {file_name}")
                    self.del_file(file_id)
            return True
        except Exception as e:
            logger.error(f"删除广告文件失败: {e}")
            return False

    def search_file(self, file_name):
        """搜索文件
        Args:
            file_name: 文件名
        Returns:
            list: 文件列表
        """
        url = "https://drive-pc.quark.cn/1/clouddrive/file/search"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "_page": 1,
            "_size": 50,
            "_fetch_total": 1,
            "_sort": "file_type:desc,updated_at:desc",
            "_is_hl": 1,
            "q": file_name
        }
        response = requests.get(url=url, headers=self.headers, params=params)
        return response.json().get('data').get('list')

    def mkdir(self, dir_path, pdir_fid="0"):
        """创建目录
        Args:
            dir_path: 目录路径，例如"foo/bar"
            pdir_fid: 父目录ID，默认为根目录
        Returns:
            str: 创建的目录ID
        """
        url = f"https://drive-pc.quark.cn/1/clouddrive/file"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {
            "pdir_fid": pdir_fid,
            "file_name": "",
            "dir_path": dir_path,
            "dir_init_lock": False,
        }
        response = requests.post(url=url, headers=self.headers, params=querystring, json=payload)
        return response.json().get('fid')
