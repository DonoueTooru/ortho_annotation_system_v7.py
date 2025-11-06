# メイン画面操作系改善計画

## 📋 改善内容

### 現在の問題点
- ❌ マウスホイールがズーム専用（スクロールできない）
- ❌ ズーム倍率の細かい調整が難しい
- ❌ 現在のズーム倍率が分からない

### 改善後
- ✅ ボタンクリックで段階的にズーム
- ✅ コンボボックスで任意の倍率を選択
- ✅ マウスホイールで縦横スクロール可能
- ✅ 現在の倍率を常に表示

---

## 🎯 実装Todoリスト

### 🔴 高優先度（必須）

#### 1. 現状調査
- [x] `on_mouse_wheel` メソッドの現在の動作を確認
- [ ] `zoom_factor` 変数の使用箇所を特定
- [ ] `display_image` メソッドとの連携を確認

#### 2. UI要素の追加
```python
# コントロールパネルに追加する要素:
# - ズームアウトボタン（🔍-）
# - ズームインボタン（🔍+）
# - 倍率表示ラベル
# - 倍率選択コンボボックス
```

**配置場所**: 既存のコントロールパネル（`control_frame`）

#### 3. 倍率オプションの定義
```python
zoom_options = [
    ("25%", 0.25),
    ("50%", 0.5),
    ("75%", 0.75),
    ("100%", 1.0),
    ("125%", 1.25),
    ("150%", 1.5),
    ("200%", 2.0),
    ("300%", 3.0),
    ("400%", 4.0),
    ("500%", 5.0),
]
```

#### 4. ズームボタン処理
```python
def zoom_in(self):
    """ズームイン（1.25倍ずつ拡大）"""
    new_zoom = self.zoom_factor * 1.25
    new_zoom = min(new_zoom, 5.0)  # 最大500%
    self.set_zoom_factor(new_zoom)

def zoom_out(self):
    """ズームアウト（0.8倍ずつ縮小）"""
    new_zoom = self.zoom_factor * 0.8
    new_zoom = max(new_zoom, 0.1)  # 最小10%
    self.set_zoom_factor(new_zoom)

def set_zoom_factor(self, new_zoom):
    """ズーム倍率を設定して画像を再描画"""
    self.zoom_factor = new_zoom
    self.display_image()
    self.update_zoom_display()
```

#### 5. コンボボックス処理
```python
def on_zoom_combo_change(self, event=None):
    """倍率コンボボックス変更時"""
    selected = self.zoom_combo.get()
    # "100%" → 1.0 に変換
    for label, value in self.zoom_options:
        if label == selected:
            self.set_zoom_factor(value)
            break
```

#### 6. 倍率表示更新
```python
def update_zoom_display(self):
    """現在の倍率をコンボボックスに反映"""
    current_percent = f"{int(self.zoom_factor * 100)}%"
    
    # リストにある値なら選択、なければカスタム表示
    found = False
    for label, value in self.zoom_options:
        if abs(value - self.zoom_factor) < 0.01:
            self.zoom_combo.set(label)
            found = True
            break
    
    if not found:
        self.zoom_combo.set(current_percent)
    
    # ボタンの有効/無効制御
    if self.zoom_factor >= 5.0:
        self.zoom_in_button.state(['disabled'])
    else:
        self.zoom_in_button.state(['!disabled'])
    
    if self.zoom_factor <= 0.1:
        self.zoom_out_button.state(['disabled'])
    else:
        self.zoom_out_button.state(['!disabled'])
```

#### 7. マウスホイール→スクロール変更
```python
def on_mouse_wheel(self, event):
    """マウスホイールでスクロール（縦横対応）"""
    
    # Shiftキー押下で横スクロール
    if event.state & 0x1:  # Shift押下
        # 横スクロール
        scroll_amount = -1 if event.delta > 0 else 1
        self.canvas.xview_scroll(scroll_amount, "units")
    else:
        # 縦スクロール
        scroll_amount = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(scroll_amount, "units")
```

#### 8-9. スクロール機能実装
```python
# Windows/Mac対応
def on_mouse_wheel_vertical(self, event):
    """縦スクロール（Shift無し）"""
    if event.num == 4 or event.delta > 0:
        self.canvas.yview_scroll(-1, "units")
    elif event.num == 5 or event.delta < 0:
        self.canvas.yview_scroll(1, "units")

def on_mouse_wheel_horizontal(self, event):
    """横スクロール（Shift押下時）"""
    if event.num == 4 or event.delta > 0:
        self.canvas.xview_scroll(-1, "units")
    elif event.num == 5 or event.delta < 0:
        self.canvas.xview_scroll(1, "units")

# イベントバインド変更
# 既存: self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
# 新規:
self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
self.canvas.bind("<Shift-MouseWheel>", self.on_mouse_wheel)
```

---

### 🟡 中優先度（推奨）

#### 10. スクロール速度調整
```python
# スクロール量を調整可能にする
self.scroll_speed = 3  # デフォルト: 3 units

def on_mouse_wheel(self, event):
    if event.state & 0x1:  # Shift
        scroll_amount = -self.scroll_speed if event.delta > 0 else self.scroll_speed
        self.canvas.xview_scroll(scroll_amount, "units")
    else:
        scroll_amount = -self.scroll_speed if event.delta > 0 else self.scroll_speed
        self.canvas.yview_scroll(scroll_amount, "units")
```

#### 11. ボタン有効/無効制御
上記の`update_zoom_display()`に実装済み

#### 12. ズーム時の中心位置維持
```python
def set_zoom_factor(self, new_zoom, keep_center=True):
    """ズーム倍率を設定（中心位置維持オプション）"""
    if keep_center and self.canvas_image:
        # 現在の表示中心座標を取得
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # スクロール位置から中心座標を計算
        x_scroll = self.canvas.xview()[0]
        y_scroll = self.canvas.yview()[0]
        
        center_x = x_scroll + (canvas_width / 2) / self.zoom_factor
        center_y = y_scroll + (canvas_height / 2) / self.zoom_factor
    
    old_zoom = self.zoom_factor
    self.zoom_factor = new_zoom
    self.display_image()
    
    if keep_center and self.canvas_image:
        # 新しいズームで中心を再計算してスクロール
        new_center_x = center_x * self.zoom_factor
        new_center_y = center_y * self.zoom_factor
        
        # スクロール位置を調整
        self.canvas.xview_moveto((new_center_x - canvas_width / 2) / (self.current_image.width * self.zoom_factor))
        self.canvas.yview_moveto((new_center_y - canvas_height / 2) / (self.current_image.height * self.zoom_factor))
    
    self.update_zoom_display()
```

---

### 🟢 低優先度（オプション）

#### 14. キーボードショートカット
```python
def setup_keyboard_shortcuts(self):
    """キーボードショートカットを設定"""
    self.root.bind("<Control-plus>", lambda e: self.zoom_in())
    self.root.bind("<Control-equal>", lambda e: self.zoom_in())  # Shift無し+でも対応
    self.root.bind("<Control-minus>", lambda e: self.zoom_out())
    self.root.bind("<Control-0>", lambda e: self.set_zoom_factor(1.0))  # 100%にリセット
```

---

## 🎨 UI配置案

### 現在のレイアウト
```
[画像選択] [WebODMフォルダ選択] [画像リセット] [保存] [中止] [色設定]
[全体×1.0] [サーモ×1.0] [可視×1.0]
```

### 改善後のレイアウト
```
[画像選択] [WebODMフォルダ選択] [画像リセット] [保存] [中止] [色設定]
[全体×1.0] [サーモ×1.0] [可視×1.0] | [🔍-] [倍率: 100% ▼] [🔍+]
```

**または、別フレームに配置:**
```
[画像選択] [WebODMフォルダ選択] [画像リセット] [保存] [中止] [色設定]
[全体×1.0] [サーモ×1.0] [可視×1.0]

[表示倍率] [🔍-] [25%|50%|75%|100%|150%|200%|300% ▼] [🔍+]
```

---

## 🔧 実装順序（推奨）

### Phase 1: ズームUI追加（30分）
1. ボタンとコンボボックスのUI追加
2. zoom_in, zoom_out メソッド実装
3. on_zoom_combo_change 実装
4. update_zoom_display 実装

### Phase 2: スクロール変更（20分）
5. on_mouse_wheel をスクロールに変更
6. 縦横スクロール対応
7. スクロール速度調整

### Phase 3: 微調整（15分）
8. ボタン有効/無効制御
9. ズーム時の中心維持（オプション）
10. 動作テスト

### Phase 4: 追加機能（オプション）
11. キーボードショートカット
12. 設定の保存/復元

---

## 🧪 テストチェックリスト

### ズーム機能
- [ ] ズームインボタンで拡大できるか
- [ ] ズームアウトボタンで縮小できるか
- [ ] コンボボックスで倍率を変更できるか
- [ ] 現在の倍率が正しく表示されるか
- [ ] 最小/最大倍率でボタンが無効になるか

### スクロール機能
- [ ] マウスホイールで縦スクロールできるか
- [ ] Shift+マウスホイールで横スクロールできるか
- [ ] スクロールバーと併用できるか
- [ ] スクロール速度が適切か

### その他
- [ ] アノテーションがズーム後も正しい位置に表示されるか
- [ ] ズーム変更後も画像が正常に表示されるか
- [ ] 中パンボタンドラッグが正常に動作するか

---

## 📝 注意事項

### イベント競合の回避
- マウスホイールイベントがアノテーション操作と競合しないか確認
- キーボードショートカットがテキスト入力と競合しないか確認

### パフォーマンス
- 高倍率時（300%以上）の描画速度を確認
- 大きな画像での動作を確認

### 互換性
- Windows/Mac/Linuxでのマウスホイール動作を確認
- event.delta と event.num の両方に対応

---

**実装準備完了！始めましょうか？** ('◇')ゞ
