#!/usr/bin/env python3
"""
RGBA画像のJPEG保存エラー修正のテストスクリプト
"""
import os
from PIL import Image, ImageDraw

# テスト用のプロジェクトを作成
test_project_path = "/home/user/webapp/test_rgba_fix"
os.makedirs(test_project_path, exist_ok=True)
os.makedirs(os.path.join(test_project_path, "全体図位置フォルダ"), exist_ok=True)

print("=" * 60)
print("RGBA画像のJPEG保存エラー修正テスト")
print("=" * 60)

# テスト1: RGBA画像を作成
print("\n[テスト1] RGBA画像の作成と保存")
test_image_rgba = Image.new('RGBA', (800, 600), color=(255, 255, 255, 255))
draw = ImageDraw.Draw(test_image_rgba)
draw.text((400, 300), "RGBA Test Image", fill=(0, 0, 0, 255))
draw.ellipse([100, 100, 200, 200], fill=(255, 0, 0, 128))  # 半透明の赤い円

print(f"  画像モード: {test_image_rgba.mode}")
print(f"  画像サイズ: {test_image_rgba.size}")

# RGB変換のテスト
print("\n[テスト2] RGB変換処理のテスト")
annotated_image = test_image_rgba.copy()

# 変換前
print(f"  変換前のモード: {annotated_image.mode}")

# RGB変換（修正したロジックと同じ）
if annotated_image.mode == 'RGBA':
    # 白背景に合成してRGBに変換
    rgb_image = Image.new('RGB', annotated_image.size, (255, 255, 255))
    rgb_image.paste(annotated_image, mask=annotated_image.split()[3])
    annotated_image = rgb_image
    print(f"  ✓ RGBAからRGBに変換しました")
elif annotated_image.mode != 'RGB':
    # その他のモードもRGBに変換
    annotated_image = annotated_image.convert('RGB')
    print(f"  ✓ {annotated_image.mode}からRGBに変換しました")

# 変換後
print(f"  変換後のモード: {annotated_image.mode}")

# JPEG保存テスト
print("\n[テスト3] JPEG保存のテスト")
output_folder = os.path.join(test_project_path, "全体図位置フォルダ")
output_path = os.path.join(output_folder, "ID001_全体図_テスト.jpg")

try:
    annotated_image.save(output_path, 'JPEG', quality=95)
    print(f"  ✅ 保存成功: {output_path}")
    
    # ファイルサイズを確認
    file_size = os.path.getsize(output_path)
    print(f"  ファイルサイズ: {file_size:,} bytes")
    
    # 保存した画像を読み込んで確認
    saved_image = Image.open(output_path)
    print(f"  保存された画像のモード: {saved_image.mode}")
    print(f"  保存された画像のサイズ: {saved_image.size}")
    
except Exception as e:
    print(f"  ❌ 保存失敗: {e}")

# テスト4: 他のモードのテスト
print("\n[テスト4] 各画像モードのテスト")
test_modes = ['RGB', 'RGBA', 'L', 'P']

for mode in test_modes:
    print(f"\n  モード: {mode}")
    
    if mode == 'P':
        # パレットモード
        test_img = Image.new('P', (100, 100))
    else:
        test_img = Image.new(mode, (100, 100), color='white')
    
    print(f"    作成時のモード: {test_img.mode}")
    
    # RGB変換
    if test_img.mode == 'RGBA':
        rgb_img = Image.new('RGB', test_img.size, (255, 255, 255))
        rgb_img.paste(test_img, mask=test_img.split()[3])
        test_img = rgb_img
    elif test_img.mode != 'RGB':
        test_img = test_img.convert('RGB')
    
    print(f"    変換後のモード: {test_img.mode}")
    
    # JPEG保存
    test_path = os.path.join(output_folder, f"test_{mode}.jpg")
    try:
        test_img.save(test_path, 'JPEG', quality=95)
        print(f"    ✅ 保存成功")
    except Exception as e:
        print(f"    ❌ 保存失敗: {e}")

print("\n" + "=" * 60)
print("✅ すべてのテスト完了")
print("=" * 60)

# 生成されたファイル一覧
print(f"\n生成されたファイル:")
files = sorted(os.listdir(output_folder))
for f in files:
    file_path = os.path.join(output_folder, f)
    file_size = os.path.getsize(file_path)
    print(f"  - {f} ({file_size:,} bytes)")
