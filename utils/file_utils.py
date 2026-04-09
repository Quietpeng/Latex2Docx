# -*- coding: utf-8 -*-
"""
文件操作工具模块

提供通用的文件操作功能：
- 文件搜索
- 文件读写
- 目录操作
- 编码处理
"""

import os
import shutil
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple


def find_tex_files(
    directory: str,
    recursive: bool = True,
    include_subfiles: bool = True
) -> List[str]:
    """
    查找目录中的所有 TeX 文件

    参数：
        directory: 搜索目录
        recursive: 是否递归搜索子目录
        include_subfiles: 是否包含 .tex 和 .latex 文件

    返回：
        TeX 文件路径列表
    """
    tex_files = []

    if not os.path.isdir(directory):
        return tex_files

    extensions = ['.tex', '.latex']
    if include_subfiles:
        extensions.append('.tikz')

    if recursive:
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if Path(file).suffix.lower() in extensions:
                    tex_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                if Path(file).suffix.lower() in extensions:
                    tex_files.append(file_path)

    return sorted(tex_files)


def read_tex_file(file_path: str, encoding: str = 'utf-8') -> Tuple[str, str]:
    """
    读取 TeX 文件

    参数：
        file_path: 文件路径
        encoding: 编码

    返回：
        (文件内容, 检测到的编码)
    """
    # 尝试不同编码
    encodings = [encoding, 'utf-8', 'latin-1', 'cp1252']

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                content = f.read()
            return content, enc
        except Exception:
            continue

    # 最后尝试二进制读取
    with open(file_path, 'rb') as f:
        raw_content = f.read()

    # 尝试解码
    for enc in encodings:
        try:
            return raw_content.decode(enc), enc
        except Exception:
            continue

    return raw_content.decode('utf-8', errors='replace'), 'utf-8'


def write_file(
    file_path: str,
    content: str,
    encoding: str = 'utf-8',
    backup: bool = False
) -> bool:
    """
    写入文件

    参数：
        file_path: 文件路径
        content: 文件内容
        encoding: 编码
        backup: 是否创建备份

    返回：
        成功标志
    """
    try:
        # 创建备份
        if backup and os.path.exists(file_path):
            backup_path = f"{file_path}.bak"
            shutil.copy2(file_path, backup_path)

        # 确保目录存在
        ensure_dir(os.path.dirname(file_path))

        # 写入文件
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)

        return True

    except Exception as e:
        print(f"写入文件失败: {e}")
        return False


def ensure_dir(directory: Optional[str]) -> bool:
    """
    确保目录存在

    参数：
        directory: 目录路径

    返回：
        成功标志
    """
    if not directory:
        return True

    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False


def get_project_root(file_path: str) -> str:
    """
    获取项目根目录（包含 \\documentclass 的文件所在目录）

    参数：
        file_path: 任意项目文件路径

    返回：
        项目根目录路径
    """
    current = os.path.abspath(file_path)

    # 如果是文件，获取其目录
    if os.path.isfile(current):
        current = os.path.dirname(current)

    # 向上查找包含 \\documentclass 的文件
    while current:
        # 检查当前目录
        for file in os.listdir(current):
            if file.endswith('.tex'):
                file_path = os.path.join(current, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(5000)
                    if '\\documentclass' in content:
                        return current
                except Exception:
                    continue

        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # 如果没找到，返回原文件的目录
    return os.path.dirname(os.path.abspath(file_path))


def copy_with_structure(
    source_file: str,
    dest_dir: str,
    base_dir: Optional[str] = None
) -> str:
    """
    复制文件并保持相对目录结构

    参数：
        source_file: 源文件路径
        dest_dir: 目标目录
        base_dir: 基础目录（用于计算相对路径）

    返回：
        目标文件路径
    """
    if base_dir:
        rel_path = os.path.relpath(source_file, base_dir)
    else:
        rel_path = os.path.basename(source_file)

    dest_path = os.path.join(dest_dir, rel_path)
    dest_full = os.path.dirname(dest_path)

    ensure_dir(dest_full)
    shutil.copy2(source_file, dest_path)

    return dest_path


def get_file_type(file_path: str) -> str:
    """
    获取文件类型

    参数：
        file_path: 文件路径

    返回：
        MIME 类型字符串
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'


def get_file_info(file_path: str) -> dict:
    """
    获取文件信息

    参数：
        file_path: 文件路径

    返回：
        文件信息字典
    """
    if not os.path.exists(file_path):
        return {}

    stat = os.stat(file_path)

    return {
        'path': file_path,
        'name': os.path.basename(file_path),
        'directory': os.path.dirname(file_path),
        'size': stat.st_size,
        'modified': stat.st_mtime,
        'type': get_file_type(file_path),
        'is_tex': file_path.endswith('.tex'),
        'is_bib': file_path.endswith('.bib'),
        'is_image': any(file_path.endswith(ext) for ext in ['.png', '.jpg', '.pdf']),
    }


def clean_temp_files(directory: str, pattern: str = '*.tmp') -> int:
    """
    清理临时文件

    参数：
        directory: 目录路径
        pattern: 文件模式

    返回：
        删除的文件数量
    """
    count = 0

    if not os.path.isdir(directory):
        return count

    from pathlib import Path

    for file in Path(directory).glob(pattern):
        try:
            file.unlink()
            count += 1
        except Exception:
            continue

    return count


def create_backup(file_path: str, backup_dir: Optional[str] = None) -> str:
    """
    创建文件备份

    参数：
        file_path: 文件路径
        backup_dir: 备份目录（默认为同一目录）

    返回：
        备份文件路径
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    import time

    # 生成备份文件名
    base, ext = os.path.splitext(os.path.basename(file_path))
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    backup_name = f"{base}_{timestamp}{ext}"

    if backup_dir:
        ensure_dir(backup_dir)
        backup_path = os.path.join(backup_dir, backup_name)
    else:
        backup_path = os.path.join(os.path.dirname(file_path), backup_name)

    shutil.copy2(file_path, backup_path)
    return backup_path
