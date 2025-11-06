#!/usr/bin/env python3
"""
個別全体図生成機能のテストスクリプト
"""
import os
import sys
from PIL import Image, ImageDraw

# テスト用のプロジェクトを作成
test_project_path = "/home/user/webapp/test_project"
os.makedirs(test_project_path, exist_ok=True)
os.makedirs(os.path.join(test_project_path, "全体図位置フォルダ"), exist_ok=True)

# テスト用のダミー画像を作成
test_image = Image.new('RGB', (800, 600), color='white')
draw = ImageDraw.Draw(test_image)
draw.text((400, 300), "Test Image", fill='black')

# テスト用のアノテーションデータ
test_annotations = [
    {
        'id': 1,
        'x': 100,
        'y': 100,
        'defect_type': 'ホットスポット',
        'shape': 'cross'
    },
    {
        'id': 2,
        'x': 300,
        'y': 200,
        'defect_type': 'クラスタ異常',
        'shape': 'circle'
    },
    {
        'id': 3,
        'x': 500,
        'y': 400,
        'defect_type': '破損',
        'shape': 'rectangle'
    }
]

# 各IDごとに個別の全体図を生成（簡易版）
for annotation in test_annotations:
    # 画像をコピー
    annotated_image = test_image.copy()
    draw = ImageDraw.Draw(annotated_image)
    
    # アノテーションを描画
    x = annotation['x']
    y = annotation['y']
    defect_type = annotation['defect_type']
    
    # 十字を描画（簡易版）
    size = 20
    draw.line([(x, y - size), (x, y + size)], fill='red', width=3)
    draw.line([(x - size, y), (x + size, y)], fill='red', width=3)
    
    # ID番号を描画
    draw.text((x + 25, y - 25), f"ID{annotation['id']}", fill='red')
    
    # ファイル名を生成
    annotation_id = annotation['id']
    safe_defect_type = defect_type.replace("/", "_").replace("\\", "_").replace(":", "_")
    filename = f"ID{annotation_id:03d}_全体図_{safe_defect_type}.jpg"
    output_path = os.path.join(test_project_path, "全体図位置フォルダ", filename)
    
    # 保存
    annotated_image.save(output_path, 'JPEG', quality=95)
    print(f"✓ 生成しました: {filename}")

# 生成されたファイルを確認
output_folder = os.path.join(test_project_path, "全体図位置フォルダ")
files = os.listdir(output_folder)
print(f"\n生成されたファイル数: {len(files)}")
print("生成されたファイル:")
for f in sorted(files):
    file_path = os.path.join(output_folder, f)
    file_size = os.path.getsize(file_path)
    print(f"  - {f} ({file_size:,} bytes)")

print("\n✅ テスト完了！")
print(f"生成された画像は以下のフォルダにあります:")
print(f"  {output_folder}")
