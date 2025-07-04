"""
数据库操作模块

处理资源搜索插件的数据库操作，包括记录存储和查询等功能
"""

import os
import sqlite3
import logging
from loguru import logger
from typing import List, Optional, Tuple, Any

class DatabaseManager:
    """数据库管理类，负责资源搜索插件的数据库操作"""
    
    def __init__(self, db_name="panDB.db"):
        """初始化数据库连接并创建表
        
        Args:
            db_name: 数据库文件名，默认为panDB.db
        """
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 在utils目录下创建数据库
        self.db_path = os.path.join(current_dir, db_name)
        
        logger.info(f"初始化数据库，路径：{self.db_path}")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """创建必要的数据表"""
        # 文件转存记录表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS pan_files (
            file_id TEXT PRIMARY KEY,
            file_name TEXT,
            file_type INTEGER,
            share_link TEXT,
            pan_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 搜索记录表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            result_count INTEGER,
            search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        self.conn.commit()
        logger.debug("数据库表创建完成")

    def insert_file(self, file_id: str, file_name: str, file_type: int, share_link: str, pan_type: str = "quark") -> bool:
        """插入文件记录
        
        Args:
            file_id: 文件ID
            file_name: 文件名
            file_type: 文件类型（0为文件夹，1为文件）
            share_link: 分享链接
            pan_type: 网盘类型，默认为quark
            
        Returns:
            bool: 操作是否成功
        """
        sql = 'INSERT OR REPLACE INTO pan_files (file_id, file_name, file_type, share_link, pan_type) VALUES (?, ?, ?, ?, ?)'
        try:
            self.cursor.execute(sql, (file_id, file_name, file_type, share_link, pan_type))
            self.conn.commit()
            logger.debug(f"文件 {file_name} 记录已保存")
            return True
        except Exception as e:
            logger.error(f"保存文件记录失败: {e}")
            self.conn.rollback()
            return False

    def delete_file(self, file_id: str) -> bool:
        """删除文件记录
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 操作是否成功
        """
        sql = 'DELETE FROM pan_files WHERE file_id = ?'
        try:
            self.cursor.execute(sql, (file_id,))
            self.conn.commit()
            logger.debug(f"文件ID {file_id} 记录已删除")
            return True
        except Exception as e:
            logger.error(f"删除文件记录失败: {e}")
            self.conn.rollback()
            return False

    def find_share_link_by_name(self, file_name: str) -> Optional[str]:
        """查询文件是否存在
        
        Args:
            file_name: 文件名
            
        Returns:
            Optional[str]: 存在返回分享链接，不存在返回None
        """
        sql = 'SELECT share_link FROM pan_files WHERE file_name = ?'
        try:
            self.cursor.execute(sql, (file_name,))
            result = self.cursor.fetchone()
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"查询文件失败: {e}")
            return None

    def find_expired_resources(self, expired_time: int, pan_type: str = None) -> List[Tuple[Any, ...]]:
        """查询失效资源
        
        Args:
            expired_time: 失效时间（分钟）
            pan_type: 网盘类型，为None时查询所有类型
            
        Returns:
            List[Tuple[Any, ...]]: 失效的资源列表
        """
        if pan_type:
            sql = '''
            SELECT * FROM pan_files 
            WHERE (strftime('%s', 'now') - strftime('%s', created_at)) > ?
            AND pan_type = ?
            '''
            self.cursor.execute(sql, (expired_time * 60, pan_type))
        else:
            sql = '''
            SELECT * FROM pan_files 
            WHERE (strftime('%s', 'now') - strftime('%s', created_at)) > ?
            '''
            self.cursor.execute(sql, (expired_time * 60,))
        
        return self.cursor.fetchall()
    
    def record_search(self, keyword: str, result_count: int) -> bool:
        """记录搜索历史
        
        Args:
            keyword: 搜索关键词
            result_count: 结果数量
            
        Returns:
            bool: 操作是否成功
        """
        sql = 'INSERT INTO search_history (keyword, result_count) VALUES (?, ?)'
        try:
            self.cursor.execute(sql, (keyword, result_count))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"记录搜索历史失败: {e}")
            self.conn.rollback()
            return False
    
    def get_search_history(self, limit: int = 10) -> List[Tuple[Any, ...]]:
        """获取搜索历史
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            List[Tuple[Any, ...]]: 搜索历史列表
        """
        sql = 'SELECT * FROM search_history ORDER BY search_time DESC LIMIT ?'
        self.cursor.execute(sql, (limit,))
        return self.cursor.fetchall()
    
    def close(self):
        """关闭数据库连接"""
        self.cursor.close()
        self.conn.close()
        logger.debug("数据库连接已关闭")

# 单例模式，确保整个应用中只有一个数据库连接
_db_instance = None

def get_db_instance(db_name="panDB.db") -> DatabaseManager:
    """获取数据库管理器实例
    
    Args:
        db_name: 数据库文件名，默认为panDB.db
        
    Returns:
        DatabaseManager: 数据库管理器实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager(db_name)
    return _db_instance 