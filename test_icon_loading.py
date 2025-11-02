#!/usr/bin/env python3
"""
アイコン読み込み機能のテストスクリプト
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# テスト用のシンプルなアイコンを生成
def create_test_icon(name, color, output_path, size=256):
    """
    テスト用のシンプルなPNGアイコンを生成
    
    Args:
        name: アイコン名（ファイル名とラベルに使用）
        color: アイコンの色（RGB or RGBA）
        output_path: 出力先パス
        size: アイコンサイズ（正方形）
    """
    # 透過背景の画像を作成
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 円形のアイコンを描画
    margin = size // 8
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color,
        outline=(255, 255, 255, 255),
        width=size // 32
    )
    
    # テキストを描画（中央）
    try:
        # フォントサイズを調整
        font_size = size // 8
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("Arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # テキストを中央に配置
    text = name[:4] if len(name) > 4 else name
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2
    
    # 影付きテキスト
    draw.text((text_x + 2, text_y + 2), text, fill=(0, 0, 0, 128), font=font)
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    
    # PNG保存
    img.save(output_path, "PNG", optimize=True)
    print(f"  ✅ 作成: {output_path}")


def main():
    # スクリプトと同じディレクトリの「アノテーション画像フォルダ」を探す
    script_dir = Path(__file__).parent
    icon_dir = script_dir / "アノテーション画像フォルダ"
    
    # フォルダが存在しない場合は作成
    if not icon_dir.exists():
        icon_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 フォルダを作成しました: {icon_dir}")
    
    print(f"📁 アイコンフォルダ: {icon_dir}")
    print("=" * 60)
    print("🎨 テスト用アイコンを生成します...\n")
    
    # デフォルトの不具合分類とその色
    defect_types = {
        "ホットスポット": "#FF0000",  # 赤
        "クラスタ異常": "#FF8C00",    # オレンジ
        "破損": "#FFD700",           # 黄
        "ストリング異常": "#0000FF",  # 青
        "系統異常": "#8A2BE2",       # 紫
        "影": "#008000"              # 緑
    }
    
    created_count = 0
    
    for defect_type, hex_color in defect_types.items():
        # HEX色をRGBAに変換
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        color = (r, g, b, 255)
        
        # アイコンファイルパス
        icon_path = icon_dir / f"{defect_type}.png"
        
        # 既に存在する場合はスキップ
        if icon_path.exists():
            print(f"  ⏭️  スキップ: {icon_path.name} (既存)")
            continue
        
        # アイコン生成
        create_test_icon(defect_type, color, str(icon_path))
        created_count += 1
    
    # サマリー
    print("\n" + "=" * 60)
    print(f"✨ 完了!")
    print(f"  新規作成: {created_count} 件")
    print(f"  既存: {len(defect_types) - created_count} 件")
    print(f"\n📂 アイコン保存先: {icon_dir}")
    
    # アイコンリストを表示
    print("\n📋 生成されたアイコン:")
    for icon_file in sorted(icon_dir.glob("*.png")):
        file_size = icon_file.stat().st_size / 1024  # KB
        print(f"  - {icon_file.name} ({file_size:.1f} KB)")


if __name__ == "__main__":
    main()
