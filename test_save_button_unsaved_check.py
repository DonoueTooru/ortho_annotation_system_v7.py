#!/usr/bin/env python3
"""
Test script for save button unsaved annotation check feature.

このスクリプトは、アノテーション編集ダイアログの「保存」ボタンを押した際にも
未保存の画像アノテーションをチェックする機能をテストするための手順を提供します。
"""

import os
import sys

def verify_implementation():
    """実装の変更内容を確認"""
    print("=" * 80)
    print("保存ボタン未保存チェック機能 - 実装検証")
    print("=" * 80)
    
    code_file = "ortho_annotation_system_v7.py"
    
    if not os.path.exists(code_file):
        print(f"❌ ERROR: {code_file} が見つかりません！")
        return False
    
    with open(code_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 実装のキーとなる要素をチェック
    checks = [
        ("save_changes() 内の未保存チェック", "thermal_has_changes = thermal_preview.has_unsaved_changes()"),
        ("可視画像の未保存チェック", "visible_has_changes = visible_preview.has_unsaved_changes()"),
        ("確認ダイアログ表示 (save_changes内)", "if thermal_has_changes or visible_has_changes:"),
        ("メッセージ生成", "message = f\"{' と '.join(unsaved_types)}のタブに未保存のアノテーションがあります"),
        ("askyesnocancel呼び出し", "result = messagebox.askyesnocancel("),
        ("キャンセル処理", "if result is None:  # キャンセル"),
        ("保存処理", "elif result:  # はい"),
        ("フォーム項目保存", "for key, entry in entries.items():"),
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

def print_behavior_comparison():
    """動作の比較を表示"""
    print("\n" + "=" * 80)
    print("動作の比較")
    print("=" * 80)
    
    print("\n【変更前の動作】")
    print("-" * 80)
    print("保存ボタンをクリック")
    print("  ↓")
    print("フォーム項目（エリア番号、PCS番号など）を保存")
    print("  ↓")
    print("ダイアログを閉じる")
    print("\n問題点:")
    print("❌ サーモ/可視画像タブで追加したアノテーションが未保存のまま")
    print("❌ ユーザーが保存し忘れる可能性")
    
    print("\n【変更後の動作】")
    print("-" * 80)
    print("保存ボタンをクリック")
    print("  ↓")
    print("サーモ/可視画像タブの未保存アノテーションをチェック")
    print("  ↓")
    print("未保存アノテーションがある場合:")
    print("  ├─ 確認ダイアログを表示")
    print("  │   「サーモ画像のタブに未保存のアノテーションがあります。")
    print("  │    保存しますか？」")
    print("  │")
    print("  ├─ [はい] を選択:")
    print("  │   ├─ 未保存の画像アノテーションを自動保存")
    print("  │   ├─ フォーム項目を保存")
    print("  │   └─ ダイアログを閉じる")
    print("  │")
    print("  ├─ [いいえ] を選択:")
    print("  │   ├─ 画像アノテーションは保存しない")
    print("  │   ├─ フォーム項目のみ保存")
    print("  │   └─ ダイアログを閉じる")
    print("  │")
    print("  └─ [キャンセル] を選択:")
    print("      ├─ 何も保存しない")
    print("      └─ ダイアログを開いたまま")
    print("\n改善点:")
    print("✅ 未保存アノテーションの保存忘れを防止")
    print("✅ ユーザーに明確な選択肢を提供")
    print("✅ データ損失のリスク低減")
    
    print("\n" + "=" * 80)

def print_test_instructions():
    """手動テストの手順を表示"""
    print("\n" + "=" * 80)
    print("手動テスト手順")
    print("=" * 80)
    
    print("\n【前提条件】")
    print("-" * 80)
    print("1. ortho_annotation_system_v7.py アプリケーションを起動")
    print("2. プロジェクトを作成または既存のプロジェクトを開く")
    print("3. オルソ画像を読み込む")
    print("4. キャンバス上でアノテーションを追加")
    
    print("\n【テストケース1: サーモ画像タブに未保存アノテーションがある】")
    print("-" * 80)
    print("1. アノテーションをダブルクリックして編集ダイアログを開く")
    print("2. 「サーモ画像」タブを選択")
    print("3. サーモ画像を選択")
    print("4. キャンバス上でクリックしてアノテーションを追加")
    print("5. タブ内の「決定」ボタンを押さずに、")
    print("   フォーム下部の「保存」ボタンをクリック")
    print("\n【期待される結果】")
    print("✓ 確認ダイアログが表示される:")
    print("  「サーモ画像のタブに未保存のアノテーションがあります。")
    print("   保存しますか？」")
    print("✓ [はい] を選択:")
    print("  - サーモ画像のアノテーションが自動保存される")
    print("  - フォーム項目が保存される")
    print("  - ダイアログが閉じる")
    print("✓ [いいえ] を選択:")
    print("  - サーモ画像のアノテーションは保存されない")
    print("  - フォーム項目のみ保存される")
    print("  - ダイアログが閉じる")
    print("✓ [キャンセル] を選択:")
    print("  - 何も保存されない")
    print("  - ダイアログは開いたまま")
    
    print("\n【テストケース2: 可視画像タブに未保存アノテーションがある】")
    print("-" * 80)
    print("1. アノテーション編集ダイアログを開く")
    print("2. 「可視画像」タブを選択")
    print("3. 可視画像を選択")
    print("4. キャンバス上でクリックしてアノテーションを追加")
    print("5. タブ内の「決定」ボタンを押さずに、")
    print("   フォーム下部の「保存」ボタンをクリック")
    print("\n【期待される結果】")
    print("✓ 「可視画像のタブに未保存のアノテーションがあります。")
    print("  保存しますか？」というメッセージが表示される")
    print("✓ 動作はテストケース1と同様")
    
    print("\n【テストケース3: 両タブに未保存アノテーションがある】")
    print("-" * 80)
    print("1. サーモ画像タブでアノテーションを追加（決定を押さない）")
    print("2. 可視画像タブでアノテーションを追加（決定を押さない）")
    print("3. フォーム下部の「保存」ボタンをクリック")
    print("\n【期待される結果】")
    print("✓ 「サーモ画像 と 可視画像のタブに未保存のアノテーションがあります。")
    print("  保存しますか？」というメッセージが表示される")
    print("✓ [はい] を選択すると両方のタブのアノテーションが保存される")
    
    print("\n【テストケース4: 未保存アノテーションがない場合】")
    print("-" * 80)
    print("1. アノテーション編集ダイアログを開く")
    print("2. フォーム項目（エリア番号など）のみを変更")
    print("3. 画像タブではアノテーションを追加しない")
    print("4. フォーム下部の「保存」ボタンをクリック")
    print("\n【期待される結果】")
    print("✓ 確認ダイアログは表示されない")
    print("✓ フォーム項目のみが保存される")
    print("✓ ダイアログがすぐに閉じる")
    
    print("\n【テストケース5: アノテーションを追加後、タブ内で「決定」を押した場合】")
    print("-" * 80)
    print("1. サーモ画像タブでアノテーションを追加")
    print("2. タブ内の「決定」ボタンをクリック（保存完了）")
    print("3. フォーム下部の「保存」ボタンをクリック")
    print("\n【期待される結果】")
    print("✓ 確認ダイアログは表示されない")
    print("  （既に画像アノテーションは保存済みのため）")
    print("✓ フォーム項目が保存される")
    print("✓ ダイアログが閉じる")
    
    print("\n【テストケース6: フォーム項目変更 + 未保存画像アノテーション】")
    print("-" * 80)
    print("1. アノテーション編集ダイアログを開く")
    print("2. エリア番号やPCS番号などのフォーム項目を変更")
    print("3. サーモ画像タブでアノテーションを追加（決定を押さない）")
    print("4. フォーム下部の「保存」ボタンをクリック")
    print("5. 確認ダイアログで「はい」を選択")
    print("\n【期待される結果】")
    print("✓ 確認ダイアログが表示される")
    print("✓ [はい] を選択すると:")
    print("  - サーモ画像のアノテーションが保存される")
    print("  - フォーム項目も保存される")
    print("  - 両方が正しく保存される")
    
    print("\n" + "=" * 80)
    print("テスト完了チェックリスト")
    print("=" * 80)
    print("□ テストケース1: サーモ画像タブの未保存チェック")
    print("□ テストケース2: 可視画像タブの未保存チェック")
    print("□ テストケース3: 両タブの未保存チェック")
    print("□ テストケース4: 未保存なしの場合")
    print("□ テストケース5: 既に保存済みの場合")
    print("□ テストケース6: フォーム項目と画像アノテーション両方")
    print("□ [はい] 選択時の動作確認")
    print("□ [いいえ] 選択時の動作確認")
    print("□ [キャンセル] 選択時の動作確認")
    print("□ フォーム項目が正しく保存される")
    print("□ 画像アノテーションが正しく保存される")
    
    print("\n" + "=" * 80)

def print_implementation_summary():
    """実装内容のサマリーを表示"""
    print("\n" + "=" * 80)
    print("実装内容サマリー")
    print("=" * 80)
    
    print("\n【変更箇所】")
    print("-" * 80)
    print("ファイル: ortho_annotation_system_v7.py")
    print("関数: save_changes()")
    print("行数: 約3576-3585行目")
    
    print("\n【変更内容】")
    print("-" * 80)
    print("1. 未保存チェックの追加")
    print("   - thermal_preview.has_unsaved_changes() を呼び出し")
    print("   - visible_preview.has_unsaved_changes() を呼び出し")
    
    print("\n2. 確認ダイアログの表示")
    print("   - 未保存アノテーションがある場合のみ表示")
    print("   - messagebox.askyesnocancel を使用")
    print("   - メッセージに未保存のタブ名を表示")
    
    print("\n3. ユーザー選択の処理")
    print("   - [はい]: 未保存アノテーションを自動保存 → フォーム保存 → 閉じる")
    print("   - [いいえ]: フォーム保存のみ → 閉じる")
    print("   - [キャンセル]: 何もせず return（ダイアログ継続）")
    
    print("\n4. フォーム項目の保存")
    print("   - 従来通りフォーム項目を保存")
    print("   - update_table() と draw_annotations() を実行")
    print("   - dialog.destroy() でダイアログを閉じる")
    
    print("\n【既存機能との統合】")
    print("-" * 80)
    print("✓ check_unsaved_and_close() 関数との統合")
    print("  - ×ボタン、キャンセルボタン: check_unsaved_and_close()")
    print("  - 保存ボタン: save_changes() 内で未保存チェック")
    print("✓ 同じ確認ダイアログロジックを使用")
    print("✓ 一貫したユーザー体験")
    
    print("\n【メリット】")
    print("-" * 80)
    print("✓ 保存ボタンでも未保存チェックが実行される")
    print("✓ すべての終了パターンで保護される:")
    print("  - ×ボタン → チェックあり")
    print("  - キャンセルボタン → チェックあり")
    print("  - 保存ボタン → チェックあり（新規追加）")
    print("✓ データ損失のリスクを最小化")
    print("✓ ユーザーの意図を明確に確認")
    
    print("\n" + "=" * 80)

def print_code_example():
    """実装コードの例を表示"""
    print("\n" + "=" * 80)
    print("実装コード例")
    print("=" * 80)
    
    print("""
変更前のコード:
----------------
def save_changes():
    for key, entry in entries.items():
        annotation[key] = entry.get()
    annotation["defect_type"] = defect_combo.get() or annotation.get("defect_type", "")
    annotation["shape"] = self.annotation_shapes.get(shape_combo.get(), annotation.get("shape", "cross"))
    annotation["management_level"] = (mgmt_var.get() or 'S')

    self.update_table()
    self.draw_annotations()
    dialog.destroy()


変更後のコード:
----------------
def save_changes():
    \"\"\"フォーム項目を保存し、未保存の画像アノテーションがあれば確認する\"\"\"
    # サーモ画像と可視画像の未保存変更をチェック
    thermal_has_changes = thermal_preview.has_unsaved_changes()
    visible_has_changes = visible_preview.has_unsaved_changes()
    
    # 未保存の画像アノテーションがある場合、確認ダイアログを表示
    if thermal_has_changes or visible_has_changes:
        unsaved_types = []
        if thermal_has_changes:
            unsaved_types.append("サーモ画像")
        if visible_has_changes:
            unsaved_types.append("可視画像")
        
        message = f"{{' と '.join(unsaved_types)}}のタブに未保存のアノテーションがあります。\\n\\n保存しますか？"
        
        result = messagebox.askyesnocancel(
            "未保存の変更",
            message,
            parent=dialog
        )
        
        if result is None:  # キャンセル - ダイアログを閉じない
            return
        elif result:  # はい - 未保存の画像アノテーションを保存
            if thermal_has_changes:
                thermal_preview.confirm()
            if visible_has_changes:
                visible_preview.confirm()
        # いいえの場合は保存せずに続行
    
    # フォーム項目を保存
    for key, entry in entries.items():
        annotation[key] = entry.get()
    annotation["defect_type"] = defect_combo.get() or annotation.get("defect_type", "")
    annotation["shape"] = self.annotation_shapes.get(shape_combo.get(), annotation.get("shape", "cross"))
    annotation["management_level"] = (mgmt_var.get() or 'S')

    self.update_table()
    self.draw_annotations()
    dialog.destroy()
""")
    
    print("\n主な変更点:")
    print("1. 関数の先頭で未保存チェックを追加")
    print("2. 確認ダイアログを表示（未保存がある場合のみ）")
    print("3. ユーザーの選択に応じて処理")
    print("4. 従来のフォーム保存処理を実行")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    # 実装検証
    implementation_ok = verify_implementation()
    
    if not implementation_ok:
        print("\n⚠️  警告: 実装検証に失敗しました！")
        print("一部の機能が正しく実装されていない可能性があります。\n")
    
    # 動作の比較表示
    print_behavior_comparison()
    
    # 実装内容のサマリー表示
    print_implementation_summary()
    
    # コード例の表示
    print_code_example()
    
    # テスト手順の表示
    print_test_instructions()
    
    print("\n" + "=" * 80)
    print("スクリプト実行完了")
    print("=" * 80)
    print("\n上記の手順に従って手動テストを実施してください。")
    print("すべてのテストケースをクリアすれば、実装は正常に動作しています。\n")
