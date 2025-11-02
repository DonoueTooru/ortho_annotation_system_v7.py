# Windows環境でのSVG→PNG変換ガイド

## ❌ 発生したエラー

```
OSError: no library called "cairo-2" was found
```

### 原因
`cairosvg`はWindowsで動作させるために**Cairo**というネイティブライブラリが必要ですが、標準ではインストールされていません。

## ✅ 解決方法（3つの選択肢）

---

## 方法1: 代替Pythonスクリプト使用（推奨）

### ステップ1: 必要なライブラリをインストール

```bash
pip install svglib reportlab
```

### ステップ2: 簡易版スクリプトを実行

```bash
python convert_svg_to_png_simple.py
```

このスクリプトは`svglib`と`reportlab`を使用し、Windowsで問題なく動作します。

**メリット:**
- ✅ Windows完全対応
- ✅ 追加のシステムライブラリ不要
- ✅ 簡単なインストール

**デメリット:**
- ⚠️ SVGの複雑な機能は一部対応していない可能性

---

## 方法2: オンライン変換ツール使用（最も簡単）

SVGファイルが少ない場合、オンラインツールが最も簡単です。

### 推奨サイト:

#### 1. **CloudConvert**
- URL: https://cloudconvert.com/svg-to-png
- 特徴: 一括変換対応、高品質、無料

#### 2. **Convertio**
- URL: https://convertio.co/ja/svg-png/
- 特徴: ドラッグ&ドロップ、簡単操作

#### 3. **Vector Magic**
- URL: https://vectormagic.com/
- 特徴: 高品質、トレース機能付き

### 手順:
1. SVGファイルをアップロード
2. PNG形式を選択
3. サイズを256x256に指定（可能な場合）
4. 変換＆ダウンロード
5. ダウンロードしたPNGを `アノテーション画像フォルダ` に配置

---

## 方法3: Inkscape使用（本格的）

### ステップ1: Inkscapeをインストール

**ダウンロード:** https://inkscape.org/release/

Windows用インストーラーをダウンロードしてインストール。

### ステップ2: コマンドラインで一括変換

Inkscapeをインストール後、コマンドプロンプトで:

```bash
cd "C:\Users\ndono\Documents\ドローンプロジェクト('◇')ゞ\アノテーション画像フォルダ"

# 各SVGファイルを変換
for %f in (*.svg) do inkscape "%f" --export-type="png" --export-width=256 --export-height=256
```

または、PowerShellの場合:

```powershell
cd "C:\Users\ndono\Documents\ドローンプロジェクト('◇')ゞ\アノテーション画像フォルダ"

Get-ChildItem -Filter *.svg | ForEach-Object {
    inkscape $_.FullName --export-type="png" --export-width=256 --export-height=256
}
```

**メリット:**
- ✅ 高品質な変換
- ✅ 複雑なSVG完全対応
- ✅ コマンドライン自動化可能

**デメリット:**
- ⚠️ 大きなソフトウェアのインストールが必要（約200MB）

---

## 方法4: 手動で各SVGを開いて保存（少数の場合）

SVGファイルが数個だけの場合:

### ステップ1: ペイント3Dまたはブラウザで開く

1. SVGファイルを右クリック
2. 「プログラムから開く」→「ペイント3D」または「ブラウザ」を選択

### ステップ2: スクリーンショット＋トリミング

1. ブラウザでSVGを開く（Ctrl+Oで開く）
2. ズームで適切なサイズに調整
3. Snipping Tool（Windows標準）でスクリーンショット
4. ペイントやPhoto editorでトリミング＋リサイズ（256x256）
5. PNGとして保存

---

## 📋 各方法の比較

| 方法 | 難易度 | 時間 | 品質 | 推奨度 |
|------|--------|------|------|--------|
| **代替Pythonスクリプト** | ⭐⭐ | 5分 | 高 | ⭐⭐⭐⭐⭐ |
| **オンライン変換** | ⭐ | 10分 | 高 | ⭐⭐⭐⭐ |
| **Inkscape** | ⭐⭐⭐ | 20分 | 最高 | ⭐⭐⭐ |
| **手動変換** | ⭐ | 30分+ | 中 | ⭐⭐ |

---

## 🚀 推奨手順（初心者向け）

### 最速・最簡単:

```bash
# 1. 必要なライブラリをインストール
pip install svglib reportlab

# 2. 簡易版スクリプトを実行
python convert_svg_to_png_simple.py
```

もしエラーが出る場合:
→ **オンライン変換ツール**を使用（方法2）

---

## 🔧 トラブルシューティング

### Q1: `pip install svglib reportlab` がエラーになる

**A1:** Pythonとpipのバージョンを確認:
```bash
python --version
pip --version
```

Python 3.7以上が必要です。古い場合は最新版をインストール:
https://www.python.org/downloads/

### Q2: スクリプトが「フォルダが見つからない」と言う

**A2:** スクリプトと同じフォルダに `アノテーション画像フォルダ` を作成:

```bash
# コマンドプロンプトで
mkdir "アノテーション画像フォルダ"
```

その後、SVGファイルをこのフォルダに配置。

### Q3: 変換されたPNGが透過していない

**A3:** 元のSVGに透過設定がない可能性があります。
- ペイントソフトで背景を透明化
- または、`test_icon_loading.py`で新規アイコンを生成

---

## 💡 代替案: テストアイコンを使用

SVGの変換が面倒な場合、テスト用アイコンを生成できます:

```bash
python test_icon_loading.py
```

これで6種類のデフォルトアイコン（PNG形式）が自動生成されます。

---

## 📝 まとめ

**最も簡単な方法:**

1️⃣ SVGファイルが少ない（1-10個）
   → **オンライン変換ツール**使用

2️⃣ SVGファイルが多い（10個以上）
   → **代替Pythonスクリプト**使用
   ```bash
   pip install svglib reportlab
   python convert_svg_to_png_simple.py
   ```

3️⃣ SVGファイルがない、または変換が面倒
   → **テストアイコン生成**
   ```bash
   python test_icon_loading.py
   ```

---

**質問があれば、お気軽にお聞きください！** ('◇')ゞ
