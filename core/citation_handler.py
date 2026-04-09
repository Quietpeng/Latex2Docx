# -*- coding: utf-8 -*-
"""
引文和参考文献处理器模块

功能说明：
    处理 LaTeX 文档中的引文命令和参考文献（.bib 文件）。
    支持：
    - BibTeX 格式（\cite, \citep, \citet 等）
    - biblatex 格式（\cite, \textcite, \parencite 等）
    - BibTeX 和 biblatex 两种参考文献处理方式
    - 自动识别和解析 .bib 文件
    - Pandoc 引文格式转换

使用示例：
    handler = CitationHandler()
    handler.load_bib_files(['refs.bib'])
    processed = handler.process_citations(content)
"""

import os
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class BibEntry:
    """BibTeX 条目数据类"""
    entry_type: str  # 条目类型（article, book, inproceedings 等）
    cite_key: str  # 引用键
    fields: Dict[str, str] = field(default_factory=dict)  # 字段
    raw_entry: str = ''  # 原始条目文本

    @property
    def authors(self) -> List[str]:
        """获取作者列表"""
        author_str = self.fields.get('author', '')
        if not author_str:
            return []
        # 分割多个作者（通常用 "and" 分隔）
        authors = re.split(r'\s+and\s+', author_str)
        return [self._format_author(a.strip()) for a in authors]

    @property
    def year(self) -> str:
        """获取年份"""
        return self.fields.get('year', '')

    @property
    def title(self) -> str:
        """获取标题"""
        return self.fields.get('title', '')

    @property
    def formatted(self) -> str:
        """获取格式化引用"""
        authors = self.authors
        year = self.year

        if authors and year:
            if len(authors) == 1:
                return f"{authors[0]} ({year})"
            elif len(authors) == 2:
                return f"{authors[0]} and {authors[1]} ({year})"
            else:
                return f"{authors[0]} et al. ({year})"
        elif year:
            return f"({year})"
        else:
            return self.cite_key

    def _format_author(self, author: str) -> str:
        """
        格式化作者姓名

        参数：
            author: 原始作者字符串

        返回：
            格式化的作者名（姓, 名格式）
        """
        # 处理 "Last, First" 格式
        if ',' in author:
            parts = author.split(',')
            if len(parts) == 2:
                return f"{parts[0].strip()}, {parts[1].strip()}"

        # 处理 "First Last" 格式
        parts = author.split()
        if len(parts) >= 2:
            return f"{parts[-1]}, {' '.join(parts[:-1])}"

        return author


class CitationHandler:
    """
    引文和参考文献处理器

    负责：
    1. 解析 .bib 文件
    2. 处理各种引文命令
    3. 转换为 Pandoc 兼容的引文格式
    """

    # BibTeX 条目正则
    BIB_ENTRY_PATTERN = re.compile(
        r'@(\w+)\s*\{\s*([^,\s]+)\s*,([^@]*?)(?=\n\s*\}|\n\s*@|\Z)',
        re.DOTALL
    )

    # BibTeX 字段正则
    BIB_FIELD_PATTERN = re.compile(
        r'(\w+)\s*=\s*(?:\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}|"([^"]*)"|(\d+))',
        re.DOTALL
    )

    # 引文命令模式
    CITE_COMMANDS = {
        # BibTeX 命令
        r'\\cite[a-z]*': 'standard',
        r'\\citep': 'paren',
        r'\\citet': 'text',
        r'\\citealt': 'alt',
        r'\\citealp': 'alp',
        r'\\citetext': 'text',
        r'\\citeauthor': 'author',
        r'\\citeyear': 'year',
        r'\\citeyearpar': 'yearpar',

        # biblatex 命令
        r'\\textcite': 'text',
        r'\\parencite': 'paren',
        r'\\footcite': 'footnote',
        r'\\supercite': 'super',
        r'\\smartcite': 'smart',
        r'\\nptextcite': 'np',
    }

    def __init__(self):
        """初始化处理器"""
        self.bib_entries: Dict[str, BibEntry] = {}
        self.cite_keys: Set[str] = set()

    def load_bib_file(self, bib_file: str, encoding: str = 'utf-8') -> int:
        """
        加载单个 BibTeX 文件

        参数：
            bib_file: .bib 文件路径
            encoding: 文件编码

        返回：
            加载的条目数量
        """
        count = 0

        try:
            with open(bib_file, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()

            entries = self._parse_bib_content(content)
            for entry in entries:
                self.bib_entries[entry.cite_key] = entry
                self.cite_keys.add(entry.cite_key)
                count += 1

        except Exception as e:
            print(f"警告：无法加载 BibTeX 文件 {bib_file}: {e}")

        return count

    def load_bib_files(self, bib_files: List[str], encoding: str = 'utf-8') -> int:
        """
        批量加载 BibTeX 文件

        参数：
            bib_files: .bib 文件路径列表
            encoding: 文件编码

        返回：
            加载的条目总数
        """
        total = 0
        for bib_file in bib_files:
            if os.path.exists(bib_file):
                total += self.load_bib_file(bib_file, encoding)
        return total

    def _parse_bib_content(self, content: str) -> List[BibEntry]:
        """
        解析 BibTeX 内容

        参数：
            content: BibTeX 文件内容

        返回：
            解析出的条目列表
        """
        entries = []

        # 预处理：移除注释
        content = self._remove_bib_comments(content)

        for match in self.BIB_ENTRY_PATTERN.finditer(content):
            entry_type = match.group(1).lower()
            cite_key = match.group(2).strip()
            fields_text = match.group(3)

            fields = self._parse_bib_fields(fields_text)

            entry = BibEntry(
                entry_type=entry_type,
                cite_key=cite_key,
                fields=fields,
                raw_entry=match.group(0)
            )
            entries.append(entry)

        return entries

    def _remove_bib_comments(self, content: str) -> str:
        """移除 BibTeX 注释"""
        # 移除 % 开头的注释行
        lines = content.split('\n')
        processed_lines = []

        for line in lines:
            # 查找不在字符串内的 %
            in_string = False
            clean_line = []
            for char in line:
                if char in ['"', "'"]:
                    in_string = not in_string
                elif char == '%' and not in_string:
                    break
                clean_line.append(char)
            processed_lines.append(''.join(clean_line))

        return '\n'.join(processed_lines)

    def _parse_bib_fields(self, fields_text: str) -> Dict[str, str]:
        """
        解析 BibTeX 字段

        参数：
            fields_text: 字段文本

        返回：
            字段字典
        """
        fields = {}

        for match in self.BIB_FIELD_PATTERN.finditer(fields_text):
            field_name = match.group(1).lower()
            # 获取字段值（可能在 {}、" 或无引号中）
            field_value = match.group(2) or match.group(3) or match.group(4) or ''

            # 清理字段值
            field_value = field_value.strip()
            # 移除多余的花括号
            field_value = re.sub(r'\{([^{}]*)\}', r'\1', field_value)
            # 清理 LaTeX 命令
            field_value = self._clean_latex_specials(field_value)

            fields[field_name] = field_value

        return fields

    def _clean_latex_specials(self, text: str) -> str:
        """清理 LaTeX 特殊命令"""
        # 保留基本结构，移除格式命令
        replacements = [
            (r'\\textit\{([^}]+)\}', r'\1'),
            (r'\\textbf\{([^}]+)\}', r'\1'),
            (r'\\emph\{([^}]+)\}', r'\1'),
            (r'\\' '{', '{'),
            (r'\\' '}', '}'),
            (r'\\&', '&'),
            (r'\\%', '%'),
            (r'\\_', '_'),
        ]

        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)

        return text

    def process_citations(self, content: str, style: str = 'markdown') -> str:
        """
        处理内容中的引文命令

        参数：
            content: 包含引文的 LaTeX 内容
            style: 输出格式（'markdown' 或 'pandoc'）

        返回：
            处理后的内容
        """
        if style == 'markdown':
            return self._process_citations_markdown(content)
        elif style == 'pandoc':
            return self._process_citations_pandoc(content)
        else:
            return content

    def _process_citations_markdown(self, content: str) -> str:
        """
        将引文转换为 Markdown 格式

        转换策略：
        - \cite{key} -> [Author et al., Year]
        - \citep{key} -> (Author et al., Year)
        - \citet{key} -> Author et al. (Year)
        """
        result = content

        # 处理各种 \cite* 命令
        result = re.sub(
            r'\\citep(?:\[[^\]]*\])?\{([^}]+)\}',
            lambda m: f"({self._format_citation(m.group(1))})",
            result
        )

        result = re.sub(
            r'\\citet(?:\[[^\]]*\])?\{([^}]+)\}',
            lambda m: f"{self._format_citation_text(m.group(1))}",
            result
        )

        result = re.sub(
            r'\\citeyear(?:par)?(?:\[.*?\])?\{([^}]+)\}',
            lambda m: f"({self._get_year(m.group(1))})",
            result
        )

        result = re.sub(
            r'\\citeauthor(?:\[.*?\])?\{([^}]+)\}',
            lambda m: self._get_authors(m.group(1)),
            result
        )

        # 通用 \cite 命令
        result = re.sub(
            r'\\cite[a-z]*(?:\[[^\]]*\])?\{([^}]+)\}',
            lambda m: f"[{self._format_citation(m.group(1))}]",
            result
        )

        return result

    def _process_citations_pandoc(self, content: str) -> str:
        """
        将引文转换为 Pandoc 引文格式

        Pandoc 引文格式：[@citekey] 或 [@citekey, p. 123]
        """
        result = content

        # 通用 \cite 命令 -> [@citekey]
        result = re.sub(
            r'\\cite[a-z]*(?:\[[^\]]*\])?\{([^}]+)\}',
            lambda m: f"[@{m.group(1)}]",
            result
        )

        return result

    def _format_citation(self, cite_keys: str) -> str:
        """
        格式化引文（括号内）

        参数：
            cite_keys: 逗号分隔的引用键

        返回：
            格式化的引文
        """
        keys = [k.strip() for k in cite_keys.split(',')]

        if len(keys) == 1:
            return self._get_entry_formatted(keys[0])
        elif len(keys) == 2:
            return f"{self._get_entry_formatted(keys[0])}; {self._get_entry_formatted(keys[1])}"
        else:
            first = self._get_entry_formatted(keys[0])
            return f"{first} et al."

    def _format_citation_text(self, cite_keys: str) -> str:
        """
        格式化引文（文本中）

        参数：
            cite_keys: 逗号分隔的引用键

        返回：
            格式化的引文
        """
        keys = [k.strip() for k in cite_keys.split(',')]

        if len(keys) == 1:
            return self._get_entry_text_formatted(keys[0])
        else:
            first_author = self._get_first_author(keys[0])
            year = self._get_year(keys[0])
            return f"{first_author} et al. ({year})"

    def _get_entry_formatted(self, key: str) -> str:
        """获取条目格式化引用"""
        if key in self.bib_entries:
            return self.bib_entries[key].formatted
        return key

    def _get_entry_text_formatted(self, key: str) -> str:
        """获取条目的文本格式引用"""
        if key in self.bib_entries:
            entry = self.bib_entries[key]
            authors = entry.authors
            year = entry.year

            if authors and year:
                if len(authors) == 1:
                    return f"{authors[0]} ({year})"
                elif len(authors) == 2:
                    return f"{authors[0]} and {authors[1]} ({year})"
                else:
                    return f"{authors[0]} et al. ({year})"
            elif year:
                return f"({year})"

        return key

    def _get_year(self, key: str) -> str:
        """获取年份"""
        if key in self.bib_entries:
            return self.bib_entries[key].year
        return key

    def _get_authors(self, key: str) -> str:
        """获取作者列表"""
        if key in self.bib_entries:
            authors = self.bib_entries[key].authors
            if len(authors) == 1:
                return authors[0]
            elif len(authors) == 2:
                return f"{authors[0]} and {authors[1]}"
            else:
                return f"{authors[0]} et al."
        return key

    def _get_first_author(self, key: str) -> str:
        """获取第一作者"""
        if key in self.bib_entries:
            authors = self.bib_entries[key].authors
            if authors:
                return authors[0]
        return key

    def generate_references_section(self, style: str = 'plain') -> str:
        """
        生成参考文献部分

        参数：
            style: 参考文献样式

        返回：
            参考文献部分的 LaTeX/Markdown 内容
        """
        if not self.bib_entries:
            return ""

        if style == 'markdown':
            return self._generate_references_markdown()
        elif style == 'plain':
            return self._generate_references_plain()
        else:
            return self._generate_references_plain()

    def _generate_references_markdown(self) -> str:
        """生成 Markdown 格式的参考文献"""
        lines = ["# 参考文献", ""]

        for key in sorted(self.bib_entries.keys()):
            entry = self.bib_entries[key]
            lines.append(self._format_reference_markdown(entry))
            lines.append("")

        return '\n'.join(lines)

    def _generate_references_plain(self) -> str:
        """生成纯文本格式的参考文献"""
        lines = ["\\section*{参考文献}", ""]

        for key in sorted(self.bib_entries.keys()):
            entry = self.bib_entries[key]
            lines.append(self._format_reference_latex(entry))
            lines.append("")

        return '\n'.join(lines)

    def _format_reference_markdown(self, entry: BibEntry) -> str:
        """格式化 Markdown 参考文献条目"""
        parts = []

        # 作者
        authors = entry.authors
        if authors:
            if len(authors) == 1:
                parts.append(authors[0])
            elif len(authors) == 2:
                parts.append(f"{authors[0]} and {authors[1]}")
            else:
                parts.append(f"{authors[0]} et al.")

        # 年份
        if entry.year:
            parts.append(f"({entry.year})")

        # 标题
        if entry.title:
            parts.append(f"**{entry.title}**")

        # 类型和出版信息
        entry_type = entry.entry_type
        journal = entry.fields.get('journal', '')
        booktitle = entry.fields.get('booktitle', '')
        publisher = entry.fields.get('publisher', '')
        volume = entry.fields.get('volume', '')
        pages = entry.fields.get('pages', '')

        if entry_type == 'article' and journal:
            parts.append(f"* {journal}*")
            if volume:
                parts[-1] += f", {volume}"
            if pages:
                parts[-1] += f", pp. {pages}"
        elif entry_type == 'book' and publisher:
            parts.append(f"{publisher}")
        elif entry_type == 'inproceedings' and booktitle:
            parts.append(f"In: *{booktitle}*")
            if pages:
                parts[-1] += f", pp. {pages}"

        return '. '.join(parts)

    def _format_reference_latex(self, entry: BibEntry) -> str:
        """格式化 LaTeX 参考文献条目"""
        # 简单实现，可以根据需要扩展
        authors = ', '.join(entry.authors) if entry.authors else ''
        year = entry.year
        title = entry.title

        parts = []
        if authors:
            parts.append(f"{authors}.")
        if year:
            parts.append(f"({year}).")
        if title:
            parts.append(f"*{title}*.")

        return ' '.join(parts)

    def get_citation_report(self) -> str:
        """
        获取引文报告

        返回：
            引文统计报告
        """
        lines = [
            "=" * 50,
            "引文处理报告",
            "=" * 50,
            f"加载的参考文献条目: {len(self.bib_entries)}",
            "",
            "引用的键:",
        ]

        for key in sorted(self.cite_keys):
            if key in self.bib_entries:
                entry = self.bib_entries[key]
                lines.append(f"  - {key}: {entry.authors[0] if entry.authors else 'Unknown'}, {entry.year}")
            else:
                lines.append(f"  - {key}: [未找到条目]")

        lines.append("=" * 50)
        return "\n".join(lines)
