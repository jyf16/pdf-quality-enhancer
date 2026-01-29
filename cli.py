import argparse
import sys

from core import EnhanceParams, collect_pdf_files, process_files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PDF 扫描件批量增强（命令行）"
    )
    parser.add_argument("inputs", nargs="+", help="PDF 文件或包含 PDF 的文件夹")
    parser.add_argument("--contrast", type=float, default=2.0, help="对比度（默认 2.0）")
    parser.add_argument("--radius", type=float, default=1.4, help="锐化半径（默认 1.4）")
    parser.add_argument("--percent", type=int, default=100, help="锐化程度（默认 100）")
    parser.add_argument("--threshold", type=int, default=0, help="锐化阈值（默认 0）")
    parser.add_argument("--suffix", default="_enhanced", help="输出文件后缀")
    parser.add_argument("--quiet", action="store_true", help="静默模式")

    args = parser.parse_args()

    file_list = collect_pdf_files(args.inputs)
    if not file_list:
        print("未找到可处理的 PDF 文件。")
        return 1

    params = EnhanceParams(
        contrast=args.contrast,
        radius=args.radius,
        percent=args.percent,
        threshold=args.threshold,
    )

    def on_status(message: str) -> None:
        if not args.quiet:
            print(message)

    def on_total_progress(current_num: int, total_num: int) -> None:
        if not args.quiet:
            print(f"总进度: {current_num}/{total_num}")

    processed, total = process_files(
        file_list,
        params,
        suffix=args.suffix,
        on_status=on_status,
        on_total_progress=on_total_progress,
    )

    print(f"批量处理完成！成功处理 {processed}/{total} 个文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
