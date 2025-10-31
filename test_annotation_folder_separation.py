#!/usr/bin/env python3
"""
Test script for annotation folder separation feature.

このスクリプトは、アノテーション入り画像をサーモ画像フォルダと可視画像フォルダに
振り分けて保存する機能をテストするための手順を提供します。
"""

import os
import sys

def verify_implementation():
    """実装の変更内容を確認"""
    print("=" * 80)
    print("アノテーション画像フォルダ振り分け機能 - 実装検証")
    print("=" * 80)
    
    code_file = "ortho_annotation_system_v7.py"
    
    if not os.path.exists(code_file):
        print(f"❌ ERROR: {code_file} が見つかりません！")
        return False
    
    with open(code_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 実装のキーとなる要素をチェック
    checks = [
        ("サーモ画像フォルダ作成", 'type_dir = os.path.join(base_dir, "サーモ画像フォルダ")'),
        ("可視画像フォルダ作成", 'type_dir = os.path.join(base_dir, "可視画像フォルダ")'),
        ("画像タイプ判定 (thermal)", 'if self.image_type == "thermal":'),
        ("画像タイプ判定 (visible)", 'elif self.image_type == "visible":'),
        ("フォルダ作成処理", "os.makedirs(type_dir, exist_ok=True)"),
        ("保存パス生成", "output_path = os.path.join(type_dir,"),
    ]
    
    all_passed = True
    for check_name, check_string in checks:
        if check_string in content:
            print(f"✓ 確認: {check_name}")
        else:
            print(f"❌ 未実装: {check_name}")
            all_passed = False
    
    print("=" * 80)
    if all_passed:
        print("✓ すべての実装要素が確認されました！")
    else:
        print("❌ 一部の実装要素が見つかりません")
    
    return all_passed

def print_folder_structure():
    """期待されるフォルダ構造を表示"""
    print("\n" + "=" * 80)
    print("期待されるフォルダ構造")
    print("=" * 80)
    
    print("""
プロジェクトフォルダ/
│
├── アノテーション入り画像フォルダ/
│   │
│   ├── サーモ画像フォルダ/
│   │   ├── ID001_image1_thermal_annotated.jpg
│   │   ├── ID001_image2_thermal_annotated.jpg
│   │   ├── ID002_image3_thermal_annotated.jpg
│   │   └── ...
│   │
│   └── 可視画像フォルダ/
│       ├── ID001_image1_visible_annotated.jpg
│       ├── ID001_image2_visible_annotated.jpg
│       ├── ID002_image3_visible_annotated.jpg
│       └── ...
│
├── 全体図位置フォルダ/
├── 不具合一覧表フォルダ/
└── ...
""")
    
    print("=" * 80)

def print_test_instructions():
    """手動テストの手順を表示"""
    print("\n" + "=" * 80)
    print("手動テスト手順")
    print("=" * 80)
    
    print("\n【前提条件】")
    print("-" * 80)
    print("1. ortho_annotation_system_v7.py アプリケーションを起動")
    print("2. プロジェクトを作成または既存のプロジェクトを開く")
    print("3. オルソ画像（全体図）を読み込む")
    print("4. キャンバス上でアノテーションを追加")
    
    print("\n【テストケース1: サーモ画像のアノテーション保存】")
    print("-" * 80)
    print("1. 追加したアノテーションをダブルクリックして編集ダイアログを開く")
    print("2. 「サーモ画像」タブを選択")
    print("3. 「サーモ画像選択」ボタンをクリックしてサーモ画像を選択")
    print("4. キャンバス上でクリックしてアノテーションを1つ以上追加")
    print("5. 「決定」ボタンをクリック")
    print("\n【期待される結果】")
    print("✓ 「アノテーション入り画像を保存しました」というメッセージが表示される")
    print("✓ プロジェクトフォルダ内に以下のパスで画像が保存される:")
    print("  アノテーション入り画像フォルダ/サーモ画像フォルダ/ID[番号]_[ファイル名]_thermal_annotated.[拡張子]")
    
    print("\n【テストケース2: 可視画像のアノテーション保存】")
    print("-" * 80)
    print("1. 同じアノテーションの編集ダイアログで「可視画像」タブを選択")
    print("2. 「可視画像選択」ボタンをクリックして可視画像を選択")
    print("3. キャンバス上でクリックしてアノテーションを1つ以上追加")
    print("4. 「決定」ボタンをクリック")
    print("\n【期待される結果】")
    print("✓ 「アノテーション入り画像を保存しました」というメッセージが表示される")
    print("✓ プロジェクトフォルダ内に以下のパスで画像が保存される:")
    print("  アノテーション入り画像フォルダ/可視画像フォルダ/ID[番号]_[ファイル名]_visible_annotated.[拡張子]")
    
    print("\n【テストケース3: 両タイプの画像を保存】")
    print("-" * 80)
    print("1. テストケース1とテストケース2を順番に実行")
    print("2. アノテーション編集ダイアログを閉じる")
    print("3. プロジェクトフォルダを開く")
    print("\n【期待される結果】")
    print("✓ アノテーション入り画像フォルダ内に2つのサブフォルダが作成される:")
    print("  - サーモ画像フォルダ")
    print("  - 可視画像フォルダ")
    print("✓ サーモ画像フォルダにサーモ画像のアノテーション入り画像が保存されている")
    print("✓ 可視画像フォルダに可視画像のアノテーション入り画像が保存されている")
    print("✓ 各画像ファイルのファイル名が正しい形式になっている:")
    print("  ID[番号]_[元ファイル名]_thermal_annotated.[拡張子]")
    print("  ID[番号]_[元ファイル名]_visible_annotated.[拡張子]")
    
    print("\n【テストケース4: 複数のアノテーションで保存】")
    print("-" * 80)
    print("1. 複数のアノテーション（例：ID001, ID002, ID003）を作成")
    print("2. 各アノテーションでサーモ画像と可視画像のアノテーション入り画像を保存")
    print("3. フォルダ構造を確認")
    print("\n【期待される結果】")
    print("✓ サーモ画像フォルダに複数のサーモ画像ファイルが保存される")
    print("  - ID001_..._thermal_annotated.jpg")
    print("  - ID002_..._thermal_annotated.jpg")
    print("  - ID003_..._thermal_annotated.jpg")
    print("✓ 可視画像フォルダに複数の可視画像ファイルが保存される")
    print("  - ID001_..._visible_annotated.jpg")
    print("  - ID002_..._visible_annotated.jpg")
    print("  - ID003_..._visible_annotated.jpg")
    
    print("\n【テストケース5: フォルダの自動作成確認】")
    print("-" * 80)
    print("1. 既存のプロジェクトの「アノテーション入り画像フォルダ」を削除")
    print("   （または新しいプロジェクトを作成）")
    print("2. サーモ画像のアノテーション入り画像を保存")
    print("3. フォルダ構造を確認")
    print("\n【期待される結果】")
    print("✓ アノテーション入り画像フォルダが自動的に作成される")
    print("✓ サーモ画像フォルダが自動的に作成される")
    print("✓ 画像が正しく保存される")
    
    print("\n【テストケース6: 既存の画像の上書き】")
    print("-" * 80)
    print("1. 既にサーモ画像のアノテーション入り画像を保存済みのアノテーションを開く")
    print("2. サーモ画像タブでアノテーションを追加または削除")
    print("3. 「決定」ボタンをクリック")
    print("4. 同じファイルを確認")
    print("\n【期待される結果】")
    print("✓ 既存のファイルが新しい内容で上書きされる")
    print("✓ ファイルパスは変わらない")
    print("✓ アノテーションの変更が反映されている")
    
    print("\n" + "=" * 80)
    print("テスト完了チェックリスト")
    print("=" * 80)
    print("□ テストケース1: サーモ画像の保存とフォルダ振り分け")
    print("□ テストケース2: 可視画像の保存とフォルダ振り分け")
    print("□ テストケース3: 両タイプの画像の同時保存")
    print("□ テストケース4: 複数アノテーションでの保存")
    print("□ テストケース5: フォルダの自動作成")
    print("□ テストケース6: 既存画像の上書き")
    print("□ ファイル名形式の確認")
    print("□ フォルダ構造の確認")
    print("□ メッセージ表示の確認")
    
    print("\n" + "=" * 80)

def print_implementation_summary():
    """実装内容のサマリーを表示"""
    print("\n" + "=" * 80)
    print("実装内容サマリー")
    print("=" * 80)
    
    print("\n【変更箇所】")
    print("-" * 80)
    print("ファイル: ortho_annotation_system_v7.py")
    print("メソッド: ImageAnnotationPreview.confirm()")
    print("行数: 約3371-3380行目")
    
    print("\n【変更内容】")
    print("-" * 80)
    print("1. 画像タイプ判定の追加")
    print("   - self.image_type が 'thermal' の場合 → サーモ画像フォルダ")
    print("   - self.image_type が 'visible' の場合 → 可視画像フォルダ")
    print("   - その他の場合 → アノテーション入り画像フォルダ直下")
    
    print("\n2. サブフォルダパスの生成")
    print("   - base_dir: アノテーション入り画像フォルダ")
    print("   - type_dir: base_dir + サーモ画像フォルダ or 可視画像フォルダ")
    
    print("\n3. フォルダの自動作成")
    print("   - os.makedirs(type_dir, exist_ok=True)")
    print("   - exist_ok=True により既存フォルダがあってもエラーにならない")
    
    print("\n4. 保存パスの変更")
    print("   - 変更前: os.path.join(base_dir, filename)")
    print("   - 変更後: os.path.join(type_dir, filename)")
    
    print("\n【フォルダ構造】")
    print("-" * 80)
    print("アノテーション入り画像フォルダ/")
    print("├── サーモ画像フォルダ/     ← 新規作成")
    print("│   └── ID001_xxx_thermal_annotated.jpg")
    print("└── 可視画像フォルダ/       ← 新規作成")
    print("    └── ID001_xxx_visible_annotated.jpg")
    
    print("\n【ファイル名形式】")
    print("-" * 80)
    print("形式: ID{id番号}_{元ファイル名}_{画像タイプ}_annotated{拡張子}")
    print("\n例:")
    print("  ID001_IR_image_001_thermal_annotated.jpg")
    print("  ID001_RGB_image_001_visible_annotated.jpg")
    print("  ID002_thermal_data_thermal_annotated.png")
    print("  ID002_visible_data_visible_annotated.png")
    
    print("\n【後方互換性】")
    print("-" * 80)
    print("✓ 既存のプロジェクトでも動作します")
    print("✓ 既存のアノテーション入り画像には影響しません")
    print("✓ 新しく保存する画像から新フォルダ構造が適用されます")
    
    print("\n【メリット】")
    print("-" * 80)
    print("✓ サーモ画像と可視画像が整理される")
    print("✓ 目的の画像を見つけやすくなる")
    print("✓ フォルダ内のファイル数が減少（各サブフォルダに分散）")
    print("✓ バックアップやコピー時に画像タイプを選択しやすい")
    
    print("\n" + "=" * 80)

def print_code_example():
    """実装コードの例を表示"""
    print("\n" + "=" * 80)
    print("実装コード例")
    print("=" * 80)
    
    print("""
変更前のコード:
----------------
if getattr(self.outer, "project_path", None):
    base_dir = os.path.join(self.outer.project_path, "アノテーション入り画像フォルダ")
else:
    base_dir = os.path.join(os.path.dirname(self.image_path), "annotated")
os.makedirs(base_dir, exist_ok=True)

name, ext = os.path.splitext(os.path.basename(self.image_path))
if not ext:
    ext = ".png"
output_path = os.path.join(base_dir, f"ID{self.annotation['id']}_{name}_{self.image_type}_annotated{ext}")


変更後のコード:
----------------
if getattr(self.outer, "project_path", None):
    base_dir = os.path.join(self.outer.project_path, "アノテーション入り画像フォルダ")
else:
    base_dir = os.path.join(os.path.dirname(self.image_path), "annotated")

# 画像タイプに応じてサブフォルダを作成
if self.image_type == "thermal":
    type_dir = os.path.join(base_dir, "サーモ画像フォルダ")
elif self.image_type == "visible":
    type_dir = os.path.join(base_dir, "可視画像フォルダ")
else:
    type_dir = base_dir

os.makedirs(type_dir, exist_ok=True)

name, ext = os.path.splitext(os.path.basename(self.image_path))
if not ext:
    ext = ".png"
output_path = os.path.join(type_dir, f"ID{self.annotation['id']}_{name}_{self.image_type}_annotated{ext}")
""")
    
    print("\n主な変更点:")
    print("1. 画像タイプ判定の追加（thermal/visible）")
    print("2. type_dir 変数の導入")
    print("3. サブフォルダパスの生成")
    print("4. os.makedirs() の対象を type_dir に変更")
    print("5. output_path の生成を type_dir ベースに変更")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    # 実装検証
    implementation_ok = verify_implementation()
    
    if not implementation_ok:
        print("\n⚠️  警告: 実装検証に失敗しました！")
        print("一部の機能が正しく実装されていない可能性があります。\n")
    
    # 実装内容のサマリー表示
    print_implementation_summary()
    
    # コード例の表示
    print_code_example()
    
    # 期待されるフォルダ構造の表示
    print_folder_structure()
    
    # テスト手順の表示
    print_test_instructions()
    
    print("\n" + "=" * 80)
    print("スクリプト実行完了")
    print("=" * 80)
    print("\n上記の手順に従って手動テストを実施してください。")
    print("すべてのテストケースをクリアすれば、実装は正常に動作しています。\n")
