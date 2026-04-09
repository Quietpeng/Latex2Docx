#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LaTeX 到 DOCX 智能转换工具 - 主入口

这是一个完整的 LaTeX 项目到 DOCX 格式的智能转换工具。

主要功能：
1. 自动解析复杂的 LaTeX 项目结构
2. 递归合并多个 tex 文件
3. 处理各种 LaTeX 命令和包
4. 完整支持参考文献和引文
5. 使用 Pandoc 生成高质量的 DOCX 文档

使用示例：
    from main import LaTeX2DOCXConverter

    converter = LaTeX2DOCXConverter('/path/to/latex/project')
    converter.convert('output.docx')
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# 导入核心模块
from core import (
    LaTeXProjectParser,
    LaTeXMerger,
    LaTeXCommandHandler,
    CitationHandler,
    LaTeXConverter
)
from core.converter import ConversionPipeline, PandocOptions


class LaTeX2DOCXConverter:
    """
    LaTeX 到 DOCX 转换器主类

    使用示例：
        converter = LaTeX2DOCXConverter('/path/to/latex/project')
        converter.convert('output.docx')

    或使用详细控制：
        converter = LaTeX2DOCXConverter('/path/to/latex/project')
        project_info = converter.parse()
        merged = converter.merge()
        processed = converter.process(merged)
        processed = converter.process_citations(processed)
        converter.convert_to_docx(processed, 'output.docx')
    """

    def __init__(
        self,
        project_path: str,
        encoding: str = 'utf-8',
        config: Optional[Dict] = None
    ):
        """
        初始化转换器

        参数：
            project_path: LaTeX 项目路径（目录或主文件）
            encoding: 文本编码
            config: 配置字典
        """
        self.project_path = project_path
        self.encoding = encoding
        self.config = config or {}

        # 初始化组件
        self.parser: Optional[LaTeXProjectParser] = None
        self.merger: Optional[LaTeXMerger] = None
        self.command_handler: Optional[LaTeXCommandHandler] = None
        self.citation_handler: Optional[CitationHandler] = None
        self.converter: Optional[LaTeXConverter] = None

        # 解析结果
        self.project_info = None
        self.merged_content: Optional[str] = None
        self.processed_content: Optional[str] = None

    def parse(self) -> 'LaTeX2DOCXConverter':
        """
        解析项目结构

        返回：
            self（支持链式调用）
        """
        self.parser = LaTeXProjectParser(self.project_path, self.encoding)
        self.project_info = self.parser.parse()
        return self

    def merge(self) -> 'LaTeX2DOCXConverter':
        """
        合并文件

        返回：
            self（支持链式调用）
        """
        if not self.project_info:
            self.parse()

        self.merger = LaTeXMerger(self.project_info, self.encoding)
        self.merged_content = self.merger.merge()
        return self

    def process(self, content: Optional[str] = None) -> 'LaTeX2DOCXConverter':
        """
        处理 LaTeX 命令

        参数：
            content: 要处理的内容（如果为 None，使用合并后的内容）

        返回：
            self（支持链式调用）
        """
        if content is None:
            content = self.merged_content

        if not content:
            raise ValueError("没有可处理的内容")

        pandoc_from = (self.config.get('pandoc_from_format') or 'latex').lower()

        # 默认让 Pandoc 直接读取 LaTeX（比正则“转 Markdown”稳健得多：图片/表格/引用都更完整）
        if pandoc_from == 'latex':
            self.processed_content = self._preprocess_latex_for_pandoc(content)
            return self

        # 兼容旧流程：转成更像 Markdown 的文本再喂给 Pandoc
        self.command_handler = LaTeXCommandHandler()
        preserve_math = self.config.get('preserve_math', True)
        self.processed_content = self.command_handler.process(content, preserve_math)
        return self

    _PAGEBREAK_MARKER = 'LATEX2DOCX_PAGEBREAK_6a0b6c7e'

    def _preprocess_latex_for_pandoc(self, content: str) -> str:
        """对 LaTeX 做最小必要的预处理，避免破坏结构。"""
        import os
        import re

        result = content

        # 保留换页：Pandoc(LaTeX->DOCX) 默认不会生成 Word 的分页符。
        # 这里先把 LaTeX 的换页命令替换为一个“段落级标记”，后续在生成的 docx 里再替换成 <w:br w:type="page"/>。
        marker = self._PAGEBREAK_MARKER
        result = re.sub(r'\\(newpage|clearpage|cleardoublepage)\b', f'\n\n{marker}\n\n', result)
        result = re.sub(r'\\pagebreak(\[[^\]]*\])?\b', f'\n\n{marker}\n\n', result)

        # Pandoc 对 \includegraphics{\detokenize{...}} 的支持不稳定，先展开路径
        result = re.sub(
            r'\\includegraphics(\[[^\]]*\])?\{\s*\\detokenize\{([^}]*)\}\s*\}',
            r'\\includegraphics\1{\2}',
            result,
            flags=re.DOTALL,
        )

        # Pandoc 不会执行 TeX 的条件宏（如 \IfFileExists），会导致图片/占位块被整体跳过。
        # 这里在转换前用 Python 按“真实文件是否存在”展开：存在 -> then 分支，否则 -> else 分支。
        base_dir = self.project_info.root_dir if self.project_info else None
        search_dirs = []
        if self.project_info:
            search_dirs.append(self.project_info.root_dir)
            if self.project_info.main_file:
                search_dirs.append(os.path.dirname(self.project_info.main_file))
            for d in (self.project_info.image_dirs or []):
                search_dirs.append(d)

        def _resolve_path(p: str) -> str:
            p = p.strip()
            if not p:
                return ''
            # \\detokenize{...}
            m = re.match(r'^\\detokenize\{(.*)\}$', p, flags=re.DOTALL)
            if m:
                p = m.group(1).strip()
            if os.path.isabs(p):
                return p
            # 先按 base_dir，再按已知资源目录尝试
            candidates = []
            if base_dir:
                candidates.append(os.path.join(base_dir, p))
            for d in search_dirs:
                candidates.append(os.path.join(d, p))
            for c in candidates:
                c = os.path.normpath(c)
                if os.path.exists(c):
                    return c
            return os.path.normpath(os.path.join(base_dir, p)) if base_dir else os.path.normpath(p)

        def _read_braced_arg(s: str, i: int):
            """读取从 s[i]=='{' 开始的一个 {..} 参数，返回 (arg, next_index)。"""
            if i >= len(s) or s[i] != '{':
                return None, i
            i += 1
            start = i
            depth = 0
            while i < len(s):
                ch = s[i]
                if ch == '{' and (i == 0 or s[i - 1] != '\\'):
                    depth += 1
                elif ch == '}' and (i == 0 or s[i - 1] != '\\'):
                    if depth == 0:
                        return s[start:i], i + 1
                    depth -= 1
                i += 1
            return None, i

        def _expand_iffileexists(s: str) -> str:
            key = '\\IfFileExists'
            out = []
            pos = 0
            while True:
                m = s.find(key, pos)
                if m < 0:
                    out.append(s[pos:])
                    break
                out.append(s[pos:m])
                i = m + len(key)
                while i < len(s) and s[i].isspace():
                    i += 1
                path_arg, i2 = _read_braced_arg(s, i)
                if path_arg is None:
                    out.append(s[m:i2])
                    pos = i2
                    continue
                i = i2
                while i < len(s) and s[i].isspace():
                    i += 1
                then_arg, i2 = _read_braced_arg(s, i)
                if then_arg is None:
                    out.append(s[m:i2])
                    pos = i2
                    continue
                i = i2
                while i < len(s) and s[i].isspace():
                    i += 1
                else_arg, i2 = _read_braced_arg(s, i)
                if else_arg is None:
                    out.append(s[m:i2])
                    pos = i2
                    continue

                resolved = _resolve_path(path_arg)
                chosen = then_arg if resolved and os.path.exists(resolved) else else_arg
                out.append(chosen)
                pos = i2
            return ''.join(out)

        # 迭代展开，处理嵌套情况（最多 3 层，避免异常输入死循环）
        for _ in range(3):
            new_result = _expand_iffileexists(result)
            if new_result == result:
                break
            result = new_result

        return result

    def _postprocess_docx_pagebreaks(self, docx_path: str) -> int:
        """把预处理插入的分页标记替换成真正的 Word 分页符。"""
        import os
        import re
        import shutil
        import tempfile
        import zipfile

        marker = self._PAGEBREAK_MARKER
        if not marker:
            return 0
        if not os.path.exists(docx_path):
            return 0

        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.docx')
        os.close(tmp_fd)

        replaced = 0
        try:
            with zipfile.ZipFile(docx_path, 'r') as zin, zipfile.ZipFile(tmp_path, 'w') as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename == 'word/document.xml':
                        xml = data.decode('utf-8', errors='ignore')
                        # 替换包含 marker 的整段 <w:p>...</w:p>
                        pattern = re.compile(r'<w:p\b[\s\S]*?' + re.escape(marker) + r'[\s\S]*?</w:p>')
                        xml, n = pattern.subn('<w:p><w:r><w:br w:type="page"/></w:r></w:p>', xml)
                        replaced += n
                        data = xml.encode('utf-8')
                    zout.writestr(item, data)
            shutil.move(tmp_path, docx_path)
            return replaced
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def process_citations(self, content: Optional[str] = None) -> 'LaTeX2DOCXConverter':
        """
        处理引文

        参数：
            content: 要处理的内容（如果为 None，使用处理后的内容）

        返回：
            self（支持链式调用）
        """
        if content is None:
            content = self.processed_content

        if not content:
            raise ValueError("没有可处理的内容")

        pandoc_from = (self.config.get('pandoc_from_format') or 'latex').lower()

        self.citation_handler = CitationHandler()

        # 加载参考文献（用于报告/诊断）
        if self.project_info and self.project_info.bib_files:
            self.citation_handler.load_bib_files(self.project_info.bib_files, self.encoding)

        # 当 Pandoc 直接读取 LaTeX 时，不要把 \cite{...} 改写成 [@key]：
        # 否则 [@key] 会变成普通文本，citeproc 也不会生成参考文献。
        if pandoc_from == 'latex':
            return self

        # Markdown 流程：把引文转成 Pandoc 引文格式
        self.processed_content = self.citation_handler.process_citations(
            content,
            style='pandoc'
        )
        return self

    def convert_to_docx(
        self,
        output_file: str,
        content: Optional[str] = None,
        bib_files: Optional[List[str]] = None,
        reference_doc: Optional[str] = None,
        csl_file: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        转换为 DOCX

        参数：
            output_file: 输出文件路径
            content: 要转换的内容（如果为 None，使用处理后的内容）
            bib_files: BibTeX 文件列表
            reference_doc: 参考文档路径
            csl_file: CSL 样式文件

        返回：
            (成功标志, 消息)
        """
        if content is None:
            content = self.processed_content

        if not content:
            return False, "没有可转换的内容"

        # 初始化转换器
        self.converter = LaTeXConverter(encoding=self.encoding)

        # 检查 Pandoc
        if not self.converter._check_pandoc():
            return False, "Pandoc 未安装或不可用"

        # 获取 bib 文件
        if bib_files is None:
            if self.project_info:
                bib_files = self.project_info.bib_files
            else:
                bib_files = []

        # 创建选项
        # 资源路径：至少要包含项目根目录与图片目录，否则图片无法被 Pandoc 找到并嵌入到 docx
        resource_paths = []
        if self.project_info:
            resource_paths.append(self.project_info.root_dir)
            if self.project_info.main_file:
                resource_paths.append(os.path.dirname(self.project_info.main_file))
            for p in (self.project_info.image_dirs or []):
                resource_paths.append(p)
            for img in (self.project_info.image_files or []):
                resource_paths.append(os.path.dirname(img))

        # 去重并标准化
        seen = set()
        uniq_resource_paths = []
        for p in resource_paths:
            p = os.path.normpath(p)
            if p and p not in seen and os.path.isdir(p):
                uniq_resource_paths.append(p)
                seen.add(p)

        pandoc_from = (self.config.get('pandoc_from_format') or 'latex').lower()
        options = PandocOptions(
            from_format=pandoc_from,
            to_format='docx',
            output=output_file,
            bibliography=bib_files,
            citeproc=True,
            csl=csl_file or '',
            reference_doc=reference_doc or '',
            standalone=True,
            resource_path=uniq_resource_paths,
            extra_args=[
                '--metadata=reference-section-title=参考文献',
            ],
        )

        # 执行转换（让 Pandoc 在项目根目录下运行，更利于相对路径解析）
        cwd = self.project_info.root_dir if self.project_info else None
        success, message = self.converter.convert(content, output_file, options, cwd=cwd)

        # 换页保留：后处理把 marker 段落替换成 Word 分页符
        if success and pandoc_from == 'latex' and self.config.get('preserve_pagebreaks', True):
            try:
                n = self._postprocess_docx_pagebreaks(output_file)
                if n:
                    message = f"{message}（已保留分页符: {n} 处）"
            except Exception as e:
                # 不因为后处理失败而判定整体失败，但给出提示
                message = f"{message}（警告：分页符后处理失败: {e}）"

        return success, message

    def convert(
        self,
        output_file: str,
        steps: Optional[List[str]] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        执行完整转换流程

        参数：
            output_file: 输出文件路径
            steps: 要执行的步骤列表（默认全部）
            **kwargs: 额外参数（传递给各个步骤）

        返回：
            (成功标志, 消息)
        """
        if steps is None:
            steps = ['parse', 'merge', 'process', 'citations', 'convert']

        try:
            # 解析
            if 'parse' in steps:
                self.parse()

            # 合并
            if 'merge' in steps:
                if not self.merged_content:
                    self.merge()

            # 处理
            if 'process' in steps:
                self.process(self.merged_content)

            # 引文
            if 'citations' in steps:
                # 只有在 Pandoc 读取 markdown 时，才需要把 \cite{...} 转成 [@key]
                pandoc_from = (self.config.get('pandoc_from_format') or 'latex').lower()
                if pandoc_from == 'markdown' and self.config.get('process_citations', True):
                    self.process_citations(self.processed_content)

            # 转换
            if 'convert' in steps:
                bib_files = kwargs.get('bib_files', self.project_info.bib_files if self.project_info else [])
                reference_doc = kwargs.get('reference_doc', self.config.get('reference_doc'))
                csl_file = kwargs.get('csl_file', self.config.get('csl'))

                return self.convert_to_docx(
                    output_file,
                    self.processed_content,
                    bib_files,
                    reference_doc,
                    csl_file
                )

            return True, "流程完成"

        except Exception as e:
            return False, str(e)

    def get_report(self) -> str:
        """
        获取转换报告

        返回：
            报告字符串
        """
        lines = ["=" * 60, "LaTeX 到 DOCX 转换报告", "=" * 60, ""]

        if self.project_info:
            lines.append(f"项目根目录: {self.project_info.root_dir}")
            lines.append(f"主入口文件: {self.project_info.main_file}")
            lines.append(f"Tex 文件数: {len(self.project_info.tex_files)}")
            lines.append(f"Bib 文件数: {len(self.project_info.bib_files)}")
            lines.append(f"图片文件数: {len(self.project_info.image_files)}")

        if self.merged_content:
            lines.append(f"合并后长度: {len(self.merged_content)} 字符")

        if self.processed_content:
            lines.append(f"处理后长度: {len(self.processed_content)} 字符")

        if self.citation_handler:
            lines.append(f"参考文献条目: {len(self.citation_handler.bib_entries)}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def save_intermediate(
        self,
        output_dir: str,
        include: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        保存中间结果

        参数：
            output_dir: 输出目录
            include: 要保存的内容类型

        返回：
            保存的文件路径字典
        """
        if include is None:
            include = ['merged', 'processed']

        os.makedirs(output_dir, exist_ok=True)
        saved = {}

        if 'merged' in include and self.merged_content:
            path = os.path.join(output_dir, 'merged.tex')
            with open(path, 'w', encoding=self.encoding) as f:
                f.write(self.merged_content)
            saved['merged'] = path

        if 'processed' in include and self.processed_content:
            path = os.path.join(output_dir, 'processed.md')
            with open(path, 'w', encoding=self.encoding) as f:
                f.write(self.processed_content)
            saved['processed'] = path

        return saved


def main():
    """主函数（命令行入口）"""
    from cli import main as cli_main
    sys.exit(cli_main())


if __name__ == '__main__':
    main()
