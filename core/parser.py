# -*- coding: utf-8 -*-
"""
LaTeX 项目解析器模块

功能说明：
    递归扫描 LaTeX 项目目录结构，自动识别：
    - 主入口 tex 文件（包含 \documentclass 的文件）
    - 章节文件和子文件
    - 参考文献文件（.bib）
    - 图片文件
    - 配置文件

使用示例：
    parser = LaTeXProjectParser('/path/to/latex/project')
    project_info = parser.parse()
    print(project_info.main_file)
    print(project_info.bib_files)
    print(project_info.chapter_files)
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class LaTeXProjectInfo:
    """LaTeX 项目信息数据类"""
    # 项目根目录
    root_dir: str
    # 主入口文件路径
    main_file: Optional[str] = None
    # 所有 tex 文件列表
    tex_files: List[str] = field(default_factory=list)
    # 章节文件列表（被 include/input 的文件）
    chapter_files: List[str] = field(default_factory=list)
    # 参考文献文件列表
    bib_files: List[str] = field(default_factory=list)
    # 图片文件目录
    image_dirs: List[str] = field(default_factory=list)
    # 图片文件列表
    image_files: List[str] = field(default_factory=list)
    # 样式文件列表
    sty_files: List[str] = field(default_factory=list)
    # cls 文件列表
    cls_files: List[str] = field(default_factory=list)
    # 项目中所有的目录
    all_dirs: List[str] = field(default_factory=list)
    # 文件依赖关系 {文件名: [依赖的文件列表]}
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    # 编码类型（通常为 utf-8 或 latin1）
    encoding: str = 'utf-8'


class LaTeXProjectParser:
    """
    LaTeX 项目解析器

    该解析器能够：
    1. 递归扫描项目目录
    2. 自动识别主入口文件
    3. 解析文件间的依赖关系（include/input/subfiles）
    4. 收集所有相关资源文件（bib、图片、样式文件等）
    """

    # 主文档标识：包含 \documentclass 的文件
    DOCUMENTCLASS_PATTERN = re.compile(r'\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}')

    # include 命令：\include{filename} - 会分页
    INCLUDE_PATTERN = re.compile(r'\\include\s*\{([^}]+)\}')

    # input 命令：\input{filename} - 不分页
    INPUT_PATTERN = re.compile(r'\\input\s*\{([^}]+)\}')

    # subfiles 包的命令
    SUBFILES_PATTERN = re.compile(r'\\subfiles(?:\[[^\]]*\])?\{([^}]+)\}')
    SUBFILE_INCLUDE_PATTERN = re.compile(r'\\subfile(?:\[[^\]]*\])?\{([^}]+)\}')

    # bibliography 命令
    BIB_PATTERN = re.compile(r'\\bibliography\s*\{([^}]+)\}')
    BIBSTYLE_PATTERN = re.compile(r'\\bibliographystyle\s*\{([^}]+)\}')

    # addbibresource 命令（biblatex 用法）
    ADDBIBRESOURCE_PATTERN = re.compile(r'\\addbibresource\{([^}]+)\}')

    # graphicspath 命令
    GRAPHICSPATH_PATTERN = re.compile(r'\\graphicspath\s*\{([^}]+)\}')

    # includegraphics 命令
    INCLUDEGRAPHICS_PATTERN = re.compile(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}')

    # 图片扩展名
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf', '.eps', '.svg', '.gif', '.bmp'}

    # tex 文件扩展名
    TEX_EXTENSIONS = {'.tex', '.tikz'}
    BIB_EXTENSIONS = {'.bib'}
    STYLE_EXTENSIONS = {'.sty'}
    CLASS_EXTENSIONS = {'.cls'}

    def __init__(self, project_path: str, encoding: str = 'utf-8'):
        """
        初始化解析器

        参数：
            project_path: LaTeX 项目根目录路径
            encoding: 文本文件编码，默认 utf-8
        """
        self.project_path = Path(project_path).resolve()
        self.encoding = encoding
        self.project_info: Optional[LaTeXProjectInfo] = None
        self._visited_files: Set[str] = set()

    def parse(self) -> LaTeXProjectInfo:
        """
        解析 LaTeX 项目

        返回：
            LaTeXProjectInfo: 包含项目所有信息的数据对象
        """
        # 重置状态
        self._visited_files = set()

        # 初始化项目信息
        self.project_info = LaTeXProjectInfo(
            root_dir=str(self.project_path),
            encoding=self.encoding
        )

        # 步骤 1: 扫描所有文件
        self._scan_files()

        # 步骤 2: 识别主入口文件
        self._identify_main_file()

        # 步骤 3: 解析文件依赖关系
        self._parse_dependencies()

        # 步骤 4: 收集图片文件
        self._collect_images()

        return self.project_info

    def _scan_files(self) -> None:
        """扫描项目目录，收集所有相关文件"""
        tex_files = []
        bib_files = []
        image_files = []
        sty_files = []
        cls_files = []
        all_dirs = []

        for root, dirs, files in os.walk(self.project_path):
            # 记录目录
            all_dirs.append(root)

            # 跳过隐藏目录和常见的非内容目录
            dirs[:] = [d for d in dirs if not d.startswith('.')
                      and d not in {'build', 'out', 'tmp', '__pycache__'}]

            for file in files:
                file_path = os.path.join(root, file)
                ext = Path(file).suffix.lower()

                if ext in self.TEX_EXTENSIONS:
                    tex_files.append(file_path)
                elif ext in self.BIB_EXTENSIONS:
                    bib_files.append(file_path)
                elif ext in self.STYLE_EXTENSIONS:
                    sty_files.append(file_path)
                elif ext in self.CLASS_EXTENSIONS:
                    cls_files.append(file_path)
                elif ext in self.IMAGE_EXTENSIONS:
                    image_files.append(file_path)

        self.project_info.tex_files = tex_files
        self.project_info.bib_files = bib_files
        self.project_info.image_files = image_files
        self.project_info.sty_files = sty_files
        self.project_info.cls_files = cls_files
        self.project_info.all_dirs = all_dirs

    def _identify_main_file(self) -> None:
        """识别主入口文件（包含 \\documentclass 的文件）"""
        main_candidates = []

        for tex_file in self.project_info.tex_files:
            try:
                with open(tex_file, 'r', encoding=self.encoding, errors='ignore') as f:
                    content = f.read(10000)  # 读取前 10KB 足以判断

                    if self.DOCUMENTCLASS_PATTERN.search(content):
                        main_candidates.append(tex_file)
            except Exception:
                continue

        # 如果找到多个候选，优先选择根目录下的
        if len(main_candidates) > 1:
            for candidate in main_candidates:
                if os.path.basename(candidate) in ['main.tex', 'paper.tex', 'thesis.tex', 'article.tex']:
                    self.project_info.main_file = candidate
                    return

        # 选择最短路径的（最可能是根目录的）
        if main_candidates:
            self.project_info.main_file = min(main_candidates, key=len)
        else:
            # 如果没有找到 documentclass，选择最大的 tex 文件
            if self.project_info.tex_files:
                self.project_info.main_file = max(
                    self.project_info.tex_files,
                    key=lambda f: os.path.getsize(f)
                )

    def _parse_dependencies(self) -> None:
        """解析所有 tex 文件的依赖关系"""
        for tex_file in self.project_info.tex_files:
            self._parse_single_file_dependencies(tex_file)

    def _parse_single_file_dependencies(self, tex_file: str) -> Dict[str, List[str]]:
        """
        解析单个 tex 文件的依赖关系

        参数：
            tex_file: tex 文件路径

        返回：
            依赖的文件路径列表
        """
        if tex_file in self._visited_files:
            return self.project_info.dependencies.get(tex_file, [])

        self._visited_files.add(tex_file)

        dependencies = []

        try:
            with open(tex_file, 'r', encoding=self.encoding, errors='ignore') as f:
                content = f.read()

            # 检测是否使用 subfiles 包
            is_subfile = '\\usepackage{subfiles}' in content or self.SUBFILES_PATTERN.search(content)

            # 解析各种 include/input 命令
            for pattern, name in [
                (self.INCLUDE_PATTERN, 'include'),
                (self.INPUT_PATTERN, 'input'),
                (self.SUBFILE_INCLUDE_PATTERN, 'subfile'),
            ]:
                for match in pattern.finditer(content):
                    dep_file = self._resolve_file_path(
                        match.group(1),
                        tex_file,
                        extension='.tex'
                    )
                    if dep_file and os.path.exists(dep_file):
                        dependencies.append(dep_file)
                        # 递归解析依赖
                        self._parse_single_file_dependencies(dep_file)

            # 解析参考文献命令
            for pattern in [self.BIB_PATTERN, self.ADDBIBRESOURCE_PATTERN]:
                for match in pattern.finditer(content):
                    bib_files_str = match.group(1)
                    # 支持多个 bib 文件用逗号分隔
                    for bib_name in bib_files_str.split(','):
                        bib_name = bib_name.strip()
                        bib_file = self._resolve_file_path(bib_name, tex_file, extension='.bib')
                        if bib_file and os.path.exists(bib_file):
                            if bib_file not in self.project_info.bib_files:
                                self.project_info.bib_files.append(bib_file)

            # 解析图片路径命令
            for match in self.GRAPHICSPATH_PATTERN.finditer(content):
                path_content = match.group(1)
                # 解析路径中的多个目录
                dirs = re.findall(r'\{([^}]+)\}', path_content)
                for img_dir in dirs:
                    full_img_dir = self._resolve_path(img_dir, tex_file)
                    if full_img_dir and os.path.isdir(full_img_dir):
                        if full_img_dir not in self.project_info.image_dirs:
                            self.project_info.image_dirs.append(full_img_dir)

        except Exception:
            pass

        self.project_info.dependencies[tex_file] = dependencies
        return dependencies

    def _resolve_file_path(
        self,
        filename: str,
        source_file: str,
        extension: str = ''
    ) -> Optional[str]:
        """
        解析文件路径

        参数：
            filename: 文件名（不含扩展名或含扩展名）
            source_file: 引用此文件的源文件路径
            extension: 要添加的扩展名

        返回：
            解析后的完整文件路径
        """
        # 去除可能的扩展名
        base_name = os.path.splitext(filename)[0]

        # 如果指定了扩展名，添加它
        if extension and not base_name.endswith(extension):
            base_name += extension

        # 首先在源文件同目录查找
        source_dir = os.path.dirname(source_file)

        # 可能的查找路径
        search_paths = [
            source_dir,                          # 源文件目录
            os.path.join(source_dir, base_name), # 源文件目录下的子目录
            self.project_path,                   # 项目根目录
            os.path.join(self.project_path, base_name),  # 项目根目录下的子目录
        ]

        for search_dir in search_paths:
            if os.path.isdir(search_dir):
                # 在目录中查找同名文件
                for file in os.listdir(search_dir):
                    if os.path.splitext(file)[0] == os.path.splitext(base_name)[0]:
                        return os.path.join(search_dir, file)

            # 直接作为文件查找
            candidate = search_dir if os.path.isdir(search_dir) else search_dir
            if os.path.isfile(candidate):
                return candidate

        return None

    def _resolve_path(self, path_str: str, source_file: str) -> str:
        """解析相对路径"""
        source_dir = os.path.dirname(source_file)
        return os.path.normpath(os.path.join(source_dir, path_str))

    def _collect_images(self) -> None:
        """收集项目中的所有图片文件"""
        # 从 graphicspath 命令收集
        # 从 includegraphics 命令收集
        for tex_file in self.project_info.tex_files:
            try:
                with open(tex_file, 'r', encoding=self.encoding, errors='ignore') as f:
                    content = f.read()

                # 收集 includegraphics 引用的图片
                for match in self.INCLUDEGRAPHICS_PATTERN.finditer(content):
                    img_name = match.group(1)
                    img_path = self._resolve_file_path(img_name, tex_file)
                    if img_path and os.path.exists(img_path):
                        if img_path not in self.project_info.image_files:
                            self.project_info.image_files.append(img_path)
            except Exception:
                continue

    def get_file_order(self) -> List[str]:
        """
        获取文件处理顺序（基于依赖关系）

        返回：
            按正确顺序排列的文件列表
        """
        if not self.project_info or not self.project_info.main_file:
            return self.project_info.tex_files if self.project_info else []

        ordered = []
        visited = set()

        def visit(file_path):
            if file_path in visited:
                return
            visited.add(file_path)

            # 先处理依赖
            for dep in self.project_info.dependencies.get(file_path, []):
                visit(dep)

            if file_path not in ordered:
                ordered.append(file_path)

        visit(self.project_info.main_file)

        # 添加未被访问的文件
        for tex_file in self.project_info.tex_files:
            if tex_file not in visited:
                ordered.append(tex_file)

        return ordered

    def print_project_structure(self) -> str:
        """
        打印项目结构信息

        返回：
            项目结构的字符串表示
        """
        if not self.project_info:
            return "项目未解析"

        info = self.project_info
        lines = [
            "=" * 60,
            "LaTeX 项目结构分析",
            "=" * 60,
            f"项目根目录: {info.root_dir}",
            f"主入口文件: {info.main_file}",
            "",
            f"Tex 文件总数: {len(info.tex_files)}",
            f"参考文献文件: {len(info.bib_files)}",
            f"样式文件: {len(info.sty_files)}",
            f"图片文件: {len(info.image_files)}",
            "",
            "Tex 文件列表:",
        ]

        for tex_file in info.tex_files:
            marker = " [主]" if tex_file == info.main_file else ""
            lines.append(f"  - {os.path.relpath(tex_file, info.root_dir)}{marker}")

        if info.bib_files:
            lines.append("")
            lines.append("参考文献文件:")
            for bib in info.bib_files:
                lines.append(f"  - {os.path.relpath(bib, info.root_dir)}")

        if info.image_dirs:
            lines.append("")
            lines.append("图片目录:")
            for img_dir in info.image_dirs:
                lines.append(f"  - {os.path.relpath(img_dir, info.root_dir)}")

        lines.append("=" * 60)

        return "\n".join(lines)
