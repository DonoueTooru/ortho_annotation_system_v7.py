#!/usr/bin/env python3
"""
Test script for unsaved annotation changes detection feature.

このスクリプトは、アノテーション編集ダイアログで未保存の変更を検出する
機能をテストするための手順を提供します。
"""

import os
import sys

def verify_implementation():
    """実装の変更内容を確認"""
    print("=" * 80)
    print("未保存アノテーション検出機能 - 実装検証")
    print("=" * 80)
    
    code_file = "ortho_annotation_system_v7.py"
    
    if not os.path.exists(code_file):
        print(f"❌ ERROR: {code_file} が見つかりません！")
        return False
    
    with open(code_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 実装のキーとなる要素をチェック
    checks = [
        ("has_unsaved_changes() メソッド", "def has_unsaved_changes(self):"),
        ("未保存変更チェックロジック", "if len(self.working_points) != len(self.original_points):"),
        ("check_unsaved_and_close() 関数", "def check_unsaved_and_close():"),
        ("サーモ画像の変更チェック", "thermal_has_changes = thermal_preview.has_unsaved_changes()"),
        ("可視画像の変更チェック", "visible_has_changes = visible_preview.has_unsaved_changes()"),
        ("確認ダイアログ表示", "result = messagebox.askyesnocancel("),
        ("プロトコル設定", "dialog.protocol(\"WM_DELETE_WINDOW\", check_unsaved_and_close)"),
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

def print_test_instructions():
    """手動テストの手順を表示"""
    print("\n" + "=" * 80)
    print("手動テスト手順")
    print("=" * 80)
    
    print("\n【テストケース1: サーモ画像タブで未保存変更がある場合】")
    print("-" * 80)
    print("1. アプリケーションを起動")
    print("2. 任意の画像を読み込み、アノテーションを追加")
    print("3. アノテーションをダブルクリックして編集ダイアログを開く")
    print("4. 「サーモ画像」タブを選択")
    print("5. サーモ画像を選択（または既に選択されている場合はそのまま）")
    print("6. キャンバス上でクリックしてアノテーションを追加")
    print("7. 「決定」ボタンを押さずに、ダイアログの×ボタンまたは「キャンセル」ボタンをクリック")
    print("\n【期待される動作】")
    print("✓ 「サーモ画像のタブに未保存のアノテーションがあります。保存しますか？」")
    print("  というメッセージが表示される")
    print("✓ 「はい」「いいえ」「キャンセル」の3つの選択肢が表示される")
    print("✓ 「はい」を選択すると、アノテーションが保存されてダイアログが閉じる")
    print("✓ 「いいえ」を選択すると、アノテーションは保存されずダイアログが閉じる")
    print("✓ 「キャンセル」を選択すると、ダイアログは開いたまま")
    
    print("\n【テストケース2: 可視画像タブで未保存変更がある場合】")
    print("-" * 80)
    print("1-5. テストケース1と同様")
    print("6. 「可視画像」タブを選択")
    print("7. 可視画像を選択（または既に選択されている場合はそのまま）")
    print("8. キャンバス上でクリックしてアノテーションを追加")
    print("9. 「決定」ボタンを押さずに、ダイアログの×ボタンまたは「キャンセル」ボタンをクリック")
    print("\n【期待される動作】")
    print("✓ 「可視画像のタブに未保存のアノテーションがあります。保存しますか？」")
    print("  というメッセージが表示される")
    print("✓ 動作はテストケース1と同様")
    
    print("\n【テストケース3: 両方のタブで未保存変更がある場合】")
    print("-" * 80)
    print("1. サーモ画像タブでアノテーションを追加（決定を押さない）")
    print("2. 可視画像タブに切り替え")
    print("3. 可視画像タブでもアノテーションを追加（決定を押さない）")
    print("4. ダイアログの×ボタンまたは「キャンセル」ボタンをクリック")
    print("\n【期待される動作】")
    print("✓ 「サーモ画像 と 可視画像のタブに未保存のアノテーションがあります。保存しますか？」")
    print("  というメッセージが表示される")
    print("✓ 「はい」を選択すると、両方のタブのアノテーションが保存される")
    
    print("\n【テストケース4: 未保存変更がない場合】")
    print("-" * 80)
    print("1. 編集ダイアログを開く")
    print("2. アノテーションを追加せず、または追加後に「決定」ボタンを押す")
    print("3. ダイアログの×ボタンまたは「キャンセル」ボタンをクリック")
    print("\n【期待される動作】")
    print("✓ 確認メッセージは表示されず、ダイアログがすぐに閉じる")
    
    print("\n【テストケース5: アノテーションを追加して削除した場合】")
    print("-" * 80)
    print("1. 編集ダイアログを開く")
    print("2. サーモ画像または可視画像タブでアノテーションを追加")
    print("3. 追加したアノテーションを右クリックで削除（元の状態に戻す）")
    print("4. ダイアログの×ボタンまたは「キャンセル」ボタンをクリック")
    print("\n【期待される動作】")
    print("✓ 確認メッセージは表示されず、ダイアログがすぐに閉じる")
    print("  （元の状態と同じなので変更なしと判定される）")
    
    print("\n【テストケース6: キャンセルボタンで一度キャンセルした後】")
    print("-" * 80)
    print("1. アノテーションを追加")
    print("2. タブ内の「キャンセル」ボタンをクリック（working_pointsがリセットされる）")
    print("3. ダイアログの×ボタンまたは「キャンセル」ボタンをクリック")
    print("\n【期待される動作】")
    print("✓ 確認メッセージは表示されず、ダイアログがすぐに閉じる")
    print("  （キャンセルボタンでリセットされたため）")
    
    print("\n" + "=" * 80)
    print("テスト完了チェックリスト")
    print("=" * 80)
    print("□ テストケース1: サーモ画像タブの未保存変更検出")
    print("□ テストケース2: 可視画像タブの未保存変更検出")
    print("□ テストケース3: 両タブの未保存変更検出")
    print("□ テストケース4: 未保存変更なしの場合")
    print("□ テストケース5: 追加後削除した場合")
    print("□ テストケース6: キャンセルボタン後")
    print("□ 「はい」選択時の自動保存動作")
    print("□ 「いいえ」選択時の破棄動作")
    print("□ 「キャンセル」選択時のダイアログ継続")
    
    print("\n" + "=" * 80)

def print_implementation_summary():
    """実装内容のサマリーを表示"""
    print("\n" + "=" * 80)
    print("実装内容サマリー")
    print("=" * 80)
    
    print("\n【追加されたメソッド】")
    print("-" * 80)
    print("1. ImageAnnotationPreview.has_unsaved_changes()")
    print("   - working_pointsとoriginal_pointsを比較")
    print("   - 変更があればTrueを返す")
    print("   - アノテーションの数や座標(x, y)が異なる場合に検出")
    
    print("\n【追加された関数】")
    print("-" * 80)
    print("2. check_unsaved_and_close()")
    print("   - サーモ画像と可視画像の両タブで未保存変更をチェック")
    print("   - 未保存変更があれば確認ダイアログを表示")
    print("   - ユーザーの選択に応じて保存/破棄/継続を実行")
    
    print("\n【変更された処理】")
    print("-" * 80)
    print("3. cancel_changes()")
    print("   - 直接dialog.destroy()せず、check_unsaved_and_close()を呼び出し")
    print("\n4. dialog.protocol('WM_DELETE_WINDOW', ...)")
    print("   - cancel_changes → check_unsaved_and_close に変更")
    print("   - ×ボタンクリック時も未保存変更チェックが実行される")
    
    print("\n【確認ダイアログの詳細】")
    print("-" * 80)
    print("・タイプ: messagebox.askyesnocancel")
    print("・タイトル: 未保存の変更")
    print("・メッセージ: [画像タイプ]のタブに未保存のアノテーションがあります。")
    print("            保存しますか？")
    print("・ボタン:")
    print("  - はい (Yes): 未保存のタブのconfirm()を実行して保存")
    print("  - いいえ (No): 保存せずにダイアログを閉じる")
    print("  - キャンセル (Cancel): ダイアログを開いたまま")
    
    print("\n【変更検出のロジック】")
    print("-" * 80)
    print("・画像が選択されていない場合: 変更なしと判定")
    print("・アノテーション数が異なる: 変更ありと判定")
    print("・アノテーション数が同じ:")
    print("  - 各アノテーションのx, y座標を比較")
    print("  - 一つでも異なれば変更ありと判定")
    print("・順序も考慮（zip()を使用）")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    # 実装検証
    implementation_ok = verify_implementation()
    
    if not implementation_ok:
        print("\n⚠️  警告: 実装検証に失敗しました！")
        print("一部の機能が正しく実装されていない可能性があります。\n")
    
    # 実装内容のサマリー表示
    print_implementation_summary()
    
    # テスト手順の表示
    print_test_instructions()
    
    print("\n" + "=" * 80)
    print("スクリプト実行完了")
    print("=" * 80)
    print("\n上記の手順に従って手動テストを実施してください。")
    print("すべてのテストケースをクリアすれば、実装は正常に動作しています。\n")
