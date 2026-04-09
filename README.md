# LaTeX → DOCX 转换工具（尽可能贴近 XeLaTeX PDF）

## 项目简介

本工具面向“多文件/图片/表格/参考文献/复杂宏”的 LaTeX 项目，目标是把内容转换为 **可编辑的 DOCX**，并尽可能接近 `xelatex → biber → xelatex ×2` 的排版效果。对应的skill已建立在[Latex2DocxSkill
](https://github.com/Quietpeng/Latex2DocxSkill.git)

### 核心能力（当前实现）

- **Pandoc 直接读取 LaTeX**：避免“正则清洗→Markdown”导致的结构损坏，图片/表格/引用更稳。
- **项目级资源解析**：转换时在项目根目录运行，并设置 `--resource-path`，提升相对路径图片命中率。
- **参考文献/引文**：使用 `--citeproc` + `.bib` 文件生成参考文献列表。
- **条件宏鲁棒处理**：预处理展开 `\IfFileExists{path}{then}{else}`（按真实文件存在性选择分支），避免图片被整体跳过。
- **换页保留（重要）**：默认把 `\newpage/\clearpage/\cleardoublepage/\pagebreak` 映射为 Word 真分页符（DOCX 后处理）。
- **样式继承（推荐）**：支持 `--reference-doc` 继承页眉页脚/页码/字体/段落/表格样式。
- **CSL 样式**：支持 `--csl` 控制参考文献/引文排版。

## 快速开始

### 1) 安装依赖

- 安装 Pandoc：https://pandoc.org/installing.html

### 2) Python 依赖（推荐使用虚拟环境）

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3) 运行转换

```bash
# 基本用法
python cli.py <输入目录> <输出文件>

# 推荐：带 verbose 输出
python cli.py .\test-latex .\out.docx -v

# 推荐：用 reference.docx 继承样式（页眉页脚/页码/字体/段落/表格样式等）
python cli.py .\test-latex .\out.docx --reference-doc .\reference.docx -v

# 可选：指定 CSL（参考文献/引文样式）
python cli.py .\test-latex .\out.docx --csl .\ieee.csl -v
```

## 命令行参数

```bash
python cli.py <输入目录> <输出文件>

参数:
  输入目录      LaTeX 项目根目录（包含主 .tex 文件）
  输出文件      输出的 DOCX 文件路径

选项:
  -v, --verbose              显示详细输出
  --reference-doc <docx>     参考 DOCX 模板（继承页眉页脚/页码/字体/段落/表格样式等）
  --csl <csl>                CSL 样式文件（控制参考文献/引文排版）
  --no-preserve-pagebreaks   禁用“换页→Word 分页符”后处理（默认启用）
```

## 如何让版式更像 LaTeX PDF（强烈推荐）

Pandoc 生成 DOCX 时，“字体字号/段前段后/行距/表格边框/标题样式/页眉页脚/页码”等**主要由 Word 样式决定**。

做法：
1. 用 Word 新建一个 `reference.docx`。
2. 在里面配置好：
   - 正文/标题（Heading 1/2/3）字体字号
   - 段前段后、行距、首行缩进
   - 表格样式（边框、底纹、字体）
   - 图注/表注样式（Caption）
   - 页眉页脚与页码
3. 转换时传入：`--reference-doc reference.docx`。

## 已知限制（现实边界）

- LaTeX 的分页/浮动体摆放（figure/table）与 Word 的布局机制不同：**内容会尽量保真，但版面不可能 100% 一致**。
- 复杂自定义宏/包（非 Pandoc LaTeX reader 支持范围内）仍可能降级为纯文本或丢失部分语义。
- 如果你需要“像 PDF 一样”的页眉页脚/页码/段落样式：请使用 `--reference-doc`；不要期望 Pandoc 自动推断 LaTeX 的版式参数。

## 故障排除

### 1) Pandoc 未找到

```bash
pandoc --version

# Windows
where pandoc

# macOS/Linux
# which pandoc
```

### 2) 图片缺失/路径找不到

- 确认图片文件真实存在于项目内（相对路径以项目根目录为基准）。
- 如果图片在 `\IfFileExists{...}{\includegraphics{...}}{...}` 里：本工具会按文件系统展开分支，但路径写法仍需能解析到真实文件。
- 使用 `-v` 查看解析到的主文件与项目根目录。

### 3) 换页不生效

- 默认已开启“换页→Word 分页符”。
- 若你显式传了 `--no-preserve-pagebreaks`，则会禁用该行为。

## Python API（可选）

```python
from main import LaTeX2DOCXConverter

config = {
    'pandoc_from_format': 'latex',
    'reference_doc': r'.\\reference.docx',
    'csl': r'.\\ieee.csl',
    'preserve_pagebreaks': True,
}

converter = LaTeX2DOCXConverter(r'.\\test-latex', config=config)
converter.parse().merge().process().process_citations()
ok, msg = converter.convert_to_docx(r'.\\out.docx')
print(ok, msg)
```

## 修改记录

- 2026-04-09 — 支持 `--reference-doc/--csl`；默认保留 LaTeX 换页为 Word 真分页符；增强 `\IfFileExists` 场景下的图片解析。

## 许可证

MIT License

## 最后

该死的不要找我要word版本的了，PDF还不够吗qwq
