# -*- coding: utf-8 -*-
"""
LaTeX 文件合并器模块

功能说明：
    将复杂的 LaTeX 项目合并为单个 tex 文件，以便 Pandoc 处理。
    处理以下命令：
    - \include{filename} - 包含文件并分页
    - \input{filename} - 包含文件不分页
    - \subfiles{filename} - subfiles 包的用法
    - \documentclass + \subfiles - 子文件的特殊处理

使用示例：
    merger = LaTeXMerger(project_info)
    merged_content = merger.merge()
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from .parser import LaTeXProjectParser, LaTeXProjectInfo


class LaTeXMerger:
    """
    LaTeX 文件合并器

    负责将多文件的 LaTeX 项目合并为单个 tex 文件，
    同时处理好各种 include 命令的路径问题。
    """

    # LaTeX 命令的正则表达式
    INCLUDE_PATTERN = re.compile(r'\\include\s*(\[[^\]]*\])?\{([^}]+)\}')
    INPUT_PATTERN = re.compile(r'\\input\s*(\[[^\]]*\])?\{([^}]+)\}')
    SUBFILES_PATTERN = re.compile(r'\\subfiles\s*(\[[^\]]*\])?\{([^}]+)\}')
    SUBFILE_PATTERN = re.compile(r'\\subfile\s*(\[[^\]]*\])?\{([^}]+)\}')
    DOCUMENTCLASS_PATTERN = re.compile(r'\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}')

    # 预amble 标识
    BEGIN_DOCUMENT = re.compile(r'\\begin\{document\}')
    END_DOCUMENT = re.compile(r'\\end\{document\}')

    def __init__(
        self,
        project_info: LaTeXProjectInfo,
        encoding: str = 'utf-8'
    ):
        """
        初始化合并器

        参数：
            project_info: 已解析的项目信息
            encoding: 文本编码
        """
        self.project_info = project_info
        self.encoding = encoding
        self._processed_files: Set[str] = set()
        self._file_contents: Dict[str, str] = {}

    def merge(self) -> str:
        """
        执行合并操作

        返回：
            合并后的单个 tex 文件内容
        """
        if not self.project_info.main_file:
            raise ValueError("未找到主入口文件")

        # 清除状态
        self._processed_files.clear()
        self._file_contents.clear()

        # 执行合并
        merged = self._merge_file(self.project_info.main_file, is_root=True)

        return merged

    def _merge_file(
        self,
        file_path: str,
        is_root: bool = False,
        relative_to: Optional[str] = None
    ) -> str:
        """
        递归合并单个文件

        参数：
            file_path: 要合并的文件路径
            is_root: 是否是根文件
            relative_to: 相对路径的参考文件

        返回：
            合并后的文件内容
        """
        # 标准化路径
        file_path = os.path.normpath(os.path.abspath(file_path))

        # 避免重复处理
        if file_path in self._processed_files:
            return f"% --- 跳过已处理文件: {os.path.basename(file_path)} ---\n"

        self._processed_files.add(file_path)

        # 读取文件内容
        try:
            with open(file_path, 'r', encoding=self.encoding, errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return f"% --- 错误：无法读取文件 {file_path}: {e} ---\n"

        # 检测是否是 subfiles 子文件
        is_subfile = '\\usepackage{subfiles}' in content or '\\subfiles{' in content

        # 根文件保持原样（保留 \documentclass 和 preamble），避免破坏 LaTeX 结构
        if (not is_root) and is_subfile:
            # 子文件需要特殊处理
            content = self._prepare_subfile_content(content)

        # 替换 include/input 命令
        content = self._replace_include_commands(content, file_path)

        # 替换 subfiles 子文件引用
        content = self._replace_subfile_commands(content, file_path)

        return content

    def _prepare_root_content(self, content: str) -> str:
        """
        准备根文件内容

        处理：
        - 移除 documentclass 行（因为会重新定义）
        - 保留必要的包声明
        """
        lines = content.split('\n')
        processed_lines = []
        skip_until_end = False

        for line in lines:
            # 跳过 documentclass 行
            if self.DOCUMENTCLASS_PATTERN.match(line.strip()):
                continue

            # 跳过 subfiles 包（稍后会添加）
            if '\\usepackage{subfiles}' in line:
                continue

            processed_lines.append(line)

        return '\n'.join(processed_lines)

    def _prepare_subfile_content(self, content: str) -> str:
        """
        准备子文件内容

        对于 subfiles 包的子文件：
        - 移除 preamble 中的内容
        - 保留 document 环境中的内容
        """
        lines = content.split('\n')
        processed_lines = []
        in_document = False

        for line in lines:
            # 检测 document 环境
            if '\\begin{document}' in line:
                in_document = True
                continue
            if '\\end{document}' in line:
                in_document = False
                continue

            # 如果不在 document 环境中，跳过（但保留一些必要的定义）
            if not in_document:
                # 保留一些宏定义（根据需要调整）
                if line.strip().startswith('\\newcommand') or \
                   line.strip().startswith('\\renewcommand'):
                    processed_lines.append(line)
                continue

            processed_lines.append(line)

        return '\n'.join(processed_lines)

    def _replace_include_commands(
        self,
        content: str,
        source_file: str
    ) -> str:
        """
        替换 \\include 和 \\input 命令

        参数：
            content: 文件内容
            source_file: 源文件路径（用于解析相对路径）

        返回：
            替换后的内容
        """
        source_dir = os.path.dirname(source_file)

        def replace_include(match):
            optional_arg = match.group(1) or ''
            filename = match.group(2)
            command = match.group(0)  # 完整的匹配

            # 解析文件路径
            file_path = self._resolve_include_path(filename, source_dir)

            if file_path and os.path.exists(file_path):
                # 递归合并包含的文件
                included = self._merge_file(file_path, relative_to=source_file)
                return included
            else:
                # 文件不存在，保留原命令并添加注释
                return f"% [警告] 找不到包含的文件: {filename}\n{command}"

        # 替换 include 命令（会分页）
        content = self.INCLUDE_PATTERN.sub(replace_include, content)

        # 替换 input 命令（不分页）
        content = self.INPUT_PATTERN.sub(replace_include, content)

        return content

    def _replace_subfile_commands(
        self,
        content: str,
        source_file: str
    ) -> str:
        """
        替换 \\subfile 命令（subfiles 包）

        参数：
            content: 文件内容
            source_file: 源文件路径

        返回：
            替换后的内容
        """
        source_dir = os.path.dirname(source_file)

        def replace_subfile(match):
            filename = match.group(1)

            # subfiles 包通常在同目录
            file_path = os.path.join(source_dir, filename)
            if not file_path.endswith('.tex'):
                file_path += '.tex'

            if os.path.exists(file_path):
                included = self._merge_file(file_path, relative_to=source_file)
                return included
            else:
                return f"% [警告] 找不到子文件: {filename}\n\\subfile{{{filename}}}"

        content = self.SUBFILE_PATTERN.sub(replace_subfile, content)
        return content

    def _resolve_include_path(
        self,
        filename: str,
        source_dir: str
    ) -> Optional[str]:
        """
        解析 include/input 文件的路径

        参数：
            filename: 文件名
            source_dir: 源文件所在目录

        返回：
            解析后的完整路径
        """
        # 去除扩展名
        base_name = os.path.splitext(filename)[0]

        # 可能的文件名
        possible_names = [
            filename if filename.endswith('.tex') else f"{filename}.tex",
            filename if filename.endswith('.tex') else f"{filename}.latex",
        ]

        # 可能的查找路径
        search_paths = [
            source_dir,  # 源文件目录
            os.path.join(source_dir, base_name),  # 可能的子目录
            self.project_info.root_dir,  # 项目根目录
        ]

        for search_path in search_paths:
            for name in possible_names:
                candidate = os.path.join(search_path, name)
                if os.path.exists(candidate):
                    return candidate

            # 检查是否作为子目录
            subdir_candidate = os.path.join(search_path, base_name)
            if os.path.isdir(subdir_candidate):
                # 查找目录中的 tex 文件
                for item in os.listdir(subdir_candidate):
                    if item.endswith('.tex'):
                        return os.path.join(subdir_candidate, item)

        return None

    def merge_with_preamble(
        self,
        additional_packages: Optional[List[str]] = None
    ) -> str:
        """
        合并并添加标准 preamble

        参数：
            additional_packages: 额外的包列表

        返回：
            包含完整 preamble 的合并内容
        """
        merged_body = self.merge()

        # 构建 preamble
        preamble = self._build_preamble(additional_packages)

        return f"{preamble}\n\n{merged_body}\n"

    def _build_preamble(
        self,
        additional_packages: Optional[List[str]] = None
    ) -> str:
        """
        构建 LaTeX preamble

        参数：
            additional_packages: 额外的包

        返回：
            preamble 字符串
        """
        packages = [
            '\\usepackage[utf8]{inputenc}',
            '\\usepackage[T1]{fontenc}',
            '\\usepackage{fontspec}',
            '\\usepackage{graphicx}',
            '\\usepackage{hyperref}',
            '\\usepackage{cite}',
            '\\usepackage{amsmath}',
            '\\usepackage{amssymb}',
            '\\usepackage{booktabs}',
            '\\usepackage{longtable}',
            '\\usepackage{array}',
        ]

        # 添加参考文献包
        if self.project_info.bib_files:
            bib_names = [os.path.basename(f) for f in self.project_info.bib_files]
            packages.append(f'\\bibliography{{{",".join(bib_names)}}}')

        # 添加额外包
        if additional_packages:
            packages.extend(additional_packages)

        return '\n'.join(packages)

    def get_merge_report(self) -> str:
        """
        获取合并报告

        返回：
            合并过程的报告字符串
        """
        lines = [
            "=" * 60,
            "LaTeX 文件合并报告",
            "=" * 60,
            f"处理文件数: {len(self._processed_files)}",
            "",
            "已处理的文件:",
        ]

        for file_path in sorted(self._processed_files):
            rel_path = os.path.relpath(file_path, self.project_info.root_dir)
            lines.append(f"  - {rel_path}")

        lines.append("=" * 60)
        return "\n".join(lines)
