#!/usr/bin/env python3
"""
SVGアイコンをPNGに変換する簡易版スクリプト（Windows対応）
cairosvgの代わりにsvglib + reportlabを使用
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as e:
    print(f"エラー: Pillowがインストールされていません: {e}")
    print("以下のコマンドでインストールしてください:")
    print("  pip install Pillow")
    sys.exit(1)

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
except ImportError:
    print("エラー: svglib と reportlab がインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip install svglib reportlab")
    sys.exit(1)


def convert_svg_to_png_simple(svg_path, png_path, size=256):
    """
    SVGファイルをPNG形式に変換（svglib使用）
    
    Args:
        svg_path: 変換元SVGファイルパス
        png_path: 変換先PNGファイルパス
        size: 出力サイズ（正方形）
    """
    try:
        # SVG → ReportLabのDrawingオブジェクトに変換
        drawing = svg2rlg(svg_path)
        
        if drawing is None:
            print(f"  ⚠️  SVG読み込み失敗")
            return False
        
        # PNG生成（一時ファイル）
        temp_png = str(png_path) + ".tmp.png"
        renderPM.drawToFile(drawing, temp_png, fmt="PNG", dpi=72)
        
        # Pillowで開いてリサイズ＆最適化
        with Image.open(temp_png) as img:
            # RGBA変換
            img = img.convert("RGBA")
            
            # 正方形にリサイズ
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            
            # 最終PNG保存
            img.save(png_path, "PNG", optimize=True)
        
        # 一時ファイル削除
        if os.path.exists(temp_png):
            os.remove(temp_png)
        
        return True
        
    except Exception as e:
        print(f"  エラー: {e}")
        # 一時ファイルのクリーンアップ
        temp_png = str(png_path) + ".tmp.png"
        if os.path.exists(temp_png):
            try:
                os.remove(temp_png)
            except:
                pass
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
    print("🔄 変換方法: svglib + reportlab (Windows対応)")
    print()
    
    # 変換処理
    success_count = 0
    fail_count = 0
    
    for svg_file in svg_files:
        png_file = svg_file.with_suffix('.png')
        
        print(f"🔄 変換中: {svg_file.name} → {png_file.name}")
        
        if convert_svg_to_png_simple(str(svg_file), str(png_file), size=256):
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
