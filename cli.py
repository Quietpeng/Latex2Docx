#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LaTeX 到 DOCX 智能转换工具 - CLI 界面

用法:
    python cli.py <输入目录> <输出文件>

示例:
    python cli.py ./latex_project ./output.docx
    python cli.py /path/to/project paper.docx
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import LaTeX2DOCXConverter


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='latex2docx',
        description='LaTeX 到 DOCX 智能转换工具\n\n自动检测项目结构、合并多文件、处理参考文献。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python cli.py ./latex_project ./output.docx
    python cli.py /path/to/project paper.docx

必选参数:
    输入目录      LaTeX 项目根目录（包含主 .tex 文件）
    输出文件      输出的 DOCX 文件路径
"""
    )

    # 位置参数
    parser.add_argument(
        'input_dir',
        help='LaTeX 项目目录'
    )

    parser.add_argument(
        'output_file',
        help='输出的 DOCX 文件路径'
    )

    # 可选参数
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细输出'
    )

    parser.add_argument(
        '--reference-doc',
        default='',
        help='参考 DOCX 模板（用于继承页眉页脚/页码/字体/段落/表格样式等）'
    )

    parser.add_argument(
        '--csl',
        default='',
        help='CSL 样式文件（用于控制参考文献/引文的排版样式）'
    )

    parser.add_argument(
        '--no-preserve-pagebreaks',
        dest='preserve_pagebreaks',
        action='store_false',
        help='禁用分页符保留（默认启用：把 \\newpage/\\clearpage 等映射为 Word 分页符）'
    )
    parser.set_defaults(preserve_pagebreaks=True)

    parser.add_argument(
        '--version',
        action='version',
        version='latex2docx 1.0.0'
    )

    return parser


def main() -> int:
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 验证输入目录
    input_dir = os.path.abspath(args.input_dir)
    if not os.path.exists(input_dir):
        print(f"错误: 输入目录不存在: {input_dir}", file=sys.stderr)
        return 1

    if not os.path.isdir(input_dir):
        print(f"错误: 输入路径不是目录: {input_dir}", file=sys.stderr)
        return 1

    # 验证输出文件
    output_file = os.path.abspath(args.output_file)
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 打印开始信息
    print("=" * 60)
    print("  LaTeX 到 DOCX 智能转换工具")
    print("=" * 60)
    print()
    print(f"输入目录: {input_dir}")
    print(f"输出文件: {output_file}")
    print()

    try:
        # 组装配置（传入 Pandoc 侧的样式/参考文献控制项）
        reference_doc = os.path.abspath(args.reference_doc) if args.reference_doc else ''
        if reference_doc and not os.path.exists(reference_doc):
            print(f"错误: reference-doc 不存在: {reference_doc}", file=sys.stderr)
            return 1

        csl_file = os.path.abspath(args.csl) if args.csl else ''
        if csl_file and not os.path.exists(csl_file):
            print(f"错误: csl 不存在: {csl_file}", file=sys.stderr)
            return 1

        config = {
            'reference_doc': reference_doc,
            'csl': csl_file,
            'preserve_pagebreaks': bool(args.preserve_pagebreaks),
            # 默认让 Pandoc 直接读取 LaTeX，结构保真更高
            'pandoc_from_format': 'latex',
        }

        # 创建转换器
        converter = LaTeX2DOCXConverter(input_dir, config=config)

        if args.verbose:
            print("[1/5] 解析项目结构...")
        converter.parse()

        if args.verbose:
            print(f"  - 发现 {len(converter.project_info.tex_files)} 个 .tex 文件")
            print(f"  - 发现 {len(converter.project_info.bib_files)} 个 .bib 文件")
            print(f"  - 主文件: {os.path.basename(converter.project_info.main_file)}")

        if args.verbose:
            print("[2/5] 合并文件...")
        converter.merge()

        if args.verbose:
            print(f"  - 合并后内容: {len(converter.merged_content)} 字符")

        if args.verbose:
            print("[3/5] 处理 LaTeX 命令...")
        converter.process()

        if args.verbose:
            print(f"  - 处理后内容: {len(converter.processed_content)} 字符")

        if args.verbose:
            print("[4/5] 处理参考文献...")
        converter.process_citations()

        bib_count = len(converter.citation_handler.bib_entries) if converter.citation_handler else 0
        if args.verbose:
            print(f"  - 加载 {bib_count} 条参考文献")

        if args.verbose:
            print("[5/5] 生成 DOCX...")
        success, message = converter.convert_to_docx(output_file)

        if success:
            size = os.path.getsize(output_file)
            print()
            print("=" * 60)
            print("  转换成功!")
            print("=" * 60)
            print(f"输出文件: {output_file}")
            print(f"文件大小: {size / 1024:.1f} KB")
            return 0
        else:
            print()
            print("=" * 60)
            print(f"  转换失败: {message}")
            print("=" * 60)
            return 1

    except KeyboardInterrupt:
        print("\n\n操作已取消")
        return 130

    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
