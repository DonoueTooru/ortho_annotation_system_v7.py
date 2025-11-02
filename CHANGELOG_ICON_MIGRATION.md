# アイコンシステム移行 変更履歴

## 📅 2025-11-02: SVG→PNG/JPG移行完了

### ✨ 主な変更

#### 1. 依存関係の削減
- ❌ **削除**: `cairosvg` ライブラリへの依存
- ✅ **継続**: `Pillow (PIL)` のみ使用（標準的なライブラリ）

#### 2. アイコン読み込みの変更

**変更前（SVG + cairosvg）:**
```python
import cairosvg
from io import BytesIO

png_bytes = cairosvg.svg2png(url=svg_path, output_width=256)
image = Image.open(BytesIO(png_bytes)).convert("RGBA")
```

**変更後（PNG/JPG直接読み込み）:**
```python
# Pillowで直接読み込み
image = Image.open(png_path).convert("RGBA")

# 必要に応じて標準サイズにリサイズ
if image.size != (256, 256):
    image = image.resize((256, 256), Image.Resampling.LANCZOS)
```

#### 3. 対応フォーマット

- **PNG** (推奨・透過背景対応)
- **JPG / JPEG** (フォールバック)
- ~~**SVG**~~ (非対応に変更)

優先順位: PNG → JPG → JPEG

#### 4. ファイル検索の改善

```python
def get_annotation_icon_path(self, defect_type):
    # PNG優先
    png_path = os.path.join(self.annotation_icon_dir, f"{sanitized}.png")
    if os.path.exists(png_path):
        return png_path
    
    # JPGフォールバック
    jpg_path = os.path.join(self.annotation_icon_dir, f"{sanitized}.jpg")
    if os.path.exists(jpg_path):
        return jpg_path
    
    # JPEGフォールバック
    jpeg_path = os.path.join(self.annotation_icon_dir, f"{sanitized}.jpeg")
    if os.path.exists(jpeg_path):
        return jpeg_path
    
    # デフォルトはPNGパス（エラー表示用）
    return png_path
```

#### 5. エラーメッセージの更新

**変更前:**
```
アノテーション用SVGアイコンを読み込めませんでした。
フォルダ『アノテーション画像フォルダ』と cairosvg のインストール状況を確認してください。
```

**変更後:**
```
アノテーション用アイコンを読み込めませんでした。
フォルダ『アノテーション画像フォルダ』とPNG/JPG形式のアイコンファイルを確認してください。

ヒント: convert_svg_to_png.py スクリプトでSVGをPNGに変換できます。
```

### 📦 新規追加ファイル

#### `convert_svg_to_png.py`
既存のSVGアイコンをPNG形式に一括変換するスクリプト

**機能:**
- `アノテーション画像フォルダ` 内の全SVGファイルを自動検出
- 256x256ピクセルのPNGに変換
- 元のSVGファイルは保持（削除しない）

**使用方法:**
```bash
python convert_svg_to_png.py
```

#### `test_icon_loading.py`
テスト用のシンプルなPNGアイコンを生成するスクリプト

**機能:**
- デフォルトの不具合分類（6種類）用アイコン生成
- 色分けされた円形アイコン
- テキストラベル付き

**使用方法:**
```bash
python test_icon_loading.py
```

#### `ICON_MIGRATION_README.md`
詳細な移行ガイドと使用方法

#### `CHANGELOG_ICON_MIGRATION.md`
本ファイル（変更履歴）

### 🔧 修正されたコード箇所

#### `ortho_annotation_system_v7.py`

**変更箇所:**
1. **Line 19-24**: cairosvgインポートを削除
2. **Line 2204-2209**: `get_annotation_icon_path()` - PNG/JPG対応
3. **Line 2211-2234**: `load_annotation_icon()` - Pillow直接読み込みに変更
4. **Line 2190-2196**: `initialize_annotation_icons()` - 警告メッセージ更新
5. **Line 2236-2247**: `_register_missing_icon()` - エラーメッセージ更新

### 📊 パフォーマンス比較

| 項目 | SVG + cairosvg | PNG直接読み込み |
|------|----------------|------------------|
| **依存ライブラリ** | Pillow + cairosvg | Pillowのみ |
| **初回読み込み** | 中速（変換あり） | 高速（変換なし） |
| **2回目以降** | 高速（キャッシュ） | 高速（キャッシュ） |
| **メモリ使用量** | 低 | 中（PNG展開） |
| **ファイルサイズ** | 小（1-10KB） | 中（5-50KB） |
| **互換性** | Linux推奨 | 全OS対応 |

### ✅ テスト結果

#### 実施したテスト:
1. ✅ 構文チェック（`py_compile`）
2. ✅ テストアイコン生成（6種類）
3. ✅ ファイル検索（PNG優先順位）
4. ✅ エラーハンドリング（ファイル不在時）
5. ✅ フォールバック機能（十字など）

#### 生成されたテストアイコン:
```
アノテーション画像フォルダ/
├── ホットスポット.png (1.5 KB)
├── クラスタ異常.png (1.6 KB)
├── 破損.png (1.6 KB)
├── ストリング異常.png (1.5 KB)
├── 系統異常.png (1.6 KB)
└── 影.png (1.5 KB)
```

### 🎯 メリット

1. **依存関係の削減**: cairosvgが不要に
2. **パフォーマンス向上**: PNG直接読み込みは高速
3. **互換性向上**: Windows/Mac/Linux完全対応
4. **メンテナンス性**: Pillowのみでシンプル
5. **エラー処理**: より明確なエラーメッセージ

### ⚠️ 注意点

1. **既存プロジェクト**: SVGアイコンをPNGに変換が必要
2. **ファイルサイズ**: PNG/JPGはSVGより大きい
3. **スケーラビリティ**: PNGは拡大時に劣化（256x256で十分）

### 🔄 移行手順

既にSVGアイコンを使用している場合:

```bash
# Step 1: SVG→PNG変換
python convert_svg_to_png.py

# Step 2: アプリ起動
python ortho_annotation_system_v7.py
```

新規プロジェクトの場合:

```bash
# Step 1: テストアイコン生成
python test_icon_loading.py

# Step 2: アプリ起動
python ortho_annotation_system_v7.py
```

### 📝 今後の改善案

- [ ] WebP形式のサポート（さらに軽量化）
- [ ] アイコンのホットリロード機能
- [ ] アイコンエディタ統合
- [ ] カスタムアイコンパックのインポート

### 🎉 完了タスク

- [x] cairosvg依存の削除
- [x] Pillow直接読み込みへの変更
- [x] PNG/JPG対応
- [x] エラーハンドリング改善
- [x] 警告メッセージ更新
- [x] 変換スクリプト作成
- [x] テストスクリプト作成
- [x] ドキュメント作成
- [x] 動作確認

---

**担当者**: Claude Code Assistant  
**完了日**: 2025-11-02  
**ステータス**: ✅ 完了
