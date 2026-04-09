# -*- coding: utf-8 -*-
"""
Pandoc 转换器模块

功能说明：
    使用 Pandoc 将处理后的 LaTeX 转换为 DOCX 格式。
    支持：
    - 多种输入格式（LaTeX, Markdown）
    - 自定义 Pandoc 参数
    - 参考文档（.docx）模板
    - 图片路径处理
    - 引文处理

使用示例：
    converter = LaTeXConverter()
    converter.convert('output.docx', 'input.tex')
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PandocOptions:
    """Pandoc 选项数据类"""
    # 基础选项
    from_format: str = 'latex'  # 输入格式
    to_format: str = 'docx'  # 输出格式
    output: str = ''  # 输出文件

    # 文档选项
    standalone: bool = False  # 生成独立文档
    wrap: str = 'auto'  # 文本换行
    highlight: str = 'default'  # 代码高亮

    # 参考文献选项
    bibliography: List[str] = None  # 参考文献文件
    citeproc: bool = True  # 使用引用处理器
    csl: str = ''  # CSL 样式文件

    # 参考文档
    reference_doc: str = ''  # 参考 DOCX 文件

    # 图片选项
    resource_path: List[str] = None  # 资源路径
    extract_media: str = ''  # 提取媒体到目录

    # 额外选项
    extra_args: List[str] = None

    def __post_init__(self):
        if self.bibliography is None:
            self.bibliography = []
        if self.resource_path is None:
            self.resource_path = []
        if self.extra_args is None:
            self.extra_args = []

    def to_list(self) -> List[str]:
        """
        转换为命令行参数列表

        返回：
            Pandoc 命令行参数列表
        """
        args = []

        # 输入格式
        if self.from_format:
            args.extend(['-f', self.from_format])

        # 输出格式
        args.extend(['-t', self.to_format])

        # 输出文件
        if self.output:
            args.extend(['-o', self.output])

        # 独立文档
        if self.standalone:
            args.append('-s')

        # 文本换行
        if self.wrap:
            args.extend(['--wrap', self.wrap])

        # 代码高亮（使用 pygments 样式，兼容旧版本）
        if self.highlight:
            args.extend(['--highlight-style', 'pygments'])

        # 参考文献
        for bib in self.bibliography:
            if os.path.exists(bib):
                args.extend(['--bibliography', bib])

        # 引用处理
        if self.citeproc:
            args.append('--citeproc')

        # CSL 样式
        if self.csl and os.path.exists(self.csl):
            args.extend(['--csl', self.csl])

        # 参考文档
        if self.reference_doc and os.path.exists(self.reference_doc):
            args.extend(['--reference-doc', self.reference_doc])

        # 资源路径（Pandoc 期望单个 SEARCHPATH；Windows 下分隔符为 ';'）
        if self.resource_path:
            joined = os.pathsep.join(self.resource_path)
            args.append(f'--resource-path={joined}')

        # 提取媒体
        if self.extract_media:
            args.extend(['--extract-media', self.extract_media])

        # 额外参数
        args.extend(self.extra_args)

        return args


class LaTeXConverter:
    """
    LaTeX 到 DOCX 转换器

    使用 Pandoc 进行格式转换，提供：
    1. 灵活的转换选项
    2. 错误处理和诊断
    3. 临时文件管理
    4. 进度反馈
    """

    # Pandoc 可执行文件路径
    PANDOC_EXECUTABLE = 'pandoc'

    # 支持的输入格式
    SUPPORTED_INPUT_FORMATS = {'latex', 'markdown', 'plain', 'html'}

    # 支持的输出格式
    SUPPORTED_OUTPUT_FORMATS = {'docx', 'odt', 'pdf', 'html', 'markdown', 'plain'}

    def __init__(
        self,
        pandoc_path: Optional[str] = None,
        encoding: str = 'utf-8'
    ):
        """
        初始化转换器

        参数：
            pandoc_path: Pandoc 可执行文件路径
            encoding: 文本编码
        """
        self.pandoc_path = pandoc_path or self.PANDOC_EXECUTABLE
        self.encoding = encoding
        self._check_pandoc()

    def _check_pandoc(self) -> bool:
        """
        检查 Pandoc 是否可用

        返回：
            True 如果 Pandoc 可用
        """
        try:
            result = subprocess.run(
                [self.pandoc_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✓ 检测到 {version_line}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        print("⚠ 警告：未检测到 Pandoc 或 Pandoc 版本过旧")
        print("  请安装 Pandoc: https://pandoc.org/installing.html")
        return False

    def convert(
        self,
        input_content: str,
        output_file: str,
        options: Optional[PandocOptions] = None,
        input_file: Optional[str] = None,
        resource_path: Optional[List[str]] = None,
        cwd: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        执行转换

        参数：
            input_content: 输入内容（LaTeX 或 Markdown）
            output_file: 输出文件路径
            options: Pandoc 选项
            input_file: 输入文件名（用于相对路径解析）
            resource_path: 额外的资源路径

        返回：
            (成功标志, 消息)
        """
        if options is None:
            options = PandocOptions(output=output_file)

        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 准备输入
        if input_file:
            # 使用文件输入
            temp_input = input_file
        else:
            # 创建临时输入文件
            temp_fd, temp_input = tempfile.mkstemp(suffix='.tex', text=True)
            with os.fdopen(temp_fd, 'w', encoding=self.encoding) as f:
                f.write(input_content)

        try:
            # 合并额外资源路径（如有）
            if resource_path:
                for p in resource_path:
                    if p and p not in options.resource_path:
                        options.resource_path.append(p)

            # 构建命令
            cmd = [self.pandoc_path]
            cmd.extend(options.to_list())
            cmd.append(temp_input)

            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
                cwd=cwd,
            )

            if result.returncode == 0:
                # 检查输出文件
                if os.path.exists(output_file):
                    return True, f"转换成功: {output_file}"
                else:
                    return False, "转换完成但未生成输出文件"
            else:
                error_msg = result.stderr or "未知错误"
                return False, f"Pandoc 错误: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "转换超时（超过 5 分钟）"
        except Exception as e:
            return False, f"转换异常: {str(e)}"
        finally:
            # 清理临时文件
            if not input_file and os.path.exists(temp_input):
                os.unlink(temp_input)

    def convert_file(
        self,
        input_file: str,
        output_file: str,
        options: Optional[PandocOptions] = None
    ) -> Tuple[bool, str]:
        """
        转换单个文件

        参数：
            input_file: 输入文件路径
            output_file: 输出文件路径
            options: Pandoc 选项

        返回：
            (成功标志, 消息)
        """
        if not os.path.exists(input_file):
            return False, f"输入文件不存在: {input_file}"

        if options is None:
            options = PandocOptions(output=output_file)

        # 设置资源路径
        input_dir = os.path.dirname(input_file)
        if input_dir and input_dir not in options.resource_path:
            options.resource_path.insert(0, input_dir)

        # 读取输入
        with open(input_file, 'r', encoding=self.encoding, errors='ignore') as f:
            content = f.read()

        return self.convert(content, output_file, options, input_file=input_file, cwd=input_dir)

    def convert_with_bibliography(
        self,
        input_content: str,
        output_file: str,
        bib_files: List[str],
        csl_file: Optional[str] = None,
        reference_doc: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        带参考文献的转换

        参数：
            input_content: 输入内容
            output_file: 输出文件
            bib_files: BibTeX 文件列表
            csl_file: CSL 样式文件
            reference_doc: 参考文档

        返回：
            (成功标志, 消息)
        """
        options = PandocOptions(
            output=output_file,
            from_format='markdown',
            bibliography=bib_files,
            citeproc=True,
            csl=csl_file or '',
            reference_doc=reference_doc or '',
            standalone=True
        )

        return self.convert(input_content, output_file, options)

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        获取支持的格式

        返回：
            格式支持信息
        """
        return {
            'input': list(self.SUPPORTED_INPUT_FORMATS),
            'output': list(self.SUPPORTED_OUTPUT_FORMATS)
        }

    def check_dependencies(self) -> Dict[str, bool]:
        """
        检查所有依赖

        返回：
            依赖检查结果
        """
        return {
            'pandoc': self._check_pandoc(),
        }


class ConversionPipeline:
    """
    转换管道

    将多个转换步骤组合成一个流程：
    1. 解析 LaTeX 项目
    2. 合并文件
    3. 处理命令
    4. 处理引文
    5. Pandoc 转换
    """

    def __init__(
        self,
        project_path: str,
        encoding: str = 'utf-8',
        config: Optional[Dict] = None
    ):
        """
        初始化转换管道

        参数：
            project_path: 项目路径
            encoding: 编码
            config: 配置字典
        """
        from .parser import LaTeXProjectParser
        from .merger import LaTeXMerger
        from .command_handler import LaTeXCommandHandler
        from .citation_handler import CitationHandler

        self.config = config or {}

        # 初始化组件
        self.parser = LaTeXProjectParser(project_path, encoding)
        self.project_info = None

        self.merger = None
        self.command_handler = LaTeXCommandHandler()
        self.citation_handler = CitationHandler()

        self.converter = LaTeXConverter(encoding=encoding)

        # 状态
        self.merged_content: Optional[str] = None
        self.processed_content: Optional[str] = None

    def run(
        self,
        output_file: str,
        step: str = 'all'
    ) -> Tuple[bool, str]:
        """
        运行转换管道

        参数：
            output_file: 输出文件路径
            step: 运行步骤 ('all', 'parse', 'merge', 'process', 'convert')

        返回：
            (成功标志, 消息)
        """
        try:
            # 步骤 1: 解析项目
            if step in ('all', 'parse'):
                self.project_info = self.parser.parse()
                print(f"✓ 项目解析完成: {len(self.project_info.tex_files)} 个文件")

            # 步骤 2: 合并文件
            if step in ('all', 'merge'):
                self.merger = LaTeXMerger(self.project_info)
                self.merged_content = self.merger.merge()
                print(f"✓ 文件合并完成")

            # 步骤 3: 处理命令
            if step in ('all', 'process'):
                if self.merged_content is None:
                    return False, "错误：未合并文件"

                self.processed_content = self.command_handler.process(
                    self.merged_content
                )
                print(f"✓ 命令处理完成")

            # 步骤 4: 处理引文
            if step in ('all', 'citation'):
                # 加载参考文献
                self.citation_handler.load_bib_files(
                    self.project_info.bib_files
                )
                print(f"✓ 参考文献加载完成: {len(self.citation_handler.bib_entries)} 条")

                # 处理引文
                if self.processed_content:
                    self.processed_content = self.citation_handler.process_citations(
                        self.processed_content,
                        style='pandoc'
                    )

            # 步骤 5: Pandoc 转换
            if step in ('all', 'convert'):
                if self.processed_content is None:
                    return False, "错误：未处理内容"

                success, message = self.converter.convert_with_bibliography(
                    self.processed_content,
                    output_file,
                    self.project_info.bib_files,
                    csl_file=self.config.get('csl', ''),
                    reference_doc=self.config.get('reference_doc', '')
                )

                if success:
                    print(f"✓ {message}")
                else:
                    return False, message

            return True, "转换管道执行完成"

        except Exception as e:
            return False, f"转换管道错误: {str(e)}"

    def get_intermediate_output(
        self,
        step: str = 'merged'
    ) -> Optional[str]:
        """
        获取中间步骤的输出

        参数：
            step: 步骤 ('merged', 'processed', 'citation')

        返回：
            对应步骤的内容
        """
        if step == 'merged':
            return self.merged_content
        elif step == 'processed':
            return self.processed_content
        else:
            return None
