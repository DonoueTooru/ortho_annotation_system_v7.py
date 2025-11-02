#!/usr/bin/env python3
"""
SVGアイコンをPNG形式に一括変換するスクリプト
使用方法: python convert_svg_to_png.py
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
    import cairosvg
    from io import BytesIO
except ImportError as e:
    print(f"エラー: 必要なライブラリがインストールされていません: {e}")
    print("以下のコマンドでインストールしてください:")
    print("  pip install Pillow cairosvg")
    sys.exit(1)


def convert_svg_to_png(svg_path, png_path, size=256):
    """
    SVGファイルをPNG形式に変換
    
    Args:
        svg_path: 変換元SVGファイルパス
        png_path: 変換先PNGファイルパス
        size: 出力サイズ（正方形）
    """
    try:
        # SVG → PNG変換
        png_bytes = cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)
        
        # Pillowで読み込んでRGBA変換
        image = Image.open(BytesIO(png_bytes)).convert("RGBA")
        
        # PNG保存
        image.save(png_path, "PNG", optimize=True)
        
        return True
    except Exception as e:
        print(f"  エラー: {e}")
        return False


def main():
    # スクリプトと同じディレクトリの「アノテーション画像フォルダ」を探す
    script_dir = Path(__file__).parent
    icon_dir = script_dir / "アノテーション画像フォルダ"
    
    if not icon_dir.exists():
        print(f"エラー: アイコンフォルダが見つかりません: {icon_dir}")
        print("フォルダを作成するか、パスを確認してください。")
        sys.exit(1)
    
    print(f"📁 アイコンフォルダ: {icon_dir}")
    print("=" * 60)
    
    # SVGファイルを検索
    svg_files = list(icon_dir.glob("*.svg"))
    
    if not svg_files:
        print("⚠️  SVGファイルが見つかりません。")
        sys.exit(0)
    
    print(f"🔍 {len(svg_files)}個のSVGファイルを発見しました。\n")
    
    # 変換処理
    success_count = 0
    fail_count = 0
    
    for svg_file in svg_files:
        png_file = svg_file.with_suffix('.png')
        
        print(f"🔄 変換中: {svg_file.name} → {png_file.name}")
        
        if convert_svg_to_png(str(svg_file), str(png_file), size=256):
            success_count += 1
            file_size = png_file.stat().st_size / 1024  # KB
            print(f"  ✅ 完了 ({file_size:.1f} KB)")
        else:
            fail_count += 1
            print(f"  ❌ 失敗")
    
    # サマリー
    print("\n" + "=" * 60)
    print(f"✨ 変換完了!")
    print(f"  成功: {success_count} 件")
    print(f"  失敗: {fail_count} 件")
    print(f"  合計: {len(svg_files)} 件")
    
    if success_count > 0:
        print(f"\n📂 変換されたPNGファイルは以下にあります:")
        print(f"  {icon_dir}")


if __name__ == "__main__":
    main()
