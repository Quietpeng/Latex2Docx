# -*- coding: utf-8 -*-
"""
路径解析器模块

功能说明：
    解析和规范化 LaTeX 项目中的各种路径：
    - 相对路径
    - 绝对路径
    - 资源路径
    - 图片路径
    - 包含文件路径

使用示例：
    resolver = PathResolver('/path/to/project')
    resolved = resolver.resolve('images/figure.png')
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse


class PathResolver:
    """
    LaTeX 项目路径解析器

    功能：
    1. 解析相对路径为绝对路径
    2. 维护搜索路径列表
    3. 处理各种 LaTeX 路径格式
    4. 检测循环引用
    """

    # LaTeX 路径分隔符（可以是 / 或 \\）
    PATH_SEPARATORS = ['/', '\\']

    def __init__(
        self,
        root_dir: str,
        search_paths: Optional[List[str]] = None
    ):
        """
        初始化路径解析器

        参数：
            root_dir: 项目根目录
            search_paths: 额外的搜索路径列表
        """
        self.root_dir = os.path.abspath(root_dir)
        self.search_paths: List[str] = [self.root_dir]

        if search_paths:
            for path in search_paths:
                abs_path = os.path.abspath(path)
                if abs_path not in self.search_paths:
                    self.search_paths.append(abs_path)

        # 缓存解析结果
        self._cache: Dict[str, str] = {}

    def resolve(
        self,
        path: str,
        source_dir: Optional[str] = None,
        extensions: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        解析路径

        参数：
            path: 要解析的路径
            source_dir: 源文件目录（用于相对路径）
            extensions: 尝试的扩展名列表

        返回：
            解析后的绝对路径，未找到返回 None
        """
        if not path:
            return None

        # 检查缓存
        cache_key = f"{path}|{source_dir}|{','.join(extensions or [])}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 预处理路径
        path = self._normalize_path(path)
        original_path = path

        # 处理 URL（不解析）
        if self._is_url(path):
            self._cache[cache_key] = path
            return path

        # 尝试直接作为绝对路径
        if os.path.isabs(path):
            if os.path.exists(path):
                self._cache[cache_key] = path
                return path

        # 尝试作为相对路径
        # 1. 首先相对于源文件目录
        if source_dir:
            candidate = os.path.join(source_dir, path)
            if os.path.exists(candidate):
                self._cache[cache_key] = os.path.abspath(candidate)
                return self._cache[cache_key]

        # 2. 相对于根目录
        candidate = os.path.join(self.root_dir, path)
        if os.path.exists(candidate):
            self._cache[cache_key] = os.path.abspath(candidate)
            return self._cache[cache_key]

        # 3. 在搜索路径中查找
        for search_dir in self.search_paths:
            # 直接查找
            candidate = os.path.join(search_dir, path)
            if os.path.exists(candidate):
                self._cache[cache_key] = os.path.abspath(candidate)
                return self._cache[cache_key]

            # 尝试添加扩展名
            if extensions:
                for ext in extensions:
                    ext_path = candidate + ext
                    if os.path.exists(ext_path):
                        self._cache[cache_key] = os.path.abspath(ext_path)
                        return self._cache[cache_key]

            # 尝试作为子目录
            base_name = os.path.splitext(path)[0]
            for item in os.listdir(search_dir):
                item_path = os.path.join(search_dir, item)
                if os.path.isdir(item_path):
                    # 检查子目录中的同名文件
                    for sub_item in os.listdir(item_path):
                        if os.path.splitext(sub_item)[0] == os.path.basename(base_name):
                            full_path = os.path.join(item_path, sub_item)
                            if os.path.exists(full_path):
                                self._cache[cache_key] = os.path.abspath(full_path)
                                return self._cache[cache_key]

        # 未找到
        self._cache[cache_key] = None
        return None

    def resolve_many(
        self,
        paths: List[str],
        source_dir: Optional[str] = None,
        extensions: Optional[List[str]] = None
    ) -> List[Optional[str]]:
        """
        批量解析路径

        参数：
            paths: 路径列表
            source_dir: 源文件目录
            extensions: 尝试的扩展名

        返回：
            解析后的路径列表
        """
        return [self.resolve(p, source_dir, extensions) for p in paths]

    def make_relative(
        self,
        path: str,
        base_dir: Optional[str] = None
    ) -> str:
        """
        将绝对路径转换为相对路径

        参数：
            path: 绝对路径
            base_dir: 基准目录（默认为根目录）

        返回：
            相对路径
        """
        if not os.path.isabs(path):
            return path

        base = base_dir or self.root_dir
        return os.path.relpath(path, base)

    def add_search_path(self, path: str) -> None:
        """
        添加搜索路径

        参数：
            path: 要添加的路径
        """
        abs_path = os.path.abspath(path)
        if abs_path not in self.search_paths:
            self.search_paths.append(abs_path)

    def get_relative_paths(
        self,
        file_paths: List[str],
        base_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """
        获取文件路径的相对路径映射

        参数：
            file_paths: 文件路径列表
            base_dir: 基准目录

        返回：
            {绝对路径: 相对路径} 字典
        """
        result = {}
        base = base_dir or self.root_dir

        for path in file_paths:
            if os.path.exists(path):
                result[path] = self.make_relative(path, base)

        return result

    def _normalize_path(self, path: str) -> str:
        """
        规范化路径

        参数：
            path: 原始路径

        返回：
            规范化后的路径
        """
        # 移除空白
        path = path.strip()

        # 统一分隔符
        for sep in self.PATH_SEPARATORS:
            if sep != os.sep:
                path = path.replace(sep, os.sep)

        # 移除重复的分隔符
        while os.sep + os.sep in path:
            path = path.replace(os.sep + os.sep, os.sep)

        # 移除 ./
        path = re.sub(r'^\./', '', path)

        # 处理 ../
        # 简化处理：移除顶层的 ../
        path = re.sub(r'^\.\./', '', path)

        return path

    def _is_url(self, path: str) -> bool:
        """
        检查路径是否是 URL

        参数：
            path: 路径字符串

        返回：
            True 如果是 URL
        """
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def find_file(
        self,
        filename: str,
        search_dirs: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        查找文件

        参数：
            filename: 文件名
            search_dirs: 搜索目录列表

        返回：
            找到的文件路径，未找到返回 None
        """
        dirs = search_dirs or self.search_paths

        for directory in dirs:
            if not os.path.isdir(directory):
                continue

            # 直接查找
            candidate = os.path.join(directory, filename)
            if os.path.exists(candidate):
                return candidate

            # 递归查找子目录
            for root, _, files in os.walk(directory):
                if filename in files:
                    return os.path.join(root, filename)

        return None

    def clear_cache(self) -> None:
        """清除路径解析缓存"""
        self._cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """
        获取解析器统计信息

        返回：
            统计信息字典
        """
        return {
            'root_dir': self.root_dir,
            'search_paths_count': len(self.search_paths),
            'cache_entries': len(self._cache),
            'cache_hits': sum(1 for v in self._cache.values() if v is not None),
        }


def resolve_latex_path(
    latex_cmd: str,
    source_file: str,
    root_dir: str
) -> Optional[str]:
    """
    辅助函数：解析 LaTeX 命令中的路径

    参数：
        latex_cmd: LaTeX 命令（如 \\include{path}）
        source_file: 源文件路径
        root_dir: 项目根目录

    返回：
        解析后的文件路径
    """
    resolver = PathResolver(root_dir)

    # 提取路径
    match = re.search(r'\{([^}]+)\}', latex_cmd)
    if not match:
        return None

    path = match.group(1)
    source_dir = os.path.dirname(source_file)

    return resolver.resolve(path, source_dir, extensions=['.tex', '.latex'])
