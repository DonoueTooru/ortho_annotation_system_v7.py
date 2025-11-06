# Requirement 3: オルソ画像全体図のアノテーション位置修正 - 提案書

## 📋 概要

**問題**: プロジェクト保存時に生成される以下の画像で、アノテーション位置がずれている
1. 全体図（全てのアノテーション入り）: `{project_name}_annotated.png`
2. 個別全体図（ID毎）: `ID{id:03d}_全体図_{defect_type}.jpg`

**原因**: これらの画像保存時に `image_type` パラメータを指定していないため、オフセットが適用されていない

**影響範囲**:
- ✅ サーモ画像: オフセット適用済み (Requirement 1で対応)
- ✅ 可視画像: オフセット適用済み (Requirement 1で対応)
- ❌ オルソ画像全体図: オフセット未適用 ← **今回対応**
- ❌ オルソ画像個別全体図: オフセット未適用 ← **今回対応**

---

## 🔍 問題の詳細分析

### 現在のコード状況

#### ✅ 正常に動作している箇所（Requirement 1実装済み）

**`copy_related_images()` - サーモ/可視画像保存**:
```python
# Line 5017-5099
def copy_related_images(self):
    # サーモ画像
    annotated_thermal = self._draw_annotation_on_related_image(
        thermal_image, x, y, annotation_id, defect_type, color, shape,
        image_type='thermal'  # ✅ オフセット適用される
    )
    
    # 可視画像
    annotated_visible = self._draw_annotation_on_related_image(
        visible_image, x, y, annotation_id, defect_type, color, shape,
        image_type='visible'  # ✅ オフセット適用される
    )
```

#### ❌ 問題のある箇所

**`save_annotated_image()` - 全体図保存** (Line 4642-4686):
```python
def save_annotated_image(self):
    # 全てのアノテーションを描画
    for annotation in self.annotations:
        icon_height = self.draw_annotation_icon_on_image(
            annotated_image, draw, x, y, defect_type, color, shape,
            overall_scale
            # ❌ image_type パラメータがない → オフセット適用されない
        )
        
        self._draw_id_label_on_image(
            draw, x, y, annotation['id'], color,
            annotated_image.size, overall_scale, icon_height,
            # ❌ image_type パラメータがない → オフセット適用されない
        )
```

**`save_individual_annotated_images()` - 個別全体図保存** (Line 4719-4820):
```python
def save_individual_annotated_images(self):
    # 各IDごとのアノテーションを描画
    icon_height = self.draw_annotation_icon_on_image(
        annotated_image, draw, x, annotation_y, defect_type, color, shape,
        overall_scale
        # ❌ image_type パラメータがない → オフセット適用されない
    )
    
    self._draw_id_label_on_image(
        draw, x, annotation_y, annotation['id'], color,
        annotated_image.size, overall_scale, icon_height,
        # ❌ image_type パラメータがない → オフセット適用されない
    )
```

---

## 💡 解決策の提案

### 方針1: オルソ画像専用のオフセット設定を追加（推奨）

**メリット**:
- サーモ/可視画像とは異なるオフセットを設定可能
- 柔軟性が高い
- Requirement 2の設計思想と一貫性がある

**実装内容**:
1. 新しいオフセット変数を追加: `ortho_offset_x`, `ortho_offset_y`
2. 設定ダイアログに「オルソ画像」セクションを追加
3. `draw_annotation_icon_on_image()` で `image_type='ortho'` 対応
4. `save_annotated_image()` と `save_individual_annotated_images()` で `image_type='ortho'` を指定

### 方針2: オフセットなし（デフォルト値0）で修正（簡易版）

**メリット**:
- 実装が簡単
- 新しい設定項目が不要

**デメリット**:
- オルソ画像でもずれがある場合に対応できない
- 将来的に要望が出る可能性

---

## 📝 推奨実装内容（方針1）

### 1. オフセット変数の追加

**場所**: `__init__()` (Line 2088付近)

**追加コード**:
```python
# アノテーション位置オフセット設定（サーモ画像・可視画像用）
self.thermal_offset_x = 0
self.thermal_offset_y = 0
self.visible_offset_x = 0
self.visible_offset_y = 0

# 新規追加: オルソ画像用オフセット
self.ortho_offset_x = 0   # オルソ画像のX軸オフセット（ピクセル）
self.ortho_offset_y = 0   # オルソ画像のY軸オフセット（ピクセル）
```

### 2. 設定ダイアログの拡張

**場所**: `customize_settings()` (Line 4532-4595付近)

**追加UI**:
```python
# === アノテーション位置調整セクション ===
offset_frame = ttk.LabelFrame(scrollable_frame, text="アノテーション位置調整 (ピクセル単位)", padding=10)

# サーモ画像オフセット（既存）
ttk.Label(offset_frame, text="サーモ画像", font=("", 10, "bold"))
# ...

# 可視画像オフセット（既存）
ttk.Label(offset_frame, text="可視画像", font=("", 10, "bold"))
# ...

# 新規追加: オルソ画像オフセット
ttk.Separator(offset_frame, orient="horizontal").grid(...)
ttk.Label(offset_frame, text="オルソ画像（全体図）", font=("", 10, "bold"))

ttk.Label(offset_frame, text="X軸オフセット:")
ortho_x_var = tk.IntVar(value=self.ortho_offset_x)
ortho_x_spinbox = ttk.Spinbox(offset_frame, from_=-1000, to=1000, textvariable=ortho_x_var, width=10)

ttk.Label(offset_frame, text="Y軸オフセット:")
ortho_y_var = tk.IntVar(value=self.ortho_offset_y)
ortho_y_spinbox = ttk.Spinbox(offset_frame, from_=-1000, to=1000, textvariable=ortho_y_var, width=10)
```

**適用処理の追加**:
```python
def apply_settings():
    # 既存のオフセット適用
    self.thermal_offset_x = thermal_x_var.get()
    self.thermal_offset_y = thermal_y_var.get()
    self.visible_offset_x = visible_x_var.get()
    self.visible_offset_y = visible_y_var.get()
    
    # 新規: オルソ画像オフセット適用
    self.ortho_offset_x = ortho_x_var.get()
    self.ortho_offset_y = ortho_y_var.get()
    
    self.save_offset_settings()
    self.draw_annotations()
    dialog.destroy()
```

### 3. JSON保存/読込の拡張

**場所**: `save_offset_settings()` と `load_offset_settings()` (Line 5036-5090付近)

**保存**:
```python
def save_offset_settings(self):
    offset_data = {
        "thermal_offset_x": self.thermal_offset_x,
        "thermal_offset_y": self.thermal_offset_y,
        "visible_offset_x": self.visible_offset_x,
        "visible_offset_y": self.visible_offset_y,
        "ortho_offset_x": self.ortho_offset_x,    # 追加
        "ortho_offset_y": self.ortho_offset_y,    # 追加
        "updated_date": datetime.now().isoformat()
    }
    # JSON書き込み...
```

**読込**:
```python
def load_offset_settings(self):
    # 既存のオフセット読込
    self.thermal_offset_x = data.get('thermal_offset_x', 0)
    self.thermal_offset_y = data.get('thermal_offset_y', 0)
    self.visible_offset_x = data.get('visible_offset_x', 0)
    self.visible_offset_y = data.get('visible_offset_y', 0)
    
    # 新規: オルソ画像オフセット読込
    self.ortho_offset_x = data.get('ortho_offset_x', 0)
    self.ortho_offset_y = data.get('ortho_offset_y', 0)
```

### 4. 描画メソッドの拡張

**場所**: `draw_annotation_icon_on_image()` (Line 2792-2869)

**変更**:
```python
def draw_annotation_icon_on_image(self, image, draw, x, y, defect_type, color, 
                                  fallback_shape, scale_multiplier=1.0, image_type=None):
    # オフセットの適用
    offset_x = 0
    offset_y = 0
    if image_type == 'thermal':
        offset_x = self.thermal_offset_x
        offset_y = self.thermal_offset_y
    elif image_type == 'visible':
        offset_x = self.visible_offset_x
        offset_y = self.visible_offset_y
    elif image_type == 'ortho':  # 追加
        offset_x = self.ortho_offset_x
        offset_y = self.ortho_offset_y
    
    adjusted_x = x + offset_x
    adjusted_y = y + offset_y
    # 以降、adjusted_x/y を使用...
```

**場所**: `_draw_id_label_on_image()` (Line 2714-2763)

**同様の変更を適用**

### 5. 全体図保存メソッドの修正

**場所**: `save_annotated_image()` (Line 4642-4686)

**変更前**:
```python
icon_height = self.draw_annotation_icon_on_image(
    annotated_image, draw, x, y, defect_type, color, shape, overall_scale
)

self._draw_id_label_on_image(
    draw, x, y, annotation['id'], color,
    annotated_image.size, overall_scale, icon_height,
)
```

**変更後**:
```python
icon_height = self.draw_annotation_icon_on_image(
    annotated_image, draw, x, y, defect_type, color, shape, overall_scale,
    image_type='ortho'  # 追加: オルソ画像オフセットを適用
)

self._draw_id_label_on_image(
    draw, x, y, annotation['id'], color,
    annotated_image.size, overall_scale, icon_height,
    image_type='ortho'  # 追加: オルソ画像オフセットを適用
)
```

### 6. 個別全体図保存メソッドの修正

**場所**: `save_individual_annotated_images()` (Line 4719-4820)

**変更前**:
```python
icon_height = self.draw_annotation_icon_on_image(
    annotated_image, draw, x, annotation_y,
    defect_type, color, shape, overall_scale
)

self._draw_id_label_on_image(
    draw, x, annotation_y, annotation['id'], color,
    annotated_image.size, overall_scale, icon_height,
)
```

**変更後**:
```python
icon_height = self.draw_annotation_icon_on_image(
    annotated_image, draw, x, annotation_y,
    defect_type, color, shape, overall_scale,
    image_type='ortho'  # 追加: オルソ画像オフセットを適用
)

self._draw_id_label_on_image(
    draw, x, annotation_y, annotation['id'], color,
    annotated_image.size, overall_scale, icon_height,
    image_type='ortho'  # 追加: オルソ画像オフセットを適用
)
```

---

## 📊 実装タスク一覧

### 🔴 高優先度タスク

1. **問題分析** ✅ 完了
   - `save_annotated_image()` でオフセットが適用されない原因を特定

2. **解決策検討** ⏳ 提案中
   - オルソ画像専用オフセット vs オフセットなし
   - **推奨**: オルソ画像専用オフセットを追加

3. **実装3-1: オフセット変数追加** ⏳
   - `__init__()` に `ortho_offset_x`, `ortho_offset_y` を追加

4. **実装3-2: 設定ダイアログUI拡張** ⏳
   - 「オルソ画像（全体図）」セクションを追加
   - X/Y軸オフセット入力欄を追加

5. **実装3-3: JSON永続化** ⏳
   - `save_offset_settings()` にオルソ画像オフセット追加
   - `load_offset_settings()` にオルソ画像オフセット追加

6. **実装3-4: save_annotated_image() 修正** ⏳
   - `image_type='ortho'` パラメータを追加

7. **実装3-5: draw_annotation_icon_on_image() 拡張** ⏳
   - `image_type='ortho'` の分岐を追加

8. **実装3-6: _draw_id_label_on_image() 拡張** ⏳
   - `image_type='ortho'` の分岐を追加

### 🟡 中優先度タスク

9. **実装3-7: save_individual_annotated_images() 修正** ⏳
   - 個別全体図でも `image_type='ortho'` を指定

### テストタスク

10. **テスト: 全体図のアノテーション位置修正確認** ⏳
11. **テスト: 個別全体図のアノテーション位置修正確認** ⏳
12. **テスト: オルソ画像オフセット設定の永続化確認** ⏳

### Git管理

13. **Git: コミット & PR更新** ⏳

---

## 🎯 期待される効果

### Before（現状）
- ❌ 全体図: アノテーション位置がずれる
- ❌ 個別全体図: アノテーション位置がずれる
- ✅ サーモ画像: 正しい位置
- ✅ 可視画像: 正しい位置

### After（実装後）
- ✅ 全体図: オフセット適用で正しい位置
- ✅ 個別全体図: オフセット適用で正しい位置
- ✅ サーモ画像: 正しい位置（既存）
- ✅ 可視画像: 正しい位置（既存）

---

## 🔧 実装難易度と工数見積もり

### 難易度: ⭐⭐☆☆☆ (中程度)

**理由**: 
- Requirement 2の設計を踏襲するため、実装パターンは確立済み
- 既存コードの修正箇所が明確
- テストが必要だが、既存の仕組みを流用可能

### 工数見積もり: 約1-2時間

- **実装**: 45分
  - オフセット変数追加: 5分
  - UI拡張: 15分
  - JSON永続化: 10分
  - 描画メソッド修正: 15分
  
- **テスト**: 30分
  - 動作確認
  - オフセット設定テスト
  - 画像保存テスト

- **ドキュメント & Git**: 15分
  - コミットメッセージ作成
  - PR更新
  - ドキュメント更新

---

## 📦 後方互換性

### ✅ 既存プロジェクトへの影響

**問題なく動作**:
- オフセット設定がない場合、デフォルト値(0)を使用
- 既存の `offset_settings.json` に `ortho_offset_x/y` がなくても正常動作
- 既存のサーモ/可視画像オフセット設定は保持される

**変更される点**:
- 次回保存時から、全体図にもオフセットが適用される
- 設定ダイアログに新しいセクションが追加される

---

## 🎬 実装後のユーザーワークフロー

### シナリオ: 全体図のアノテーション位置を調整したい

1. プロジェクトを開く
2. 「保存」を実行（初回）
3. 全体図を確認 → アノテーション位置がずれている
4. 「色設定」ボタンをクリック
5. 「アノテーション位置調整」セクションまでスクロール
6. **「オルソ画像（全体図）」セクション** で X/Y オフセットを入力
   - 例: X軸 +15px, Y軸 -10px
7. 「適用して閉じる」をクリック
8. 再度「保存」を実行
9. 全体図を確認 → アノテーション位置が修正されている ✅

---

## ❓ よくある質問

### Q1: なぜオルソ画像用のオフセットが必要なのか？

**A**: オルソ画像、サーモ画像、可視画像はそれぞれ異なる画像ファイルであり、画像の解像度や座標系が微妙に異なる可能性があります。そのため、それぞれに独立したオフセット設定を持つことで、すべての画像で正確なアノテーション位置を実現できます。

### Q2: Requirement 2 との違いは？

**A**: 
- **Requirement 2**: サーモ/可視画像のオフセット設定を追加
- **Requirement 3**: オルソ画像（全体図）のオフセット設定を追加

設計思想は同じで、対象画像が異なるだけです。

### Q3: デフォルト値(0)のままでも動作するか？

**A**: はい、動作します。オフセット値が0の場合、現在の動作と同じになります。オフセット設定は必要な場合のみ調整すればOKです。

---

## 📚 参考資料

- **Requirement 2実装**: `REQUIREMENT2_OFFSET_IMPLEMENTATION.md`
- **Requirement 1実装**: `REQUIREMENT1_UNIFIED_IMAGE_SAVE.md`
- **現在のPR**: https://github.com/DonoueTooru/ortho_annotation_system_v7.py/pull/1

---

## ✅ 承認待ち

このTODOリストと実装方針で問題ないか、ユーザーからの承認をお待ちしています。

**承認いただければ、直ちに実装を開始します!** (''◇'')ゞ
