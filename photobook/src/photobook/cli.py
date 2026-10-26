import argparse
import os
import sys
import tempfile
from pathlib import Path

import yaml

from photobook.config import DEFAULT_CONFIG, load_config
from photobook.layout import build_pages
from photobook.metadata import sort_by_capture_time
from photobook.renderer import render_pdf
from photobook.scanner import scan_images


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="photobook",
        description="photo/ の画像からミニマルな正方形フォトブックPDFを生成します。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="config.yaml を作成")
    init_parser.add_argument("--config", default="config.yaml", help="設定ファイルのパス")

    build_parser = subparsers.add_parser("build", help="フォトブックPDFを生成")
    build_parser.add_argument("--config", default="config.yaml", help="設定ファイルのパス")
    build_parser.add_argument(
        "--overwrite", action="store_true",
        help="出力PDFが存在する場合に上書きする（明示指定が必要）",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()

    try:
        if args.command == "init":
            config_path = Path(args.config)
            if config_path.exists():
                print(f"エラー: 設定ファイルが既に存在します: {config_path}", file=sys.stderr)
                return 2
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                yaml.safe_dump(DEFAULT_CONFIG, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            print(f"設定ファイルを作成しました: {config_path}")
            return 0

        config = load_config(Path(args.config))
        input_dir = Path(config["input"]["directory"])
        output_dir = Path(config["output"]["directory"])
        output_path = output_dir / config["output"]["filename"]
        overwrite = args.overwrite or config["output"]["overwrite"]

        images = scan_images(
            input_dir,
            recursive=config["input"]["recursive"],
            extensions=config["input"]["extensions"],
        )
        if not images:
            print(f"エラー: 対象画像がありません: {input_dir}", file=sys.stderr)
            return 1

        images = sort_by_capture_time(images)
        layout_config = config["layout"]
        pages = build_pages(
            images,
            mode=layout_config["mode"],
            max_photos_per_page=layout_config["max_photos_per_page"],
        )

        if output_path.exists() and not overwrite:
            print(
                f"エラー: 出力ファイルが既に存在します: {output_path}\n"
                "上書きするには `photobook build --overwrite` を指定してください。",
                file=sys.stderr,
            )
            return 2

        output_dir.mkdir(parents=True, exist_ok=True)
        # Render to a temporary PDF in the same directory, then replace the final file.
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=".photobook-", suffix=".pdf", dir=output_dir, delete=False
            ) as temp_file:
                temp_name = temp_file.name

            render_pdf(
                pages=pages,
                destination=Path(temp_name),
                title=config["project"]["title"],
                subtitle=config["project"]["subtitle"],
                page_size_mm=float(config["output"]["page_size_mm"]),
                margin_mm=float(config["design"]["margin_mm"]),
                cover_background=config["design"]["cover_background"],
                page_background=config["design"]["page_background"],
                title_color=config["design"]["title_color"],
                gap_mm=float(config["layout"]["gap_mm"]),
                random_seed=config["layout"]["random_seed"],
                layout_mode=config["layout"]["mode"],
            )
            if output_path.exists() and not overwrite:
                print(f"エラー: 出力ファイルが生成中に作成されました: {output_path}", file=sys.stderr)
                return 2
            os.replace(temp_name, output_path)
            temp_name = None
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

        print(f"PDFを生成しました: {output_path}")
        print(f"写真枚数: {len(images)} / 総ページ数: {len(pages) + 1}")
        return 0

    except (FileNotFoundError, ValueError, OSError, KeyError, TypeError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
