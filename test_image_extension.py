#!/usr/bin/env python3
"""
画像拡張機能のテストスクリプト
"""
import os
from PIL import Image, ImageDraw

print("=" * 70)
print("画像拡張機能テスト")
print("=" * 70)

# テスト用のプロジェクトを作成
test_project_path = "/home/user/webapp/test_extension"
os.makedirs(test_project_path, exist_ok=True)
os.makedirs(os.path.join(test_project_path, "output"), exist_ok=True)

# テスト用の元画像を作成
original_width = 800
original_height = 600
original_image = Image.new('RGB', (original_width, original_height), color=(200, 200, 200))
draw = ImageDraw.Draw(original_image)

# グリッド線を描画（座標確認用）
for i in range(0, original_width, 100):
    draw.line([(i, 0), (i, original_height)], fill=(150, 150, 150), width=1)
for i in range(0, original_height, 100):
    draw.line([(0, i), (original_width, i)], fill=(150, 150, 150), width=1)

# 中央に元画像サイズを表示
draw.text((original_width//2 - 100, original_height//2), 
          f"Original: {original_width}x{original_height}", 
          fill=(0, 0, 0))

print(f"\n[テスト1] 元画像の作成")
print(f"  サイズ: {original_width} x {original_height}")

# 拡張率のテスト
extension_ratios = [1/3, 1/2, 1/4, 0.1]

for ratio in extension_ratios:
    print(f"\n[テスト2] 拡張率: {ratio:.3f} ({ratio*100:.1f}%)")
    
    # 拡張サイズを計算
    total_extension = int(original_height * ratio)
    top_extension = total_extension // 2
    bottom_extension = total_extension - top_extension
    new_height = original_height + top_extension + bottom_extension
    
    print(f"  元の高さ: {original_height}px")
    print(f"  拡張合計: {total_extension}px")
    print(f"  上部拡張: {top_extension}px")
    print(f"  下部拡張: {bottom_extension}px")
    print(f"  新しい高さ: {new_height}px")
    
    # 拡張画像を作成
    extended_image = Image.new('RGB', (original_width, new_height), (255, 255, 255))
    extended_image.paste(original_image, (0, top_extension))
    
    # 拡張領域を可視化（薄い黄色）
    draw_ext = ImageDraw.Draw(extended_image)
    draw_ext.rectangle([0, 0, original_width, top_extension], 
                       outline=(255, 200, 0), width=3)
    draw_ext.rectangle([0, new_height - bottom_extension, original_width, new_height], 
                       outline=(255, 200, 0), width=3)
    
    # 情報テキストを追加
    draw_ext.text((10, 10), f"Top Extension: {top_extension}px", fill=(255, 0, 0))
    draw_ext.text((10, new_height - 30), f"Bottom Extension: {bottom_extension}px", fill=(255, 0, 0))
    
    # 保存
    output_path = os.path.join(test_project_path, "output", f"extended_ratio_{ratio:.3f}.jpg")
    extended_image.save(output_path, 'JPEG', quality=95)
    print(f"  ✅ 保存: {os.path.basename(output_path)}")

# テスト3: アノテーション座標の調整テスト
print(f"\n[テスト3] アノテーション座標の調整")

# 拡張率1/3で拡張
ratio = 1/3
total_extension = int(original_height * ratio)
top_extension = total_extension // 2
new_height = original_height + total_extension

extended_image = Image.new('RGB', (original_width, new_height), (255, 255, 255))
extended_image.paste(original_image, (0, top_extension))
draw_ext = ImageDraw.Draw(extended_image)

# テストアノテーション位置
test_annotations = [
    {"x": 100, "y": 0, "label": "上端 (y=0)"},
    {"x": 300, "y": 100, "label": "上部 (y=100)"},
    {"x": 500, "y": original_height // 2, "label": "中央"},
    {"x": 700, "y": original_height - 100, "label": "下部 (y=500)"},
    {"x": 400, "y": original_height, "label": "下端 (y=600)"},
]

print(f"  上部オフセット: {top_extension}px")
print(f"\n  元座標 → 調整後座標:")

for ann in test_annotations:
    original_x = ann["x"]
    original_y = ann["y"]
    adjusted_x = original_x
    adjusted_y = original_y + top_extension
    
    print(f"    {ann['label']:20s} ({original_x:3d}, {original_y:3d}) → ({adjusted_x:3d}, {adjusted_y:3d})")
    
    # アノテーションを描画（赤い十字）
    size = 20
    draw_ext.line([(adjusted_x, adjusted_y - size), (adjusted_x, adjusted_y + size)], 
                  fill=(255, 0, 0), width=3)
    draw_ext.line([(adjusted_x - size, adjusted_y), (adjusted_x + size, adjusted_y)], 
                  fill=(255, 0, 0), width=3)
    draw_ext.text((adjusted_x + 25, adjusted_y - 10), ann['label'], fill=(255, 0, 0))

# 境界線を表示
draw_ext.line([(0, top_extension), (original_width, top_extension)], 
              fill=(0, 255, 0), width=2)  # 元画像の上端
draw_ext.line([(0, top_extension + original_height), (original_width, top_extension + original_height)], 
              fill=(0, 255, 0), width=2)  # 元画像の下端

output_path = os.path.join(test_project_path, "output", "annotation_coordinate_test.jpg")
extended_image.save(output_path, 'JPEG', quality=95)
print(f"\n  ✅ 保存: {os.path.basename(output_path)}")

print("\n" + "=" * 70)
print("✅ すべてのテスト完了")
print("=" * 70)

# 生成されたファイル一覧
output_folder = os.path.join(test_project_path, "output")
files = sorted(os.listdir(output_folder))
print(f"\n生成されたファイル ({len(files)}個):")
for f in files:
    file_path = os.path.join(output_folder, f)
    file_size = os.path.getsize(file_path)
    
    # 画像サイズを取得
    img = Image.open(file_path)
    w, h = img.size
    
    print(f"  - {f:40s} {w:4d}x{h:4d} ({file_size:6,} bytes)")

print(f"\n出力フォルダ: {output_folder}")
