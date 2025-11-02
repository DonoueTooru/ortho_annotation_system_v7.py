# アイコンシステム移行ガイド

## 📋 変更内容

SVGアイコン + cairosvg から **PNG/JPG直接読み込み（Pillowのみ）** に変更しました。

### ✅ 完了した変更

1. ✅ cairosvg依存の完全削除
2. ✅ Pillow直接読み込みへの変更
3. ✅ PNG/JPG/JPEG対応（優先順位: PNG → JPG → JPEG）
4. ✅ 自動リサイズ機能（256x256標準サイズ）
5. ✅ エラーハンドリングとフォールバック改善
6. ✅ 警告メッセージの更新

## 🚀 使用方法

### 方法1: 既存SVGをPNGに変換（推奨）

既にSVGアイコンがある場合:

```bash
cd /home/user/webapp
python convert_svg_to_png.py
```

このスクリプトが:
- `アノテーション画像フォルダ` 内の全SVGファイルを検索
- 自動的にPNG形式（256x256）に変換
- 元のSVGファイルは削除されません

### 方法2: テスト用アイコンを生成

テスト用のシンプルなPNGアイコンを生成:

```bash
cd /home/user/webapp
python test_icon_loading.py
```

デフォルトの不具合分類（6種類）のアイコンが自動生成されます。

### 方法3: 手動でPNG/JPGを配置

`アノテーション画像フォルダ` に以下の形式でアイコンを配置:

- `ホットスポット.png`
- `クラスタ異常.png`
- `破損.png`
- `ストリング異常.png`
- `系統異常.png`
- `影.png`

**推奨仕様:**
- 形式: PNG（透過背景推奨）またはJPG/JPEG
- サイズ: 256x256ピクセル以上（自動リサイズ対応）
- 透過: アルファチャンネル対応（RGBA）

## 📁 ファイル構造

```
/home/user/webapp/
├── ortho_annotation_system_v7.py  # メインアプリ（修正済み）
├── convert_svg_to_png.py          # SVG→PNG変換スクリプト
├── test_icon_loading.py           # テストアイコン生成スクリプト
└── アノテーション画像フォルダ/
    ├── ホットスポット.png
    ├── クラスタ異常.png
    ├── 破損.png
    ├── ストリング異常.png
    ├── 系統異常.png
    └── 影.png
```

## 🔧 技術詳細

### 変更されたメソッド

#### `get_annotation_icon_path(defect_type)`
```python
# 変更前: .svg固定
return os.path.join(self.annotation_icon_dir, f"{sanitized}.svg")

# 変更後: PNG優先、JPG/JPEGフォールバック
png_path = os.path.join(self.annotation_icon_dir, f"{sanitized}.png")
if os.path.exists(png_path):
    return png_path
jpg_path = os.path.join(self.annotation_icon_dir, f"{sanitized}.jpg")
if os.path.exists(jpg_path):
    return jpg_path
# ...
```

#### `load_annotation_icon(defect_type)`
```python
# 変更前: cairosvg経由でSVG→PNG変換
png_bytes = cairosvg.svg2png(url=path, output_width=256)
image = Image.open(BytesIO(png_bytes)).convert("RGBA")

# 変更後: Pillow直接読み込み
image = Image.open(path).convert("RGBA")
if image.size != (256, 256):
    image = image.resize((256, 256), Image.Resampling.LANCZOS)
```

### エラーハンドリング

1. **ファイル不在**: フォールバック図形（十字、矢印など）を表示
2. **読み込み失敗**: エラーメッセージとフォールバック
3. **フォーマット不正**: 自動的にRGBA変換を試行

### キャッシュ機能

- 読み込んだアイコンは `annotation_icon_cache` にキャッシュ
- 同じアイコンの再読み込みを防止
- メモリ効率の向上

## 🎨 カスタムアイコンの追加

新しい不具合分類を追加する場合:

1. メインアプリで新しい不具合分類を定義
2. 対応するPNG/JPGファイルを `アノテーション画像フォルダ` に配置
3. ファイル名は不具合分類名と一致させる（例: `新分類.png`）

## ⚠️ 注意事項

### 互換性
- **Pillow (PIL)** のみ必要（標準的なPythonライブラリ）
- **cairosvgは不要**（削除しても問題なし）
- Windows/Mac/Linux完全対応

### パフォーマンス
- PNG直接読み込みはSVG変換より高速
- キャッシュ機能により2回目以降はさらに高速
- メモリ使用量は若干増加（256x256ピクセル × アイコン数）

### ファイルサイズ
- PNG: 通常5-50KB（透過込み）
- JPG: 通常3-30KB（透過なし）
- SVG: 通常1-10KB（ベクター形式）

**トレードオフ**: ファイルサイズは増えるが、依存関係とパフォーマンスが改善

## 🐛 トラブルシューティング

### アイコンが表示されない
1. `アノテーション画像フォルダ` の存在を確認
2. PNG/JPGファイルの存在を確認
3. ファイル名が不具合分類名と一致するか確認
4. ファイルの読み取り権限を確認

### 警告メッセージが出る
```
アノテーション用アイコンを読み込めませんでした。
フォルダ『アノテーション画像フォルダ』とPNG/JPG形式のアイコンファイルを確認してください。
```

**解決方法**:
- `test_icon_loading.py` を実行してテストアイコンを生成
- または `convert_svg_to_png.py` でSVGを変換

### 画像が歪む
- 元画像のアスペクト比が1:1でない場合、自動リサイズで歪む可能性
- **推奨**: 正方形（1:1）の画像を使用

## 📚 参考情報

### Pillow (PIL) ドキュメント
https://pillow.readthedocs.io/

### 対応画像形式
- PNG (推奨・透過対応)
- JPEG/JPG
- BMP
- GIF
- TIFF

## 🎉 完了

SVG→PNG/JPG移行が完了しました！
依存関係がシンプルになり、より安定した動作が期待できます。

---

*最終更新: 2025-11-02*
