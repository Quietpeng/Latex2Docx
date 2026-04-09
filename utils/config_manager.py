# -*- coding: utf-8 -*-
"""
配置管理器模块

功能说明：
    管理和加载 LaTeX 到 DOCX 转换工具的配置：
    - 配置文件（YAML, JSON）
    - 命令行参数
    - 默认配置
    - 配置验证

使用示例：
    config = ConfigManager()
    config.load('config.yaml')
    settings = config.get_all()
"""

import os
import json
import yaml
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field


@dataclass
class ConversionConfig:
    """转换配置数据类"""
    # 输入输出
    input_dir: str = ''
    output_file: str = ''
    main_file: str = ''

    # Pandoc 选项
    pandoc_from: str = 'latex'
    pandoc_to: str = 'docx'
    pandoc_options: List[str] = field(default_factory=list)

    # 参考文献
    bib_files: List[str] = field(default_factory=list)
    csl_file: str = ''
    reference_doc: str = ''

    # 处理选项
    encoding: str = 'utf-8'
    preserve_math: bool = True
    process_citations: bool = True
    cleanup_temp: bool = True

    # 路径选项
    resource_paths: List[str] = field(default_factory=list)

    # 输出选项
    verbose: bool = False
    generate_report: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, list):
                result[key] = value
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversionConfig':
        """从字典创建"""
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })


class ConfigManager:
    """
    配置管理器

    支持：
    1. YAML 配置文件
    2. JSON 配置文件
    3. 环境变量
    4. 命令行参数
    5. 默认值
    """

    DEFAULT_CONFIG_FILE = 'latex2docx.yaml'

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        参数：
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config: ConversionConfig = ConversionConfig()
        self._loaded: bool = False

    def load(
        self,
        config_file: Optional[str] = None,
        use_env: bool = True
    ) -> bool:
        """
        加载配置

        参数：
            config_file: 配置文件路径
            use_env: 是否加载环境变量

        返回：
            成功标志
        """
        # 确定配置文件路径
        file_path = config_file or self.config_file

        if file_path and os.path.exists(file_path):
            self._load_file(file_path)
        elif os.path.exists(self.DEFAULT_CONFIG_FILE):
            self._load_file(self.DEFAULT_CONFIG_FILE)

        # 加载环境变量
        if use_env:
            self._load_env()

        self._loaded = True
        return True

    def _load_file(self, file_path: str) -> bool:
        """
        从文件加载配置

        参数：
            file_path: 文件路径

        返回：
            成功标志
        """
        ext = os.path.splitext(file_path)[1].lower()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if ext in ('.yaml', '.yml'):
                    data = yaml.safe_load(f)
                elif ext == '.json':
                    data = json.load(f)
                else:
                    return False

            if data:
                # 合并配置
                self.config = ConversionConfig.from_dict({
                    **self.config.to_dict(),
                    **data
                })

            return True

        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False

    def _load_env(self) -> None:
        """加载环境变量"""
        env_mappings = {
            'LATEX2DOCX_ENCODING': 'encoding',
            'LATEX2DOCX_PANDOC_FROM': 'pandoc_from',
            'LATEX2DOCX_PANDOC_TO': 'pandoc_to',
            'LATEX2DOCX_CSL_FILE': 'csl_file',
            'LATEX2DOCX_REFERENCE_DOC': 'reference_doc',
            'LATEX2DOCX_VERBOSE': 'verbose',
        }

        for env_var, config_key in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                if isinstance(getattr(self.config, config_key), bool):
                    value = value.lower() in ('true', '1', 'yes')
                setattr(self.config, config_key, value)

        # 处理列表类型的环境变量
        bib_files = os.environ.get('LATEX2DOCX_BIB_FILES')
        if bib_files:
            self.config.bib_files = [
                f.strip() for f in bib_files.split(',')
            ]

        resource_paths = os.environ.get('LATEX2DOCX_RESOURCE_PATHS')
        if resource_paths:
            self.config.resource_paths = [
                p.strip() for p in resource_paths.split(',')
            ]

    def save(self, file_path: Optional[str] = None) -> bool:
        """
        保存配置

        参数：
            file_path: 保存路径

        返回：
            成功标志
        """
        save_path = file_path or self.config_file or self.DEFAULT_CONFIG_FILE

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.endswith('.json'):
                    json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
                else:
                    yaml.dump(self.config.to_dict(), f, allow_unicode=True, default_flow_style=False)

            return True

        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        参数：
            key: 配置键
            default: 默认值

        返回：
            配置值
        """
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置配置值

        参数：
            key: 配置键
            value: 配置值
        """
        if hasattr(self.config, key):
            setattr(self.config, key, value)

    def get_all(self) -> ConversionConfig:
        """
        获取所有配置

        返回：
            配置对象
        """
        return self.config

    def update(self, updates: Dict[str, Any]) -> None:
        """
        更新配置

        参数：
            updates: 更新字典
        """
        for key, value in updates.items():
            self.set(key, value)

    def is_loaded(self) -> bool:
        """
        检查配置是否已加载

        返回：
            是否已加载
        """
        return self._loaded

    def validate(self) -> List[str]:
        """
        验证配置

        返回：
            错误列表，空列表表示验证通过
        """
        errors = []

        # 检查必要的配置
        if not self.config.input_dir and not self.config.main_file:
            errors.append("缺少输入配置：input_dir 或 main_file")

        if not self.config.output_file:
            errors.append("缺少输出配置：output_file")

        # 检查文件是否存在
        if self.config.main_file and not os.path.exists(self.config.main_file):
            errors.append(f"主文件不存在: {self.config.main_file}")

        for bib in self.config.bib_files:
            if not os.path.exists(bib):
                errors.append(f"参考文献文件不存在: {bib}")

        if self.config.csl_file and not os.path.exists(self.config.csl_file):
            errors.append(f"CSL 文件不存在: {self.config.csl_file}")

        if self.config.reference_doc and not os.path.exists(self.config.reference_doc):
            errors.append(f"参考文档不存在: {self.config.reference_doc}")

        return errors

    def to_pandoc_options(self) -> List[str]:
        """
        将配置转换为 Pandoc 选项

        返回：
            Pandoc 命令行参数列表
        """
        options = []

        # 格式
        options.extend(['-f', self.config.pandoc_from])
        options.extend(['-t', self.config.pandoc_to])

        # 输出
        options.extend(['-o', self.config.output_file])

        # 参考文献
        for bib in self.config.bib_files:
            options.extend(['--bibliography', bib])

        if self.config.csl_file:
            options.extend(['--csl', self.config.csl_file])

        # 参考文档
        if self.config.reference_doc:
            options.extend(['--reference-doc', self.config.reference_doc])

        # 资源路径
        for path in self.config.resource_paths:
            options.extend(['--resource-path', path])

        # 引用处理
        if self.config.process_citations:
            options.append('--citeproc')

        # 其他选项
        options.extend(self.config.pandoc_options)

        return options

    def create_sample_config(self, file_path: str) -> bool:
        """
        创建示例配置文件

        参数：
            file_path: 配置文件路径

        返回：
            成功标志
        """
        sample = {
            'input_dir': '/path/to/latex/project',
            'output_file': 'output.docx',
            'main_file': 'main.tex',
            'pandoc_from': 'latex',
            'pandoc_to': 'docx',
            'bib_files': ['references.bib'],
            'csl_file': '',
            'reference_doc': '',
            'encoding': 'utf-8',
            'preserve_math': True,
            'process_citations': True,
            'cleanup_temp': True,
            'resource_paths': ['./images', './figures'],
            'verbose': False,
            'generate_report': True,
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(sample, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception:
            return False
