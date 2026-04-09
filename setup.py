# -*- coding: utf-8 -*-
"""
测试 LaTeX 到 DOCX 转换工具

这些测试用例展示了工具的核心功能。
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import (
    LaTeXProjectParser,
    LaTeXMerger,
    LaTeXCommandHandler,
    CitationHandler
)


def test_parser():
    """测试项目解析器"""
    print("\n" + "=" * 50)
    print("测试 1: 项目解析器")
    print("=" * 50)

    # 创建一个简单的测试项目
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建主文件
        main_tex = os.path.join(tmpdir, 'main.tex')
        with open(main_tex, 'w', encoding='utf-8') as f:
            f.write(r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{graphicx}
\bibliography{refs}

\begin{document}

\title{测试文档}
\author{测试作者}

\maketitle

\include{chapter1}
\include{chapter2}

\bibliographystyle{plain}
\bibliography{refs}

\end{document}
""")

        # 创建章节文件
        chapter1 = os.path.join(tmpdir, 'chapter1.tex')
        with open(chapter1, 'w', encoding='utf-8') as f:
            f.write(r"""\section{第一章}
这是第一章的内容。

\subsection{第一节}
这里是第一节的内容。
""")

        chapter2 = os.path.join(tmpdir, 'chapter2.tex')
        with open(chapter2, 'w', encoding='utf-8') as f:
            f.write(r"""\section{第二章}
这是第二章的内容。
""")

        # 创建 bib 文件
        refs_bib = os.path.join(tmpdir, 'refs.bib')
        with open(refs_bib, 'w', encoding='utf-8') as f:
            f.write(r"""@article{test2024,
    author = {Test Author},
    title = {Test Title},
    journal = {Test Journal},
    year = {2024},
}
""")

        # 解析项目
        parser = LaTeXProjectParser(tmpdir)
        project_info = parser.parse()

        print(f"✓ 项目根目录: {project_info.root_dir}")
        print(f"✓ 主入口文件: {project_info.main_file}")
        print(f"✓ Tex 文件数: {len(project_info.tex_files)}")
        print(f"✓ Bib 文件数: {len(project_info.bib_files)}")
        print(f"✓ 章节文件: {len(project_info.chapter_files)}")

        print("\n" + parser.print_project_structure())

        return project_info


def test_merger(project_info):
    """测试文件合并器"""
    print("\n" + "=" * 50)
    print("测试 2: 文件合并器")
    print("=" * 50)

    merger = LaTeXMerger(project_info)
    merged_content = merger.merge()

    print(f"✓ 合并完成")
    print(f"✓ 合并后长度: {len(merged_content)} 字符")
    print(f"✓ 包含章节数: {merged_content.count('section')}")

    print("\n合并报告:")
    print(merger.get_merge_report())

    return merged_content


def test_command_handler(content):
    """测试命令处理器"""
    print("\n" + "=" * 50)
    print("测试 3: 命令处理器")
    print("=" * 50)

    handler = LaTeXCommandHandler()
    processed = handler.process(content)

    print(f"✓ 处理完成")
    print(f"✓ 处理后长度: {len(processed)} 字符")

    # 提取标签
    labels = handler.extract_labels(processed)
    print(f"✓ 提取的标签: {labels}")

    print("\n处理摘要:")
    print(handler.get_processing_summary(processed))

    return processed


def test_citation_handler(content):
    """测试引文处理器"""
    print("\n" + "=" * 50)
    print("测试 4: 引文处理器")
    print("=" * 50)

    handler = CitationHandler()

    # 创建测试 bib 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
        f.write(r"""@article{smith2024,
    author = {Smith, John and Doe, Jane},
    title = {A Great Paper},
    journal = {Nature},
    year = {2024},
    volume = {100},
    pages = {1--20},
}

@book{latexguide,
    author = {Lamport, Leslie},
    title = {LaTeX: A Document Preparation System},
    publisher = {Addison-Wesley},
    year = {1994},
}
""")
        bib_file = f.name

    try:
        # 加载 bib 文件
        count = handler.load_bib_file(bib_file)
        print(f"✓ 加载 {count} 条参考文献")

        # 处理内容中的引文
        test_content = r"""
参考文献见 \cite{smith2024} 和 \citep{latexguide}。

根据 \citet{smith2024} 的研究，...

又见 \citeyear{latexguide} 的著作。
"""
        processed = handler.process_citations(test_content, style='pandoc')
        print(f"✓ 引文处理完成")
        print(f"\n处理后的引文:")
        print(processed)

        print("\n" + handler.get_citation_report())

    finally:
        os.unlink(bib_file)

    return handler


def test_full_pipeline():
    """测试完整流程"""
    print("\n" + "=" * 50)
    print("测试 5: 完整转换流程")
    print("=" * 50)

    # 创建测试项目
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建主文件
        main_tex = os.path.join(tmpdir, 'main.tex')
        with open(main_tex, 'w', encoding='utf-8') as f:
            f.write(r"""\documentclass{article}
\usepackage{graphicx}

\begin{document}

\title{测试论文}
\author{张三}

\maketitle

\include{intro}
\include{method}

\bibliographystyle{plain}
\bibliography{refs}

\end{document}
""")

        # 创建章节
        intro = os.path.join(tmpdir, 'intro.tex')
        with open(intro, 'w', encoding='utf-8') as f:
            f.write(r"""\section{引言}
这是引言部分。

如图 \ref{fig:example} 所示。

\begin{figure}
\centering
\includegraphics{image.png}
\caption{示例图片}
\label{fig:example}
\end{figure}
""")

        method = os.path.join(tmpdir, 'method.tex')
        with open(method, 'w', encoding='utf-8') as f:
            f.write(r"""\section{方法}
这是方法部分。

根据 \cite{test2024} 的研究，我们采用以下方法。
""")

        # 创建 bib 文件
        refs = os.path.join(tmpdir, 'refs.bib')
        with open(refs, 'w', encoding='utf-8') as f:
            f.write(r"""@article{test2024,
    author = {张三 and 李四},
    title = {测试研究},
    journal = {测试期刊},
    year = {2024},
}
""")

        # 执行完整流程
        from main import LaTeX2DOCXConverter

        converter = LaTeX2DOCXConverter(tmpdir)
        converter.parse()
        converter.merge()
        converter.process()
        converter.process_citations()

        print(f"✓ 解析完成: {len(converter.project_info.tex_files)} 个文件")
        print(f"✓ 合并完成: {len(converter.merged_content)} 字符")
        print(f"✓ 处理完成: {len(converter.processed_content)} 字符")
        print(f"✓ 引文处理完成: {len(converter.citation_handler.bib_entries)} 条")

        # 保存中间结果
        output_dir = os.path.join(tmpdir, 'output')
        saved = converter.save_intermediate(output_dir)
        print(f"\n✓ 中间结果已保存:")
        for name, path in saved.items():
            print(f"  - {name}: {os.path.basename(path)}")

        # 生成报告
        print("\n" + converter.get_report())


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("  LaTeX 到 DOCX 转换工具 - 测试套件")
    print("=" * 60)

    try:
        # 测试各个组件
        project_info = test_parser()
        merged_content = test_merger(project_info)
        processed_content = test_command_handler(merged_content)
        test_citation_handler(processed_content)

        # 测试完整流程
        test_full_pipeline()

        print("\n" + "=" * 60)
        print("  所有测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
