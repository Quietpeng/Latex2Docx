# -*- coding: utf-8 -*-
"""
LaTeX 命令处理器模块

功能说明：
    处理 LaTeX 文档中的各种命令，转换为 Pandoc 可识别的格式。
    主要处理：
    - 特殊字符和符号
    - 交叉引用（\ref, \pageref, \cite 等）
    - 浮动体（figure, table）
    - 列表环境
    - 数学公式
    - 格式命令（\textbf, \textit 等）

使用示例：
    handler = LaTeXCommandHandler()
    processed = handler.process(content)
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass


@dataclass
class CommandMapping:
    """命令映射数据类"""
    pattern: str  # 正则表达式
    replacement: str  # 替换文本或替换函数
    description: str  # 描述


class LaTeXCommandHandler:
    """
    LaTeX 命令处理器

    将复杂的 LaTeX 命令转换为更通用的格式，
    以便 Pandoc 更好地处理。
    """

    def __init__(self):
        """初始化处理器"""
        self._setup_mappings()

    def _setup_mappings(self) -> None:
        """设置命令映射规则"""
        # 基础格式命令映射
        self.format_mappings = [
            # 粗体
            (r'\\textbf\{([^}]+)\}', r'**\1**', '粗体'),
            (r'\\bf\s*\{([^}]+)\}', r'**\1**', '粗体'),
            (r'\\bfseries\s*\{([^}]+)\}', r'**\1**', '粗体'),

            # 斜体
            (r'\\textit\{([^}]+)\}', r'*\1*', '斜体'),
            (r'\\emph\{([^}]+)\}', r'*\1*', '强调'),
            (r'\\it\s*\{([^}]+)\}', r'*\1*', '斜体'),
            (r'\\itshape\s*\{([^}]+)\}', r'*\1*', '斜体'),

            # 等宽字体
            (r'\\texttt\{([^}]+)\}', r'`\1`', '等宽字体'),
            (r'\\verb\s*\*?\s*\|([^|]+)\|', r'`\1`', '行内代码'),
            (r'\\verb\s*\*?\s*([^a-zA-Z\s])([^}]*)\1', r'`\2`', '行内代码'),

            # 下标
            (r'\\textsubscript\{([^}]+)\}', r'~\1~', '下标'),
            (r'\\textsubscript\{([^}]+)\}', r'~\1~', '下标'),
            (r'_\{([^}]+)\}', r'_\1', '下标（数学模式）'),
            (r'\^\\{([^}]+)\\}', r'^\1', '上标（数学模式）'),

            # 删除线和下划线
            (r'\\sout\{([^}]+)\}', r'~~\1~~', '删除线'),
            (r'\\uline\{([^}]+)\}', r'+\1+', '下划线'),
        ]

        # 空白和间距命令
        self.space_mappings = [
            (r'\\hspace\{[^}]*\}', '', '水平间距'),
            (r'\\vspace\{[^}]*\}', '', '垂直间距'),
            (r'\\smallskip', '', '小间距'),
            (r'\\medskip', '', '中间距'),
            (r'\\bigskip', '', '大间距'),
            (r'\\[\\]|\ \\\ ', ' ', '制表符/反斜杠空格'),
            (r'~', ' ', '不换行空格'),
            (r'\\\\(?:\[[\d\w]+\])?', '\n\n', '换行'),
            (r'\\par', '\n\n', '段落'),
        ]

        # 环境映射
        self.environment_mappings = [
            # 列表环境
            (r'\\begin\{itemize\}\s*\n?', '', '无序列表开始'),
            (r'\\end\{itemize\}', '', '无序列表结束'),
            (r'\\begin\{enumerate\}\s*\n?', '', '有序列表开始'),
            (r'\\end\{enumerate\}', '', '有序列表结束'),
            (r'\\begin\{description\}\s*\n?', '', '描述列表开始'),
            (r'\\end\{description\}', '', '描述列表结束'),
            (r'\\item\s*(?:\[[^\]]*\])?\s*', '- ', '列表项'),
            (r'\\item\[\s*([^\]]*)\s*\]\s*', r'- **\1** ', '带标签的列表项'),

            # 引用环境
            (r'\\begin\{quote\}\s*\n?', '> ', '引用开始'),
            (r'\\end\{quote\}', '', '引用结束'),
            (r'\\begin\{quotation\}\s*\n?', '> ', '引用开始'),
            (r'\\end\{quotation\}', '', '引用结束'),
            (r'\\begin\{verse\}\s*\n?', '> ', '诗歌开始'),
            (r'\\end\{verse\}', '', '诗歌结束'),

            # 居中
            (r'\\begin\{center\}\s*\n?', '', '居中开始'),
            (r'\\end\{center\}', '', '居中结束'),

            # verbatim
            (r'\\begin\{verbatim\}\s*\n?', '```\n', '代码块开始'),
            (r'\\end\{verbatim\}', '\n```', '代码块结束'),
            (r'\\begin\{lstlisting\}\s*\n?', '```\n', '代码块开始'),
            (r'\\end\{lstlisting\}', '\n```', '代码块结束'),
            (r'\\begin\{minted\}[^\[]*(?:\[[^\]]*\])?\{[^}]*\}\s*\n?', '```\n', '代码块开始'),
            (r'\\end\{minted\}', '\n```', '代码块结束'),

            # 表格
            (r'\\begin\{tabular\}(?:\[[^\]]*\])?\{[^}]*\}', '\\\\begin{table}', '表格开始'),
            (r'\\end\{tabular\}', '\\\\end{table}', '表格结束'),
            (r'\\hline', '', '表格横线'),
            (r'\\cline\{[^}]*\}', '', '表格部分横线'),
            (r'\\multicolumn\{(\d+)\}\{(?:\{[^}]*\})?\}(?:\{([^}]*)\})?', r'\2', '多列表格'),
            (r'&', '\t', '表格分隔符'),

            # 浮动体
            (r'\\begin\{figure\*?\}\s*(?:\[[^\]]*\])?', '\\\\begin{figure}', '图片开始'),
            (r'\\end\{figure\*?\}', '\\\\end{figure}', '图片结束'),
            (r'\\begin\{table\*?\}', '\\\\begin{table}', '表格浮动体开始'),
            (r'\\end\{table\*?\}', '\\\\end{table}', '表格浮动体结束'),
        ]

        # 交叉引用命令
        self.reference_mappings = [
            (r'\\ref\{([^}]+)\}', r'@fig:\1 @tab:\1 @eq:\1', '交叉引用'),
            (r'\\pageref\{([^}]+)\}', r'[页面 @\1]', '页码引用'),
            (r'\\eqref\{([^}]+)\}', r'(@\1)', '公式引用'),
            (r'\\autoref\{([^}]+)\}', r'@\1', '自动引用'),
            (r'\\cref\{([^}]+)\}', r'@\1', '智能引用'),
            (r'\\nameref\{([^}]+)\}', r'"\1"', '名称引用'),
        ]

        # 特殊符号映射
        self.symbol_mappings = [
            (r'\\copyright', '©', '版权符号'),
            (r'\\textcopyright', '©', '版权符号'),
            (r'\\textregistered', '®', '注册商标'),
            (r'\\texttrademark', '™', '商标'),
            (r'\\textrademark', '™', '商标'),
            (r'\\ldots', '...', '省略号'),
            (r'\\dots', '...', '省略号'),
            (r'\\textellipsis', '...', '省略号'),
            (r'---', '—', '长破折号'),
            (r'--', '–', '短破折号'),
            (r'``', '"', '左双引号'),
            (r"''", '"', '右双引号'),
            (r'`', "'", '左单引号'),
            (r"'", "'", '右单引号'),
        ]

        # LaTeX 特殊字符
        self.special_char_mappings = [
            (r'\\%', '%', '百分号'),
            (r'\\#', '#', '井号'),
            (r'\\&', '&', '与号'),
            (r'\\\$', '$', '美元符号'),
            (r'\\textbackslash', '\\\\', '反斜杠'),
            (r'\\textasciitilde', '~', '波浪号'),
            (r'\\textasciicircum', '^', '脱字符'),
        ]

    def process(self, content: str, preserve_math: bool = True) -> str:
        """
        处理 LaTeX 内容

        参数：
            content: 原始 LaTeX 内容
            preserve_math: 是否保留数学公式

        返回：
            处理后的内容
        """
        result = content

        # 1. 处理注释
        result = self._remove_comments(result)

        # 2. 处理特殊字符
        result = self._process_special_chars(result)

        # 3. 处理符号
        result = self._process_symbols(result)

        # 4. 处理格式命令
        result = self._process_format_commands(result)

        # 5. 处理空白和间距
        result = self._process_spaces(result)

        # 6. 处理环境
        result = self._process_environments(result)

        # 7. 处理交叉引用
        result = self._process_references(result)

        # 8. 处理数学公式（可选）
        if preserve_math:
            result = self._process_math(result)

        # 9. 清理未处理的命令
        result = self._cleanup_remaining_commands(result)

        return result

    def _remove_comments(self, content: str) -> str:
        """移除 LaTeX 注释"""
        lines = content.split('\n')
        processed = []

        for line in lines:
            # 查找注释符号（不在字符串内）
            in_math = False
            result_line = []
            i = 0

            while i < len(line):
                char = line[i]

                # 跟踪数学模式
                if char == '$':
                    in_math = not in_math
                    result_line.append(char)
                elif not in_math and char == '%':
                    # 注释开始
                    break
                else:
                    result_line.append(char)

                i += 1

            processed.append(''.join(result_line))

        return '\n'.join(processed)

    def _process_special_chars(self, content: str) -> str:
        """处理 LaTeX 特殊字符"""
        for pattern, replacement, _ in self.special_char_mappings:
            content = re.sub(pattern, replacement, content)
        return content

    def _process_symbols(self, content: str) -> str:
        """处理特殊符号"""
        for pattern, replacement, _ in self.symbol_mappings:
            content = re.sub(pattern, replacement, content)
        return content

    def _process_format_commands(self, content: str) -> str:
        """处理格式命令"""
        for pattern, replacement, _ in self.format_mappings:
            content = re.sub(pattern, replacement, content)
        return content

    def _process_spaces(self, content: str) -> str:
        """处理空白和间距"""
        for pattern, replacement, _ in self.space_mappings:
            content = re.sub(pattern, replacement, content)
        return content

    def _process_environments(self, content: str) -> str:
        """处理 LaTeX 环境"""
        for pattern, replacement, _ in self.environment_mappings:
            content = re.sub(pattern, replacement, content)
        return content

    def _process_references(self, content: str) -> str:
        """处理交叉引用"""
        for pattern, replacement, _ in self.reference_mappings:
            content = re.sub(pattern, replacement, content)
        return content

    def _process_math(self, content: str) -> str:
        """处理数学公式"""
        # 处理行内公式 $...$
        content = re.sub(
            r'\$([^\$]+)\$',
            lambda m: self._convert_math_inline(m.group(1)),
            content
        )

        # 处理显示公式 $$...$$ 或 \[...\]
        content = re.sub(
            r'\$\$([^\$]+)\$\$',
            lambda m: f"\n$${m.group(1)}$$\n",
            content
        )

        # 处理 \[...\]
        content = re.sub(
            r'\\\[([^\]]+)\\\]',
            lambda m: f"\n$${m.group(1)}$$\n",
            content
        )

        return content

    def _convert_math_inline(self, math: str) -> str:
        """
        转换行内数学公式为更兼容的格式

        参数：
            math: 数学公式内容

        返回：
            转换后的公式
        """
        # 简单处理：保留基本结构
        result = math

        # 处理分数
        result = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', result)

        # 处理上下标
        result = re.sub(r'\^{([^}]+)}', r'^\1', result)
        result = re.sub(r'_\{([^}]+)\}', r'_\1', result)

        return f'${result}$'

    def _cleanup_remaining_commands(self, content: str) -> str:
        """清理剩余的未处理命令"""
        # 移除剩余的 LaTeX 命令的花括号
        content = re.sub(r'\{([^{}]*)\}', r'\1', content)

        # 清理空的命令
        content = re.sub(r'\\[a-zA-Z]+\s*', '', content)

        # 清理多余的空白
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    def extract_labels(self, content: str) -> Dict[str, str]:
        """
        提取文档中的标签定义

        参数：
            content: LaTeX 内容

        返回：
            标签到类型的映射 {标签: 类型}
        """
        labels = {}

        # figure 标签
        for match in re.finditer(r'\\begin\{figure[^}]*\}\s*(?:\\label\{([^}]+)\})?', content):
            if match.group(1):
                labels[match.group(1)] = 'figure'

        # table 标签
        for match in re.finditer(r'\\begin\{table[^}]*\}\s*(?:\\label\{([^}]+)\})?', content):
            if match.group(1):
                labels[match.group(1)] = 'table'

        # equation 标签
        for match in re.finditer(r'\\begin\{equation[^}]*\}\s*(?:\\label\{([^}]+)\})?', content):
            if match.group(1):
                labels[match.group(1)] = 'equation'

        # 通用 \label 命令
        for match in re.finditer(r'\\label\{([^}]+)\}', content):
            label = match.group(1)
            if label not in labels:
                labels[label] = 'unknown'

        return labels

    def get_processing_summary(self, content: str) -> str:
        """
        获取处理摘要

        参数：
            content: 处理后的内容

        返回：
            摘要信息
        """
        # 统计各种元素
        item_count = len(re.findall(r'(?:\\item|^\s*-\s+)', content, re.MULTILINE))
        ref_count = len(re.findall(r'\\ref\{[^}]+\}', content))
        cite_count = len(re.findall(r'\\cite[pt]?\{[^}]+\}', content))
        math_blocks = len(re.findall(r'\$\$[^\$]+\$\$|\\\[.+?\\\]', content, re.DOTALL))

        lines = [
            "=" * 50,
            "LaTeX 处理摘要",
            "=" * 50,
            f"列表项数量: {item_count}",
            f"交叉引用数量: {ref_count}",
            f"引文数量: {cite_count}",
            f"数学公式块: {math_blocks}",
            "=" * 50,
        ]

        return "\n".join(lines)
