# -*- coding: utf-8 -*-
"""
LaTeX 到 DOCX 转换工具 - 核心模块

本模块包含处理复杂 LaTeX 项目结构的所有核心功能。
主要职责：
- 递归解析 LaTeX 项目结构
- 合并多个 tex 文件
- 处理 LaTeX 命令和引文
- 调用 Pandoc 生成 DOCX
"""

from .parser import LaTeXProjectParser
from .merger import LaTeXMerger
from .command_handler import LaTeXCommandHandler
from .citation_handler import CitationHandler
from .converter import LaTeXConverter

__all__ = [
    'LaTeXProjectParser',
    'LaTeXMerger',
    'LaTeXCommandHandler',
    'CitationHandler',
    'LaTeXConverter',
]

__version__ = '1.0.0'
