# Requirement 4: オフセット調整の累積問題の修正 - 提案書

## 📋 概要

**問題**: アノテーション位置調整を繰り返すと、アノテーションの位置が本来の位置からどんどんずれていく

**原因（推定）**: オフセット設定を変更するたびに、アノテーション座標自体が更新されている可能性

**目標**: アノテーションの元座標は常に固定し、オフセットは画像保存時のみ適用する

---

## 🔍 問題の詳細分析

### 現象
1. アノテーションを登録（例: x=100, y=100）
2. オフセット設定で +10px を設定
3. 画像を保存 → アノテーションが x=110, y=110 に表示される（正常）
4. オフセット設定を +20px に変更
5. 画像を保存 → アノテーションが x=130, y=130 に表示される（**異常**）
   - **期待**: x=120, y=120（元座標100 + オフセット20）
   - **実際**: x=130, y=130（前回の110 + オフセット20）

### 推定される原因

#### パターンA: オフセット適用時にアノテーション座標を更新している
```python
# 悪い例（現在の実装の可能性）
def apply_settings():
    # オフセット設定を適用
    self.ortho_offset_x = ortho_x_var.get()
    self.ortho_offset_y = ortho_y_var.get()
    
    # ❌ アノテーション座標を更新してしまっている？
    for annotation in self.annotations:
        annotation['x'] += self.ortho_offset_x
        annotation['y'] += self.ortho_offset_y
```

#### パターンB: キャンバス表示時にもオフセットが適用されている
```python
# 悪い例
def draw_annotations(self):
    for annotation in self.annotations:
        # ❌ 表示時にもオフセット適用？
        x = annotation["x"] + self.ortho_offset_x
        y = annotation["y"] + self.ortho_offset_y
        # 描画...
```

---

## 💡 正しい設計方針

### 基本原則

1. **アノテーション座標は元の位置を保持**
   - `annotation['x']`, `annotation['y']` は常にユーザーがクリックした元の座標
   - オフセット設定の変更でアノテーション座標は変更しない

2. **キャンバス表示時はオフセットを適用しない**
   - ユーザーがクリックした位置に正確に表示
   - オフセットは保存時のみの補正値

3. **画像保存時のみオフセットを適用**
   - `save_annotated_image()`: オルソ画像全体図
   - `save_individual_annotated_images()`: 個別全体図
   - `copy_related_images()`: サーモ/可視画像

### データフロー

```
[ユーザークリック]
    ↓
[annotation['x'] = クリック位置X]  ← 常に元の位置
[annotation['y'] = クリック位置Y]  ← 常に元の位置
    ↓
    ├─→ [キャンバス表示]
    │       ↓
    │   [x, y = annotation['x'], annotation['y']]  ← オフセット適用なし
    │       ↓
    │   [画面に表示]
    │
    └─→ [画像保存]
            ↓
        [adjusted_x = annotation['x'] + offset_x]  ← オフセット適用
        [adjusted_y = annotation['y'] + offset_y]  ← オフセット適用
            ↓
        [画像に描画]
```

---

## 🔧 現在の実装の確認が必要な箇所

### 1. `customize_settings()` の `apply_settings()`
**確認事項**: オフセット設定変更時にアノテーション座標を更新していないか？

**期待される実装**:
```python
def apply_settings():
    # オフセット設定を適用
    self.thermal_offset_x = thermal_x_var.get()
    self.thermal_offset_y = thermal_y_var.get()
    self.visible_offset_x = visible_x_var.get()
    self.visible_offset_y = visible_y_var.get()
    self.ortho_offset_x = ortho_x_var.get()
    self.ortho_offset_y = ortho_y_var.get()
    
    # オフセット設定を保存
    self.save_offset_settings()
    
    # ❌ アノテーション座標は更新しない
    # ✅ キャンバス表示のみ更新（オフセットは適用しない）
    self.draw_annotations()
    
    dialog.destroy()
```

### 2. `draw_annotations()`
**確認事項**: キャンバス表示時にオフセットを適用していないか？

**期待される実装**:
```python
def draw_annotations(self):
    for annotation in self.annotations:
        # ✅ 元の座標をそのまま使用（オフセット適用なし）
        x = annotation["x"] * self.zoom_factor
        y = annotation["y"] * self.zoom_factor
        
        # 描画処理...
```

### 3. 画像保存メソッド
**確認事項**: 保存時のみオフセットを適用しているか？

**期待される実装**:
```python
def save_annotated_image(self):
    for annotation in self.annotations:
        # 元の座標を取得
        x = annotation["x"]
        y = annotation["y"]
        
        # ✅ 描画時にオフセット適用（image_type='ortho'）
        icon_height = self.draw_annotation_icon_on_image(
            ..., x, y, ..., image_type='ortho'
        )
```

---

## 📝 実装タスク

### タスク1: 問題箇所の特定 🔴
**優先度**: 高

**作業内容**:
1. `apply_settings()` でアノテーション座標を変更していないか確認
2. `draw_annotations()` でオフセットを適用していないか確認
3. その他、アノテーション座標を変更している箇所を特定

### タスク2: 設計方針の確認 🔴
**優先度**: 高

**確認事項**:
- アノテーション座標は常に元の位置を保持する
- キャンバス表示時はオフセット未適用
- 画像保存時のみオフセット適用

### タスク3: 実装修正（必要に応じて） 🔴
**優先度**: 高

#### 3-1. `apply_settings()` の修正
**目的**: オフセット設定変更時にアノテーション座標を変更しない

**修正方針**:
```python
def apply_settings():
    # オフセット変数を更新
    self.ortho_offset_x = ortho_x_var.get()
    self.ortho_offset_y = ortho_y_var.get()
    # ...
    
    # ❌ 削除: アノテーション座標の更新処理
    # for annotation in self.annotations:
    #     annotation['x'] += offset...
    
    # ✅ 保持: キャンバス再描画（オフセット未適用）
    self.draw_annotations()
```

#### 3-2. `draw_annotations()` の確認
**目的**: キャンバス表示時にオフセットを適用しない

**確認ポイント**:
```python
def draw_annotations(self):
    for annotation in self.annotations:
        # ✅ これが正しい
        x = annotation["x"] * self.zoom_factor
        y = annotation["y"] * self.zoom_factor
        
        # ❌ これが間違い（もしあれば削除）
        # x = (annotation["x"] + self.ortho_offset_x) * self.zoom_factor
```

#### 3-3. 画像保存メソッドの確認
**目的**: 保存時のみオフセットを適用

**確認ポイント**:
- `save_annotated_image()`: `image_type='ortho'` を指定済み ✅
- `save_individual_annotated_images()`: `image_type='ortho'` を指定済み ✅
- `copy_related_images()`: `image_type='thermal'/'visible'` を指定済み ✅

**これらは既に正しく実装されているはず**

---

## 🧪 テスト手順

### テスト1: オフセット調整の繰り返しテスト
1. アノテーションを登録（例: 画面上の特定位置）
2. オフセット設定を +10px, +10px に設定
3. プロジェクトを保存
4. 保存された画像を確認（アノテーションが元の位置 + 10px に表示される）
5. オフセット設定を +20px, +20px に変更
6. プロジェクトを再保存
7. 保存された画像を確認
   - **期待**: アノテーションが元の位置 + 20px に表示される
   - **NG**: アノテーションが元の位置 + 30px に表示される

### テスト2: 元座標の保持確認
1. アノテーションを登録
2. annotations.json を確認
3. オフセット設定を変更
4. annotations.json を再確認
   - **期待**: x, y 座標が変わっていない
   - **NG**: x, y 座標が変わっている

### テスト3: キャンバス表示の確認
1. アノテーションを登録
2. オフセット設定を変更
3. キャンバス上のアノテーション表示を確認
   - **期待**: アノテーションは元の位置に表示される
   - **NG**: アノテーションが移動している

---

## 🎯 期待される結果

### Before（問題がある場合）
```
初回登録: annotation['x'] = 100
オフセット +10px 設定 → 保存 → 画像上で x=110 ✅
オフセット +20px 変更 → 保存 → 画像上で x=130 ❌（100+10+20）
```

### After（修正後）
```
初回登録: annotation['x'] = 100（常にこの値を保持）
オフセット +10px 設定 → 保存 → 画像上で x=110 ✅
オフセット +20px 変更 → 保存 → 画像上で x=120 ✅（100+20）
オフセット 0px 変更 → 保存 → 画像上で x=100 ✅（100+0）
```

---

## 🔍 調査結果の記録

### 調査項目チェックリスト

#### 1. `customize_settings()` の `apply_settings()` ✅ **正常**
- [x] オフセット変数の更新のみ行っている（Line 4597-4616）
- [x] アノテーション座標を変更する処理はない
- [x] `draw_annotations()` を呼び出しているが、オフセット未適用（Line 4614）

**コード確認結果**:
```python
def apply_settings():  # Line 4597
    # 色設定を適用
    for defect_type, color_var in color_vars.items():
        self.defect_types[defect_type] = color_var.get()
    
    # オフセット設定を適用
    self.thermal_offset_x = thermal_x_var.get()
    self.thermal_offset_y = thermal_y_var.get()
    self.visible_offset_x = visible_x_var.get()
    self.visible_offset_y = visible_y_var.get()
    self.ortho_offset_x = ortho_x_var.get()
    self.ortho_offset_y = ortho_y_var.get()
    
    # オフセット設定を保存
    self.save_offset_settings()
    
    # 表示を更新
    self.draw_annotations()  # ✅ 再描画のみ、座標変更なし
    dialog.destroy()
```

#### 2. `draw_annotations()` ✅ **正常**
- [x] アノテーション座標をそのまま使用している（Line 2782-2783）
- [x] オフセットを加算していない
- [x] ズーム倍率のみ適用している

**コード確認結果**:
```python
def draw_annotations(self):  # Line 2777
    for annotation in self.annotations:
        # ✅ オフセット適用なし、元座標 × ズーム倍率のみ
        x = annotation["x"] * self.zoom_factor
        y = annotation["y"] * self.zoom_factor
        # 描画処理...
```

#### 3. アノテーション座標の更新箇所 ✅ **正常**
- [x] アノテーション移動機能のみが座標を更新（Line 3270-3275, 3328-3333）
- [x] その他、意図しない更新はない

**コード確認結果**:
```bash
# annotation["x"] = ... の検索結果
3270:            self.moving_annotation["x"] = image_x
3274:            self.moving_annotation["x"] = max(0, min(...))
3328:        self.moving_annotation["x"] = self.move_original_pos[0] + dx
3332:        self.moving_annotation["x"] = max(0, min(...))
3359:            self.moving_annotation["x"] = self.move_original_pos[0]
```
すべてアノテーション移動機能の正常な動作

#### 4. 画像保存時のソース画像パス確認 ✅ **正常**
- [x] `copy_related_images()` は `annotation['thermal_image']` から読み込み（Line 5066）
- [x] このパスは**元のWebODM画像パス**を指している
- [x] 保存後も `annotation['thermal_image']` は更新されない
- [x] よって、常に元画像からアノテーションを描画する

**コード確認結果**:
```python
def copy_related_images(self):  # Line 5047
    for annotation in self.annotations:
        x = annotation['x']  # ✅ 元座標
        y = annotation['y']  # ✅ 元座標
        
        if annotation.get('thermal_image'):
            src_path = annotation['thermal_image']  # ✅ 元のWebODM画像パス
            thermal_image = Image.open(src_path)  # ✅ 常に元画像から読み込み
            
            annotated_thermal = self._draw_annotation_on_related_image(
                thermal_image, x, y, ..., image_type='thermal'
            )  # ✅ ここでオフセット適用
```

**`annotation['thermal_image']` の更新箇所検索**:
```bash
3557:  annotation["thermal_image"] = thermal_path  # アノテーション追加時
3569:  annotation["thermal_image"] = file_path     # アノテーション追加時
3581:  annotation["thermal_image"] = selected_path # アノテーション追加時
4121:  annotation["thermal_image"] = thermal_path  # アノテーション編集時
4143:  annotation["thermal_image"] = file_path     # アノテーション編集時
4157:  annotation["thermal_image"] = selected_path # アノテーション編集時
```
すべてユーザー操作による設定のみ、保存処理での更新はなし

### ✅ 結論: 現在の実装は**正しい**

**重要な発見**:
1. アノテーション座標 (`annotation['x']`, `annotation['y']`) は**常に元の位置を保持**
2. キャンバス表示時はオフセット**適用されない**
3. 画像保存時のみオフセット適用され、**常に元画像から読み込む**
4. **累積は発生しないアーキテクチャ**

---

## 💭 ユーザー報告問題の再評価

### 可能性の分析

#### 可能性1: ユーザーの期待と実装の不一致 ⚠️ **最有力**
**仮説**: ユーザーは**キャンバス上でもオフセット効果を確認したい**

**現在の動作**:
- キャンバス表示: オフセット適用なし（元座標のまま表示）
- 保存画像: オフセット適用あり

**ユーザーの期待**:
- キャンバス表示: オフセット適用あり（保存前にプレビューしたい）
- 保存画像: オフセット適用あり

**解決案**:
1. `draw_annotations()` で `ortho_offset` を適用してキャンバスでもプレビュー表示
2. ただし、これには設計上の課題あり：
   - アノテーション移動機能との整合性
   - クリック座標とアノテーション座標のマッピング
   - ユーザー混乱の可能性（画面上の位置とデータの位置が異なる）

#### 可能性2: テスト環境の問題 🔍
**仮説**: キャッシュや再読み込みの問題

**考えられるシナリオ**:
- 画像ビューアーが前回の保存画像をキャッシュしている
- プロジェクトの再読み込みが正しく行われていない
- 複数のプロジェクトを混同している

**解決案**:
- プロジェクトの完全な再起動
- 出力フォルダの削除後に再保存
- 異なるオフセット値で明確に区別できるテスト

#### 可能性3: 別の要因による位置ずれ 🔍
**仮説**: オフセット以外の要因

**考えられる要因**:
- ズーム機能との干渉
- アノテーション移動機能との干渉
- 画像スケール計算の問題

**解決案**:
- ログ出力を追加して座標を追跡
- 各ステップでのアノテーション座標を記録

---

## 📚 関連情報

### 関連実装
- **Requirement 2**: サーモ/可視画像オフセット（同じ設計であるべき）
- **Requirement 3**: オルソ画像オフセット（問題が発生している箇所）

### 設計原則の再確認
1. **座標の永続性**: アノテーション座標は登録時の値を永続的に保持
2. **オフセットの役割**: 保存時の補正値（表示時は無関係）
3. **設定の独立性**: オフセット設定の変更はアノテーションデータに影響しない

---

## ✅ 次のアクション

### ステップ1: 問題箇所の特定
1. 現在のコードを詳細に調査
2. アノテーション座標が変更される箇所を特定
3. オフセットが意図しない場所で適用されていないか確認

### ステップ2: 修正実装（必要な場合のみ）
1. 問題箇所を修正
2. アノテーション座標は常に元の位置を保持
3. オフセットは保存時のみ適用

### ステップ3: テスト
1. オフセット調整の繰り返しテスト
2. 元座標の保持確認
3. キャンバス表示の確認

### ステップ4: コミット & PR更新
1. 変更をコミット
2. PRを更新
3. ドキュメントを更新

---

## 🤔 考えられるシナリオ

### シナリオ1: 既に正しく実装されている
**可能性**: 中～高

**状況**: 
- 実装は正しいが、ユーザーの操作手順に問題がある
- または、別の要因（ブラウザキャッシュ、ファイルの再読み込みなど）

**対応**:
- コードレビューで問題がないことを確認
- ユーザーに正しい操作手順を案内
- キャッシュクリアやプロジェクトの再読み込みを試す

### シナリオ2: 実装に問題がある
**可能性**: 中

**状況**:
- オフセット設定時にアノテーション座標を更新している
- またはキャンバス表示時にオフセットを適用している

**対応**:
- 問題箇所を特定して修正
- テストで動作確認

### シナリオ3: 設計の誤解
**可能性**: 低

**状況**:
- オフセットは累積的に適用するべきという誤った理解

**対応**:
- 設計方針を再確認
- ドキュメントを明確化

---

## 📋 まとめ

### 問題
アノテーション位置調整を繰り返すと位置がずれる

### 原因（推定）
- オフセット設定変更時にアノテーション座標を更新している
- またはキャンバス表示時にオフセットを適用している

### 解決方針
1. アノテーション座標は常に元の位置を保持
2. キャンバス表示時はオフセット未適用
3. 画像保存時のみオフセット適用

### 実装タスク
1. 問題箇所の特定
2. 必要に応じて修正
3. テストで動作確認
4. コミット & PR更新

---

## 🎯 推奨アクション

### 現時点の結論
**コードレビューの結果**: 現在の実装は**技術的に正しい**

- アノテーション座標は常に元の位置を保持 ✅
- キャンバス表示時はオフセット未適用 ✅
- 画像保存時のみオフセット適用 ✅
- 常に元画像から読み込み、累積なし ✅

### ユーザーへの確認事項 🔴 **最優先**

以下の点をユーザーに確認する必要があります：

#### 質問1: どこで累積を観測していますか？
- [ ] キャンバス画面上でアノテーションの表示位置がずれる
- [ ] 保存された画像ファイルでアノテーションの位置がずれる
- [ ] 両方

#### 質問2: 具体的な操作手順を教えてください
1. アノテーションを登録
2. オフセット設定を +10px に設定して保存
3. その後の操作は？
   - [ ] プロジェクトを再起動した
   - [ ] プロジェクトを再起動せず、続けて設定を変更した
   - [ ] 保存画像を確認する方法は？（外部ビューアー、再読み込み）

#### 質問3: 期待する動作は？
- [ ] キャンバス上でもオフセット効果をリアルタイムプレビューしたい
- [ ] 保存画像のみオフセット適用されればよい（現在の実装）

### 次のステップ

#### オプションA: ユーザーフィードバック待ち（推奨）
1. 上記の質問をユーザーに投げかける
2. 具体的な再現手順を入手
3. 必要に応じて実装を調整

#### オプションB: キャンバスプレビュー機能を追加（要確認）
**IF** ユーザーがキャンバス上でオフセット効果を見たい場合：

**実装方針**:
```python
def draw_annotations(self):
    for annotation in self.annotations:
        # 元座標
        orig_x = annotation["x"]
        orig_y = annotation["y"]
        
        # オフセット適用（プレビュー用）
        display_x = (orig_x + self.ortho_offset_x) * self.zoom_factor
        display_y = (orig_y + self.ortho_offset_y) * self.zoom_factor
        
        # 描画...
```

**注意事項**:
- アノテーション移動機能との整合性を保つ必要あり
- クリック座標の変換ロジックを調整
- ユーザーに「画面上の位置」と「データ上の位置」の違いを説明

#### オプションC: デバッグ機能を追加（暫定対応）
**目的**: 問題の原因を特定するためのログ出力

**実装内容**:
1. `apply_settings()` 実行時にアノテーション座標をログ出力
2. 保存前後でアノテーション座標をログ出力
3. `annotations.json` の変化を追跡

---

**次のステップ**: ユーザーに上記の確認事項を質問し、具体的な再現手順を入手します。
