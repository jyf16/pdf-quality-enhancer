# PDF 扫描件批量增强工具

一个基于 PyQt5 的桌面应用，用于批量增强 PDF 扫描件中的图片清晰度与对比度，并导出增强后的 PDF。

## 功能

- 拖拽 PDF 文件或文件夹批量处理
- 可调对比度与锐化参数
- 处理进度提示

## 环境要求

- Python 3.9+
- 依赖见 pyproject.toml 或 requirements.txt

## 安装依赖

使用任一方式即可：

### 方式一：conda

创建并激活环境，然后安装依赖：

```bash
conda create -n pdf-quality-enhancer python=3.10 -y
conda activate pdf-quality-enhancer
pip install -r requirements.txt
```

### 方式二：uv（推荐）

创建并同步环境：

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

也可以直接基于 pyproject.toml 安装：

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 方式三：纯 pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

直接执行脚本：

```bash
python gui.py
```

命令行模式：

```bash
python cli.py <文件或文件夹> [--contrast 2.0] [--radius 1.4] [--percent 100] [--threshold 0]
```

## 使用方法

1. 启动程序后，将 PDF 文件或包含 PDF 的文件夹拖入列表。
2. 调整对比度与锐化参数。
3. 点击“开始处理”。
4. 处理完成后，将在原路径生成 *_enhanced.pdf 文件。

命令行示例：

```bash
python cli.py /path/to/a.pdf /path/to/folder
```

## 说明

- 原文件不被覆盖。
- 处理过程中可能因 PDF 内容或加密设置导致失败，请查看提示信息。
