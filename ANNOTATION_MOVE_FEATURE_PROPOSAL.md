# アノテーション移動機能 実装提案書

## 📅 提案日
2025年

## 🎯 機能概要

メイン画面に配置したアノテーションを移動させる機能を追加します。
2つの操作方法を提供し、ユーザーの好みや作業スタイルに応じて使い分けられるようにします。

## 🔧 実装する2つの操作方法

### 方法1: Ctrl + ドラッグ＆ドロップ

**操作フロー**:
1. Ctrlキーを押しながらアノテーションを左クリック
2. そのままドラッグして移動先まで移動
3. マウスボタンを離すと新しい位置に確定

**特徴**:
- ✅ 直感的で素早い操作
- ✅ 1アクションで移動完了
- ✅ リアルタイムプレビュー

### 方法2: モード切替方式

**操作フロー**:
1. メイン画面左上の矢印アイコンをクリックして「移動モード」をON
2. 移動したいアノテーションを左クリック → 半透明化して選択状態に
3. 移動先をクリック → アノテーションが新しい位置に移動＆確定
4. 矢印アイコンを再度クリックして移動モードをOFF（または自動OFF）

**特徴**:
- ✅ 正確な位置指定が可能
- ✅ 移動先を確認してから確定できる
- ✅ 誤操作防止

## 📋 詳細設計

### 1. 状態管理

新しい状態変数を追加：

```python
class OrthoImageAnnotationSystem:
    def __init__(self, root):
        # ... 既存の初期化 ...
        
        # アノテーション移動機能用の状態変数
        self.move_mode = False              # 移動モードのON/OFF
        self.moving_annotation = None       # 現在移動中のアノテーション
        self.move_start_pos = None          # ドラッグ開始位置（Ctrl+ドラッグ用）
        self.move_original_pos = None       # 元の位置（キャンセル用）
```

### 2. UI要素の追加

#### 矢印アイコンボタン

**配置位置**: メイン画面の画像表示エリア左上（キャンバス内にオーバーレイ）

**デザイン案**:
```
┌────────────────────────────────────┐
│ [↗] ← 移動モード切替ボタン          │
│                                    │
│     オルソ画像表示エリア            │
│                                    │
│                                    │
└────────────────────────────────────┘
```

**ボタン仕様**:
- アイコン: ↗ または ⬆ または 🔄
- トグルボタン（ON/OFF切替）
- ON時: 背景色をハイライト（例: 水色、緑色）
- サイズ: 40x40px程度

**実装方法**:
```python
# キャンバス上にボタンを配置
self.move_mode_button = tk.Button(
    self.canvas, 
    text="↗", 
    command=self.toggle_move_mode,
    width=2,
    height=1,
    relief=tk.RAISED
)
self.move_mode_button_window = self.canvas.create_window(
    10, 10,  # 左上から10pxの位置
    anchor=tk.NW,
    window=self.move_mode_button
)
```

### 3. イベントハンドリング

#### 既存イベントの拡張

**`on_canvas_click()`の拡張**:

```python
def on_canvas_click(self, event):
    """キャンバスクリック時の処理"""
    if self.current_image:
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        image_x = canvas_x / self.zoom_factor
        image_y = canvas_y / self.zoom_factor
        
        # 画像範囲内チェック
        if 0 <= image_x <= self.current_image.width and 0 <= image_y <= self.current_image.height:
            
            # 移動モード中の処理
            if self.move_mode:
                self.handle_move_mode_click(image_x, image_y)
                return
            
            # 通常モード: アノテーション追加
            self.add_annotation(image_x, image_y)
```

#### 新規イベントバインド

```python
# Ctrl + ドラッグ用イベント
self.canvas.bind("<Control-Button-1>", self.on_ctrl_click)
self.canvas.bind("<Control-B1-Motion>", self.on_ctrl_drag)
self.canvas.bind("<Control-ButtonRelease-1>", self.on_ctrl_release)

# Escキーでキャンセル
self.root.bind("<Escape>", self.cancel_move)
```

### 4. 主要メソッドの実装

#### 4.1 モード切替

```python
def toggle_move_mode(self):
    """移動モードのON/OFFを切り替え"""
    self.move_mode = not self.move_mode
    
    if self.move_mode:
        # 移動モードON
        self.move_mode_button.config(relief=tk.SUNKEN, bg="#90EE90")
        self.canvas.config(cursor="hand2")  # カーソルを手の形に
    else:
        # 移動モードOFF
        self.move_mode_button.config(relief=tk.RAISED, bg="SystemButtonFace")
        self.canvas.config(cursor="")
        # 選択中のアノテーションをクリア
        if self.moving_annotation:
            self.moving_annotation = None
            self.draw_annotations()
```

#### 4.2 最近接アノテーション検索

```python
def find_nearest_annotation(self, image_x, image_y, threshold=30):
    """指定座標から最も近いアノテーションを検索
    
    Args:
        image_x: 画像座標X
        image_y: 画像座標Y
        threshold: 検索範囲の閾値（ピクセル）
    
    Returns:
        最も近いアノテーション、または None
    """
    min_distance = float('inf')
    nearest_annotation = None
    
    for annotation in self.annotations:
        ann_x = annotation["x"]
        ann_y = annotation["y"]
        
        # ユークリッド距離を計算
        distance = math.sqrt((image_x - ann_x)**2 + (image_y - ann_y)**2)
        
        # 閾値内かつ最小距離を更新
        if distance < threshold / self.zoom_factor and distance < min_distance:
            min_distance = distance
            nearest_annotation = annotation
    
    return nearest_annotation
```

#### 4.3 Ctrl + ドラッグ処理

```python
def on_ctrl_click(self, event):
    """Ctrl + クリック時の処理（ドラッグ開始）"""
    if not self.current_image:
        return
    
    canvas_x = self.canvas.canvasx(event.x)
    canvas_y = self.canvas.canvasy(event.y)
    
    image_x = canvas_x / self.zoom_factor
    image_y = canvas_y / self.zoom_factor
    
    # 最も近いアノテーションを検索
    annotation = self.find_nearest_annotation(image_x, image_y)
    
    if annotation:
        self.moving_annotation = annotation
        self.move_start_pos = (image_x, image_y)
        self.move_original_pos = (annotation["x"], annotation["y"])
        self.canvas.config(cursor="fleur")  # 移動カーソル

def on_ctrl_drag(self, event):
    """Ctrl + ドラッグ中の処理（リアルタイム更新）"""
    if not self.moving_annotation or not self.move_start_pos:
        return
    
    canvas_x = self.canvas.canvasx(event.x)
    canvas_y = self.canvas.canvasy(event.y)
    
    image_x = canvas_x / self.zoom_factor
    image_y = canvas_y / self.zoom_factor
    
    # 移動量を計算
    dx = image_x - self.move_start_pos[0]
    dy = image_y - self.move_start_pos[1]
    
    # アノテーション位置を更新
    self.moving_annotation["x"] = self.move_original_pos[0] + dx
    self.moving_annotation["y"] = self.move_original_pos[1] + dy
    
    # 画像範囲内にクランプ
    self.moving_annotation["x"] = max(0, min(self.current_image.width, self.moving_annotation["x"]))
    self.moving_annotation["y"] = max(0, min(self.current_image.height, self.moving_annotation["y"]))
    
    # 再描画
    self.draw_annotations()

def on_ctrl_release(self, event):
    """Ctrl + ドラッグ終了時の処理（確定）"""
    if self.moving_annotation:
        # ログ出力
        print(f"アノテーションID {self.moving_annotation['id']} を移動: "
              f"{self.move_original_pos} → ({self.moving_annotation['x']:.1f}, {self.moving_annotation['y']:.1f})")
        
        # テーブルを更新
        self.update_table()
        
        # 状態をリセット
        self.moving_annotation = None
        self.move_start_pos = None
        self.move_original_pos = None
        self.canvas.config(cursor="")
```

#### 4.4 モード切替方式処理

```python
def handle_move_mode_click(self, image_x, image_y):
    """移動モード中のクリック処理"""
    
    if self.moving_annotation is None:
        # 1回目のクリック: アノテーションを選択
        annotation = self.find_nearest_annotation(image_x, image_y)
        
        if annotation:
            self.moving_annotation = annotation
            self.move_original_pos = (annotation["x"], annotation["y"])
            # 半透明化して再描画
            self.draw_annotations()
        else:
            messagebox.showinfo("情報", "アノテーションが見つかりません。")
    
    else:
        # 2回目のクリック: 選択中のアノテーションを移動
        self.moving_annotation["x"] = image_x
        self.moving_annotation["y"] = image_y
        
        # 画像範囲内にクランプ
        self.moving_annotation["x"] = max(0, min(self.current_image.width, self.moving_annotation["x"]))
        self.moving_annotation["y"] = max(0, min(self.current_image.height, self.moving_annotation["y"]))
        
        # ログ出力
        print(f"アノテーションID {self.moving_annotation['id']} を移動: "
              f"{self.move_original_pos} → ({image_x:.1f}, {image_y:.1f})")
        
        # テーブル更新
        self.update_table()
        
        # 選択状態をクリア
        self.moving_annotation = None
        self.move_original_pos = None
        
        # 再描画（通常状態に戻す）
        self.draw_annotations()
```

#### 4.5 キャンセル処理

```python
def cancel_move(self, event=None):
    """移動操作をキャンセル"""
    if self.moving_annotation and self.move_original_pos:
        # 元の位置に戻す
        self.moving_annotation["x"] = self.move_original_pos[0]
        self.moving_annotation["y"] = self.move_original_pos[1]
        
        # 状態をリセット
        self.moving_annotation = None
        self.move_original_pos = None
        self.move_start_pos = None
        
        # カーソルを元に戻す
        self.canvas.config(cursor="hand2" if self.move_mode else "")
        
        # 再描画
        self.draw_annotations()
        
        messagebox.showinfo("キャンセル", "移動操作をキャンセルしました。")
```

#### 4.6 半透明描画

```python
def draw_annotations(self):
    """アノテーションを描画（半透明対応）"""
    self.canvas_icon_refs.clear()
    for annotation in self.annotations:
        self.canvas.delete(f"annotation_{annotation['id']}")
        x = annotation["x"] * self.zoom_factor
        y = annotation["y"] * self.zoom_factor
        defect_type = annotation.get("defect_type")
        color = self.defect_types.get(defect_type, "#FF0000")
        
        # 移動中のアノテーションは半透明化
        is_moving = (self.moving_annotation and 
                     annotation['id'] == self.moving_annotation['id'])
        
        icon_size = max(24, int(self.annotation_default_icon_size * self.zoom_factor))
        tk_icon = self.get_tk_icon(defect_type, icon_size, alpha=0.5 if is_moving else 1.0)
        
        if tk_icon:
            self.canvas.create_image(
                x, y,
                image=tk_icon,
                anchor=tk.CENTER,
                tags=f"annotation_{annotation['id']}"
            )
            self.canvas_icon_refs.append(tk_icon)
            
            label_offset = (tk_icon.height() / 2) + 12 * self.zoom_factor
            # 移動中はIDテキストも半透明化
            self.draw_id_text(x, y - label_offset, color, annotation['id'], 
                            stipple='gray50' if is_moving else None)
            continue
        
        # ... 既存の形状描画処理 ...
```

#### 4.7 アイコン取得（透明度対応）

```python
def get_tk_icon(self, defect_type, size, alpha=1.0):
    """透明度を指定してTkinterアイコンを取得
    
    Args:
        defect_type: 不良分類
        size: アイコンサイズ
        alpha: 透明度（0.0～1.0）
    """
    cache_key = (defect_type, size, alpha)
    
    if cache_key in self.annotation_icon_tk_cache:
        return self.annotation_icon_tk_cache[cache_key]
    
    base_icon = self.load_annotation_icon(defect_type)
    if base_icon is None:
        return None
    
    # リサイズ
    icon = base_icon.resize((size, size), Image.Resampling.LANCZOS)
    
    # 透明度適用
    if alpha < 1.0:
        icon = icon.copy()
        icon.putalpha(int(255 * alpha))
    
    # Tkinter形式に変換
    tk_icon = ImageTk.PhotoImage(icon)
    self.annotation_icon_tk_cache[cache_key] = tk_icon
    
    return tk_icon
```

## 🎨 UI/UX設計

### ビジュアルフィードバック

#### 状態別の視覚表現

| 状態 | カーソル | アノテーション | ボタン |
|------|---------|--------------|--------|
| 通常モード | デフォルト | 100%不透明 | 通常 |
| 移動モードON | 手のひら | 100%不透明 | ハイライト |
| アノテーション選択中 | 手のひら | 50%半透明 | ハイライト |
| Ctrl+ドラッグ中 | 移動カーソル | 50%半透明 | - |

### ステータス表示（オプション）

画面下部にステータスバーを追加することも検討：

```
[通常モード] 画像サイズ: 4000x3000  アノテーション数: 15
```

```
[移動モード] アノテーションを選択してください
```

```
[移動中] ID 5 を移動中... Escでキャンセル
```

## 🔒 制約事項とエラーハンドリング

### 1. 移動範囲の制限

```python
# 画像範囲外に移動させない
annotation["x"] = max(0, min(self.current_image.width, annotation["x"]))
annotation["y"] = max(0, min(self.current_image.height, annotation["y"]))
```

### 2. 移動モード中の制御

- 移動モード中は新規アノテーション追加を無効化
- ダブルクリック編集は引き続き有効
- 右クリック削除は引き続き有効（要検討）

### 3. エラーケース

- アノテーションが見つからない → 情報メッセージ表示
- 画像未読み込み → 操作無効化
- 移動先が範囲外 → 自動的に範囲内に補正

## 📊 データ管理

### 移動履歴のログ

```python
# ログ出力例
print(f"[{datetime.now()}] アノテーション移動: ID={ann_id}, "
      f"元位置=({old_x:.1f}, {old_y:.1f}), "
      f"新位置=({new_x:.1f}, {new_y:.1f})")
```

### 保存データ形式

既存のJSONフォーマットをそのまま使用（x, y座標のみ更新）

```json
{
  "id": 1,
  "x": 1234.5,
  "y": 678.9,
  "defect_type": "ホットスポット",
  ...
}
```

## 🧪 テスト計画

### 機能テスト

1. **Ctrl + ドラッグテスト**
   - [ ] Ctrl+クリックで選択できる
   - [ ] ドラッグ中にリアルタイム更新される
   - [ ] マウスリリースで確定される
   - [ ] 複数アノテーションを連続移動できる

2. **モード切替テスト**
   - [ ] 矢印ボタンで移動モードをON/OFFできる
   - [ ] 1回目クリックで選択＆半透明化される
   - [ ] 2回目クリックで新位置に移動＆確定される
   - [ ] 選択後にEscでキャンセルできる

3. **制御テスト**
   - [ ] 移動モード中は新規アノテーション追加されない
   - [ ] 画像範囲外に移動しようとすると範囲内に補正される
   - [ ] ズーム状態でも正しく動作する

4. **データ整合性テスト**
   - [ ] 移動後のデータが正しく保存される
   - [ ] 保存→読み込み後も位置が保持される
   - [ ] テーブル表示が正しく更新される

### パフォーマンステスト

- 100個以上のアノテーションがある場合の動作確認
- ドラッグ中の描画パフォーマンス確認

## 📝 実装の優先順位

### Phase 1: 基本機能（High Priority）
1. 状態変数の追加
2. 矢印ボタンの追加
3. `find_nearest_annotation()` 実装
4. Ctrl + ドラッグ機能実装
5. モード切替機能実装

### Phase 2: UX改善（Medium Priority）
6. 半透明表示
7. カーソル変更
8. Escキャンセル機能
9. 移動モード中のアノテーション追加無効化

### Phase 3: 仕上げ（Low Priority）
10. ステータス表示
11. ログ出力
12. エラーハンドリング強化
13. 包括的なテスト

## 💡 将来の拡張案

- **複数選択移動**: 複数のアノテーションを一括移動
- **グリッドスナップ**: 指定したグリッドに吸着
- **元に戻す/やり直し**: Ctrl+Z / Ctrl+Yでアンドゥ・リドゥ
- **移動アニメーション**: スムーズな移動アニメーション
- **ショートカットキー**: テンキーで微調整移動

## 📚 関連ファイル

- **メインプログラム**: `ortho_annotation_system_v7.py`
- **実装TODO**: 上記のTodoリストを参照

---

**実装準備完了**

全ての設計が完了しました。実装を進めますか？
