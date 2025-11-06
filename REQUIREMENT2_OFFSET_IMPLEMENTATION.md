# Requirement 2: アノテーション位置調整機能の実装完了報告

## 概要
サーモ画像・可視画像保存時のアノテーション位置ずれを補正するため、オフセット設定機能を実装しました。

## 実装日時
2025-11-06

## 実装内容

### 1. オフセット変数の追加 ✅
**場所**: `OrthoImageAnnotationSystem.__init__()` (Line 2078-2087)

```python
# アノテーション位置オフセット設定(サーモ画像・可視画像用)
self.thermal_offset_x = 0           # サーモ画像のX軸オフセット(ピクセル)
self.thermal_offset_y = 0           # サーモ画像のY軸オフセット(ピクセル)
self.visible_offset_x = 0           # 可視画像のX軸オフセット(ピクセル)
self.visible_offset_y = 0           # 可視画像のY軸オフセット(ピクセル)
```

**特徴**:
- 4つの独立したオフセット変数 (サーモX/Y、可視X/Y)
- ピクセル単位での精密な位置調整が可能
- デフォルト値は0 (オフセットなし)

### 2. 設定ダイアログの拡張 ✅
**場所**: `customize_settings()` (旧 `customize_colors()`) (Line 4425-4528)

**変更点**:
- メソッド名を `customize_colors()` → `customize_settings()` にリネーム
- ダイアログサイズを `300x400` → `500x650` に拡大
- スクロール可能なUIに変更

**UI構成**:

#### セクション1: 色設定
- 既存の不具合タイプ別色選択機能を保持
- 各不具合タイプごとに「色選択」ボタン

#### セクション2: アノテーション位置調整
**サーモ画像設定**:
- X軸オフセット入力欄 (Spinbox, -1000 ～ +1000px)
- Y軸オフセット入力欄 (Spinbox, -1000 ～ +1000px)

**可視画像設定**:
- X軸オフセット入力欄 (Spinbox, -1000 ～ +1000px)
- Y軸オフセット入力欄 (Spinbox, -1000 ～ +1000px)

**操作性**:
- 説明文: "保存時にサーモ画像・可視画像に描画するアノテーションの位置を調整できます"
- ピクセル単位での表示 ("px")
- セクション間にセパレーター
- 「適用して閉じる」ボタンで設定を保存

### 3. JSON永続化機能 ✅

#### 保存機能: `save_offset_settings()` (Line 4949-4969)
**保存場所**: `{project_path}/アノテーション設定フォルダ/offset_settings.json`

**保存データ構造**:
```json
{
  "thermal_offset_x": 0,
  "thermal_offset_y": 0,
  "visible_offset_x": 0,
  "visible_offset_y": 0,
  "updated_date": "2025-11-06T12:34:56.789012"
}
```

**特徴**:
- UTF-8エンコーディング
- インデント付きJSON (indent=2)
- エラーハンドリング付き
- 更新日時を記録

#### 読込機能: `load_offset_settings()` (Line 4971-4990)
**呼び出しタイミング**: `load_annotations()` 内で自動呼び出し

**処理内容**:
1. `offset_settings.json` の存在チェック
2. 存在する場合、4つのオフセット値を読み込み
3. ファイルが存在しない場合はデフォルト値(0)を使用
4. エラー発生時もデフォルト値を維持

### 4. 描画メソッドへのオフセット適用 ✅

#### `draw_annotation_icon_on_image()` の拡張 (Line 2792-2869)
**新パラメータ**: `image_type=None`
- `'thermal'`: サーモ画像用オフセットを適用
- `'visible'`: 可視画像用オフセットを適用
- `None`: オフセットなし (オルソ画像用)

**オフセット適用ロジック**:
```python
offset_x = 0
offset_y = 0
if image_type == 'thermal':
    offset_x = self.thermal_offset_x
    offset_y = self.thermal_offset_y
elif image_type == 'visible':
    offset_x = self.visible_offset_x
    offset_y = self.visible_offset_y

adjusted_x = x + offset_x
adjusted_y = y + offset_y
```

**適用範囲**:
- アイコン描画位置
- フォールバック形状 (十字、矢印、円形、四角) の描画位置
- 画像境界内へのクランピング処理

#### `_draw_id_label_on_image()` の拡張 (Line 2714-2763)
**新パラメータ**: `image_type=None`

**オフセット適用**:
- ID番号ラベルの描画位置にも同じオフセットを適用
- アイコンとラベルの相対位置関係を保持
- フォント設定、ストローク幅などは既存ロジックを維持

### 5. UIボタンの更新 ✅
**場所**: `setup_ui()` (Line 2142)

```python
# 変更前
ttk.Button(button_frame, text="色設定", command=self.customize_colors)

# 変更後
ttk.Button(button_frame, text="色設定", command=self.customize_settings)
```

**表示**: ボタンラベルは「色設定」のまま（後方互換性）

## 使用方法

### 設定手順
1. メインUIの「色設定」ボタンをクリック
2. 「色・アノテーション位置設定」ダイアログが開く
3. 下部の「アノテーション位置調整」セクションで調整
   - サーモ画像のX/Y軸オフセットを入力
   - 可視画像のX/Y軸オフセットを入力
4. 「適用して閉じる」ボタンをクリック
5. 設定が自動保存される

### オフセット値の決定方法
1. 現在のシステムでプロジェクトを保存
2. サーモ画像/可視画像のアノテーション位置を確認
3. ずれている量をピクセル単位で計測
4. オフセット設定で補正値を入力
5. 再度保存して確認

### プラス/マイナスの意味
- **X軸**: プラス = 右方向、マイナス = 左方向
- **Y軸**: プラス = 下方向、マイナス = 上方向

## 技術的な詳細

### ファイル構成
- **実装ファイル**: `ortho_annotation_system_v7.py`
- **設定ファイル**: `{project_name}/アノテーション設定フォルダ/offset_settings.json`

### 主要な変更箇所
1. `__init__()`: オフセット変数の初期化 (Line 2078-2087)
2. `customize_settings()`: UI実装 (Line 4425-4528)
3. `save_offset_settings()`: JSON保存 (Line 4949-4969)
4. `load_offset_settings()`: JSON読込 (Line 4971-4990)
5. `load_annotations()`: オフセット自動読込 (Line 4992-5037, Line 5032)
6. `draw_annotation_icon_on_image()`: オフセット適用 (Line 2792-2869)
7. `_draw_id_label_on_image()`: オフセット適用 (Line 2714-2763)
8. `setup_ui()`: ボタン参照更新 (Line 2142)

### 後方互換性
- 既存プロジェクトで`offset_settings.json`が存在しない場合、デフォルト値(0)を使用
- 既存の色設定機能は完全に保持
- 既存のアノテーションデータに影響なし

## 注意事項

### 現在の制限事項
1. **オフセットの適用範囲**
   - 現時点では `draw_annotation_icon_on_image()` と `_draw_id_label_on_image()` にオフセット機能を実装
   - **実際のサーモ/可視画像保存時にオフセットを適用するには、Requirement 1の実装が必要**
   - 現在の `copy_related_images()` は元画像をそのままコピーしており、アノテーションを描画していない

2. **Requirement 1との連携**
   - Requirement 1で実装予定: サーモ/可視画像にアノテーションを描画して保存
   - その際に `image_type='thermal'` または `image_type='visible'` パラメータを渡すことでオフセットが適用される

### 推奨される使用方法
- 最初はデフォルト値(0)で保存し、ずれを確認
- ずれの量を測定してからオフセット値を設定
- 小さな値から試して段階的に調整

## テスト項目 (未実施)

Requirement 2の機能テストは、Requirement 1の実装後に実施予定:

- [ ] オフセット設定の永続化確認
- [ ] オフセット値がサーモ/可視画像に正しく適用されることを確認
- [ ] UIの動作確認 (Spinboxの動作、適用ボタンの動作)
- [ ] JSON読込/保存の正常動作確認

## 次のステップ

### Requirement 1の実装 (未実施)
1. `copy_related_images()` の修正
   - 単純なファイルコピーから、アノテーション入り画像生成に変更
2. 新メソッド `save_thermal_visible_with_annotations()` の作成
   - サーモ/可視画像を読み込み
   - アノテーションを描画 (オフセット適用)
   - 統一された命名規則で保存
3. フォルダ構成の統一
   - 「サーモ画像フォルダ」と「可視画像フォルダ」を統合検討

## 実装完了の確認

### 完了した項目 (8/8)
- ✅ 実装2-1: オフセット変数の追加
- ✅ 実装2-2: メソッドのリネーム
- ✅ 実装2-3: 設定ダイアログの拡張
- ✅ 実装2-4: サーモ画像用オフセット入力欄
- ✅ 実装2-5: 可視画像用オフセット入力欄
- ✅ 実装2-6: JSON保存機能
- ✅ 実装2-7: JSON読込機能
- ✅ 実装2-8: 描画メソッドへのオフセット適用

### 保留中の項目
- ⏳ テスト項目 (Requirement 1実装後に実施)
- ⏳ Requirement 1 (画像保存の統一)

## まとめ

Requirement 2 (アノテーション位置調整機能) の実装が完了しました。

**主要な成果**:
1. 設定UIの実装: スクロール可能な拡張ダイアログ
2. オフセット永続化: JSONファイルでの保存/読込
3. 描画ロジック対応: `image_type` パラメータによる柔軟なオフセット適用
4. 後方互換性: 既存機能を損なわない設計

**次のアクション**:
Requirement 1を実装することで、このオフセット機能が実際のサーモ/可視画像保存時に活用されます。
