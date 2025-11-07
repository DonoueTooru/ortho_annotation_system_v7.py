# Requirement 5: 差分保存機能の実装 - 提案書

## 📋 概要

**目的**: プロジェクト保存時に変更された画像のみを再生成し、処理時間を短縮する

**現状の問題**: 毎回すべての画像を再生成するため、アノテーション数が多いと保存に時間がかかる

**目標**: 変更があったアノテーションの画像のみを再生成し、変更がない場合は一覧表の更新のみ実施

---

## 🔍 現状分析

### 現在の保存処理フロー

**`save_project()` メソッド** (Line 4620-4666):

```python
def save_project(self):
    # 1. annotations.json 保存
    # 2. CSV出力 (export_to_csv)
    # 3. Excel出力 (export_to_excel)
    # 4. 関連画像をコピー (copy_related_images) ← 全アノテーション処理
    # 5. アノテーション入り全体図を保存 (save_annotated_image) ← 毎回再生成
    # 6. 個別全体図を保存 (save_individual_annotated_images) ← 全アノテーション処理
    # 7. v2 CSV/XLSX出力
```

### 処理時間の内訳（推定）

- **annotations.json 保存**: 高速（数ms）
- **CSV/Excel出力**: 高速（数百ms）
- **copy_related_images()**: **遅い**（各アノテーションで画像読み込み・描画・保存）
- **save_annotated_image()**: **遅い**（全体図の画像処理）
- **save_individual_annotated_images()**: **非常に遅い**（各IDで全体図処理）

### 問題点

1. **全画像を毎回再生成**: テキスト情報のみ変更しても画像を再生成
2. **変更検出なし**: どのアノテーションが変更されたか追跡していない
3. **無駄な処理**: 変更のないアノテーションも処理対象

---

## 💡 提案する解決策

### 基本方針

1. **変更検出メカニズムの導入**:
   - アノテーションの変更状態を追跡
   - 前回保存時の状態と比較

2. **差分保存の実装**:
   - 変更されたアノテーションのみ画像を再生成
   - 変更がない場合は画像生成をスキップ

3. **一覧表は常に更新**:
   - CSV/Excel出力は常に実行（高速なため）

### 変更検出の対象

#### アノテーション単位での変更検出

各アノテーションについて以下の変更を検出：

1. **座標変更**: `x`, `y`, `thermal_overlays`, `visible_overlays`
2. **属性変更**: `defect_type`, `shape`, `management_level`
3. **画像パス変更**: `thermal_image`, `visible_image`
4. **削除**: アノテーションの削除

#### 全体図での変更検出

全体図の再生成が必要な条件：

1. **任意のアノテーションに変更があった**
2. **オフセット設定が変更された**
3. **色設定が変更された**

---

## 🏗️ 実装設計

### 1. 変更追跡システム

#### データ構造

```python
class AnnotationSystemV7:
    def __init__(self):
        # 前回保存時のスナップショット
        self.last_saved_annotations = None
        self.last_saved_offsets = None
        self.last_saved_colors = None
        
        # 変更フラグ
        self.has_unsaved_changes = False
        self.changed_annotation_ids = set()  # 変更されたアノテーションID
```

#### 変更検出ロジック

```python
def detect_changes(self):
    """
    変更を検出してchanged_annotation_idsを更新
    
    Returns:
        dict: {
            'changed_ids': set(),        # 変更されたアノテーションID
            'deleted_ids': set(),        # 削除されたアノテーションID
            'added_ids': set(),          # 新規追加されたアノテーションID
            'need_full_redraw': bool,    # 全体図の再描画が必要か
            'need_individual_redraw': set() # 個別全体図の再描画が必要なID
        }
    """
    pass
```

### 2. 差分保存メソッド

#### 修正版 `save_project()`

```python
def save_project(self):
    """プロジェクトを差分保存"""
    if not self.annotations:
        messagebox.showwarning("警告", "保存するアノテーションがありません。")
        return
    
    try:
        # 変更を検出
        changes = self.detect_changes()
        
        # annotations.json 保存（常に実行）
        self.save_annotations_json()
        
        # CSV/Excel出力（常に実行）
        self.export_to_csv()
        self.export_to_excel()
        self.export_v2_csv()
        self.export_v2_xlsx()
        
        # 変更がある場合のみ画像生成
        if changes['changed_ids'] or changes['added_ids']:
            # 変更されたアノテーションのみ処理
            self.copy_related_images_incremental(
                changes['changed_ids'] | changes['added_ids']
            )
        
        # 削除されたアノテーションの画像を削除
        if changes['deleted_ids']:
            self.delete_related_images(changes['deleted_ids'])
        
        # 全体図の再生成（必要な場合のみ）
        if changes['need_full_redraw']:
            self.save_annotated_image()
        
        # 個別全体図の再生成（変更されたIDのみ）
        if changes['need_individual_redraw']:
            self.save_individual_annotated_images_incremental(
                changes['need_individual_redraw']
            )
        
        # スナップショットを更新
        self.update_snapshot()
        
        # 変更フラグをリセット
        self.has_unsaved_changes = False
        self.changed_annotation_ids.clear()
        
        messagebox.showinfo("成功", f"プロジェクト '{self.project_name}' を保存しました。")
        
    except Exception as e:
        messagebox.showerror("エラー", f"保存に失敗しました: {str(e)}")
```

### 3. 変更追跡の統合

#### アノテーション追加時

```python
def on_canvas_click(self, event):
    # アノテーション追加処理...
    self.annotations.append(annotation)
    
    # 変更フラグを設定
    self.has_unsaved_changes = True
    self.changed_annotation_ids.add(annotation['id'])
```

#### アノテーション編集時

```python
def edit_annotation_dialog(self, annotation):
    # 編集前のスナップショットを保存
    original_snapshot = copy.deepcopy(annotation)
    
    def save_changes():
        # 変更があったか確認
        if self._annotation_changed(original_snapshot, annotation):
            self.has_unsaved_changes = True
            self.changed_annotation_ids.add(annotation['id'])
        
        dialog.destroy()
```

#### アノテーション削除時

```python
def delete_annotation(self):
    # 削除処理...
    deleted_id = selected_annotation['id']
    self.annotations.remove(selected_annotation)
    
    # 変更フラグを設定
    self.has_unsaved_changes = True
    self.changed_annotation_ids.add(deleted_id)
```

#### オフセット設定変更時

```python
def apply_settings():
    # オフセット設定を適用
    offset_changed = (
        self.thermal_offset_x != thermal_x_var.get() or
        self.thermal_offset_y != thermal_y_var.get() or
        # ... 他のオフセット
    )
    
    if offset_changed:
        # 全アノテーションを再生成対象にする
        self.changed_annotation_ids = set(a['id'] for a in self.annotations)
        self.has_unsaved_changes = True
```

---

## 📝 実装タスク

### タスク1: 変更検出システムの実装 🔴

**優先度**: 高

#### 1-1. スナップショット機能

**実装内容**:
```python
def create_snapshot(self):
    """現在の状態のスナップショットを作成"""
    return {
        'annotations': copy.deepcopy(self.annotations),
        'offsets': {
            'thermal_x': self.thermal_offset_x,
            'thermal_y': self.thermal_offset_y,
            'visible_x': self.visible_offset_x,
            'visible_y': self.visible_offset_y,
            'ortho_x': self.ortho_offset_x,
            'ortho_y': self.ortho_offset_y,
        },
        'colors': copy.deepcopy(self.defect_types),
    }

def update_snapshot(self):
    """スナップショットを最新状態に更新"""
    self.last_saved_snapshot = self.create_snapshot()
```

#### 1-2. 変更検出ロジック

**実装内容**:
```python
def detect_changes(self):
    """変更されたアノテーションを検出"""
    if not self.last_saved_snapshot:
        # 初回保存時は全て変更扱い
        return {
            'changed_ids': set(a['id'] for a in self.annotations),
            'deleted_ids': set(),
            'added_ids': set(a['id'] for a in self.annotations),
            'need_full_redraw': True,
            'need_individual_redraw': set(a['id'] for a in self.annotations),
        }
    
    current = {a['id']: a for a in self.annotations}
    previous = {a['id']: a for a in self.last_saved_snapshot['annotations']}
    
    current_ids = set(current.keys())
    previous_ids = set(previous.keys())
    
    added_ids = current_ids - previous_ids
    deleted_ids = previous_ids - current_ids
    potential_changed = current_ids & previous_ids
    
    changed_ids = set()
    for aid in potential_changed:
        if self._annotation_changed(previous[aid], current[aid]):
            changed_ids.add(aid)
    
    # オフセット・色の変更チェック
    offset_changed = self._offset_changed()
    color_changed = self._color_changed()
    
    need_full_redraw = bool(changed_ids or added_ids or deleted_ids or 
                            offset_changed or color_changed)
    
    need_individual_redraw = changed_ids | added_ids
    
    return {
        'changed_ids': changed_ids,
        'deleted_ids': deleted_ids,
        'added_ids': added_ids,
        'need_full_redraw': need_full_redraw,
        'need_individual_redraw': need_individual_redraw,
    }

def _annotation_changed(self, old, new):
    """アノテーションが変更されたか判定"""
    # 比較対象のキー
    keys = ['x', 'y', 'defect_type', 'shape', 'management_level',
            'thermal_image', 'visible_image', 'thermal_overlays', 
            'visible_overlays']
    
    for key in keys:
        if old.get(key) != new.get(key):
            return True
    return False
```

### タスク2: 差分保存メソッドの実装 🔴

**優先度**: 高

#### 2-1. `copy_related_images_incremental()`

**実装内容**:
```python
def copy_related_images_incremental(self, target_ids):
    """
    指定されたIDのアノテーションのみ関連画像を生成
    
    Args:
        target_ids: set of int - 処理対象のアノテーションID
    """
    for annotation in self.annotations:
        if annotation['id'] not in target_ids:
            continue
        
        # 既存の copy_related_images() と同じ処理
        # ただし、1つのアノテーションのみ処理
        ...
```

#### 2-2. `delete_related_images()`

**実装内容**:
```python
def delete_related_images(self, deleted_ids):
    """
    削除されたアノテーションの画像ファイルを削除
    
    Args:
        deleted_ids: set of int - 削除されたアノテーションID
    """
    for aid in deleted_ids:
        # サーモ画像の削除
        thermal_pattern = f"ID{aid:03d}_*_サーモ異常.*"
        thermal_folder = os.path.join(self.project_path, "サーモ画像フォルダ")
        for file in glob.glob(os.path.join(thermal_folder, thermal_pattern)):
            os.remove(file)
        
        # 可視画像の削除
        visible_pattern = f"ID{aid:03d}_*_可視異常.*"
        visible_folder = os.path.join(self.project_path, "可視画像フォルダ")
        for file in glob.glob(os.path.join(visible_folder, visible_pattern)):
            os.remove(file)
        
        # 個別全体図の削除
        individual_pattern = f"ID{aid:03d}_*.*"
        individual_folder = os.path.join(self.project_path, "個別全体図フォルダ")
        for file in glob.glob(os.path.join(individual_folder, individual_pattern)):
            os.remove(file)
```

#### 2-3. `save_individual_annotated_images_incremental()`

**実装内容**:
```python
def save_individual_annotated_images_incremental(self, target_ids):
    """
    指定されたIDの個別全体図のみを生成
    
    Args:
        target_ids: set of int - 処理対象のアノテーションID
    """
    for annotation in sorted(self.annotations, key=lambda x: x['id']):
        if annotation['id'] not in target_ids:
            continue
        
        # 既存の save_individual_annotated_images() と同じ処理
        # ただし、1つのアノテーションのみ処理
        ...
```

### タスク3: 変更追跡の統合 🔴

**優先度**: 高

#### 3-1. アノテーション追加時の追跡

**実装箇所**:
- `on_canvas_click()` (Line 3230付近)
- アノテーション追加ダイアログ

**実装内容**:
```python
# アノテーション追加後
self.has_unsaved_changes = True
self.changed_annotation_ids.add(new_annotation['id'])
```

#### 3-2. アノテーション編集時の追跡

**実装箇所**:
- `edit_annotation_dialog()` (Line 3683)

**実装内容**:
```python
def save_changes():
    # 変更チェック
    if self._annotation_changed(original_data, annotation):
        self.has_unsaved_changes = True
        self.changed_annotation_ids.add(annotation['id'])
```

#### 3-3. アノテーション削除時の追跡

**実装箇所**:
- `delete_annotation()` メソッド

**実装内容**:
```python
# 削除後
self.has_unsaved_changes = True
self.changed_annotation_ids.add(deleted_annotation['id'])
```

#### 3-4. アノテーション移動時の追跡

**実装箇所**:
- `on_canvas_click()` (移動モード) (Line 3268付近)
- `on_ctrl_drag()` (Line 3320付近)

**実装内容**:
```python
# 座標変更後
self.has_unsaved_changes = True
self.changed_annotation_ids.add(self.moving_annotation['id'])
```

#### 3-5. オフセット設定変更時の追跡

**実装箇所**:
- `customize_settings()` の `apply_settings()` (Line 4597)

**実装内容**:
```python
def apply_settings():
    # オフセット変更チェック
    if self._offset_changed_from_saved():
        # 全アノテーションを変更対象に
        self.changed_annotation_ids = set(a['id'] for a in self.annotations)
        self.has_unsaved_changes = True
```

### タスク4: プロジェクト読み込み時の初期化 🔴

**優先度**: 高

**実装内容**:
```python
def load_annotations(self):
    """アノテーションを読み込み"""
    # 既存の読み込み処理...
    
    # スナップショットを初期化
    self.update_snapshot()
    self.has_unsaved_changes = False
    self.changed_annotation_ids.clear()
```

### タスク5: ユーザーフィードバックの改善 🟡

**優先度**: 中

#### 5-1. 保存時のメッセージ改善

**実装内容**:
```python
def save_project(self):
    changes = self.detect_changes()
    
    # 処理内容をメッセージに含める
    changed_count = len(changes['changed_ids'])
    added_count = len(changes['added_ids'])
    deleted_count = len(changes['deleted_ids'])
    
    if changed_count == 0 and added_count == 0 and deleted_count == 0:
        message = "変更がないため、一覧表のみを更新しました。"
    else:
        message = f"プロジェクト '{self.project_name}' を保存しました。\n"
        if added_count > 0:
            message += f"- 追加: {added_count}件\n"
        if changed_count > 0:
            message += f"- 変更: {changed_count}件\n"
        if deleted_count > 0:
            message += f"- 削除: {deleted_count}件\n"
    
    messagebox.showinfo("成功", message)
```

#### 5-2. 未保存変更の警告

**実装内容**:
```python
def on_closing(self):
    """ウィンドウを閉じる時の処理"""
    if self.has_unsaved_changes:
        result = messagebox.askyesnocancel(
            "未保存の変更",
            "保存していない変更があります。保存しますか？"
        )
        if result is None:  # キャンセル
            return
        elif result:  # はい
            self.save_project()
    
    self.root.destroy()
```

### タスク6: テストと検証 🟡

**優先度**: 中

#### 6-1. 単体テスト

**テスト項目**:
1. 変更検出ロジックのテスト
2. スナップショット機能のテスト
3. 差分保存の正確性テスト

#### 6-2. 統合テスト

**テスト項目**:
1. アノテーション追加→保存→変更→保存
2. オフセット変更→保存
3. 変更なし→保存（一覧表のみ更新）

#### 6-3. パフォーマンステスト

**計測項目**:
- 変更前: 全画像再生成の時間
- 変更後: 差分保存の時間
- 改善率の確認

### タスク7: ドキュメント作成 🟢

**優先度**: 低

**作成内容**:
- 実装仕様書
- ユーザーガイド（変更通知の読み方など）

---

## 🧪 テストシナリオ

### シナリオ1: 新規アノテーション追加

**手順**:
1. プロジェクトを読み込み
2. 新しいアノテーションを追加
3. 保存

**期待結果**:
- ✅ 新規アノテーションの画像のみ生成
- ✅ 全体図を再生成
- ✅ CSV/Excelを更新
- ✅ メッセージ: "追加: 1件"

### シナリオ2: 既存アノテーションの編集

**手順**:
1. プロジェクトを読み込み
2. 既存のアノテーションを編集（座標変更）
3. 保存

**期待結果**:
- ✅ 編集されたアノテーションの画像のみ再生成
- ✅ 全体図を再生成
- ✅ CSV/Excelを更新
- ✅ メッセージ: "変更: 1件"

### シナリオ3: テキスト情報のみ変更

**手順**:
1. プロジェクトを読み込み
2. アノテーションのテキスト情報のみ変更（例: 備考欄）
3. 保存

**期待結果**:
- ✅ 画像生成はスキップ（座標・色・形状は変更なし）
- ✅ CSV/Excelを更新
- ✅ メッセージ: "一覧表のみを更新しました"

### シナリオ4: 変更なし

**手順**:
1. プロジェクトを読み込み
2. 何も変更せず保存

**期待結果**:
- ✅ 画像生成は完全にスキップ
- ✅ CSV/Excelを更新
- ✅ メッセージ: "変更がないため、一覧表のみを更新しました"

### シナリオ5: アノテーション削除

**手順**:
1. プロジェクトを読み込み
2. アノテーションを削除
3. 保存

**期待結果**:
- ✅ 削除されたアノテーションの画像を削除
- ✅ 全体図を再生成
- ✅ CSV/Excelを更新
- ✅ メッセージ: "削除: 1件"

### シナリオ6: オフセット設定変更

**手順**:
1. プロジェクトを読み込み
2. オフセット設定を変更
3. 保存

**期待結果**:
- ✅ 全アノテーションの画像を再生成
- ✅ 全体図を再生成
- ✅ CSV/Excelを更新
- ✅ メッセージ: "変更: N件"（全アノテーション数）

---

## 📊 期待される効果

### パフォーマンス改善

**現状**（100アノテーションの場合）:
- CSV/Excel出力: 1秒
- 関連画像生成: 50秒（100枚 × 0.5秒）
- 全体図生成: 5秒
- 個別全体図生成: 100秒（100枚 × 1秒）
- **合計: 約156秒**

**改善後**（1アノテーションのみ変更の場合）:
- CSV/Excel出力: 1秒
- 関連画像生成: 0.5秒（1枚のみ）
- 全体図生成: 5秒
- 個別全体図生成: 1秒（1枚のみ）
- **合計: 約7.5秒**

**改善率**: **約95%の時間短縮**（変更1件の場合）

### ユーザー体験の改善

1. **待ち時間の大幅削減**: テキスト変更時は瞬時に保存完了
2. **明確なフィードバック**: 何が変更されたか明示
3. **未保存変更の警告**: データ損失のリスク低減

---

## 🎯 実装の優先順位

### Phase 1: コア機能（必須）

1. ✅ 変更検出システム実装
2. ✅ 差分保存メソッド実装
3. ✅ 変更追跡の統合
4. ✅ プロジェクト読み込み時の初期化

### Phase 2: 改善機能（推奨）

5. ✅ ユーザーフィードバック改善
6. ✅ 未保存変更警告

### Phase 3: 検証（必須）

7. ✅ テストと検証
8. ✅ ドキュメント作成

---

## 📋 まとめ

### 目的

プロジェクト保存時の処理時間を短縮し、ユーザー体験を向上

### 実装内容

1. 変更検出システム
2. 差分保存機能
3. 変更追跡の統合
4. ユーザーフィードバック

### 期待効果

- **95%の時間短縮**（変更1件の場合）
- 瞬時の保存完了（変更なしの場合）
- 明確なフィードバック

### 実装タスク数

- **必須タスク**: 7個
- **推奨タスク**: 2個
- **合計**: 9個

---

**次のステップ**: タスクの承認と実装開始
