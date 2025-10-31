import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import json
import csv
import pandas as pd
from datetime import datetime
import shutil
import math
import numpy as np
import cv2
import copy
from pathlib import Path
import re
from io import BytesIO

try:
    import cairosvg
    _CAIROSVG_AVAILABLE = True
except ImportError:
    cairosvg = None
    _CAIROSVG_AVAILABLE = False


try:
    from openpyxl import load_workbook, Workbook
except ImportError:
    load_workbook = None
    Workbook = None

# 管理レベルおよび拡張出力用の定数とユーティリティ
MANAGEMENT_LEVELS = ['S', 'A', 'B', 'N']

DEFECT_V2_HEADERS = [
    'エリア(工区)','接続箱No.','接続箱','回路No.','アレイ番号','モジュール場所',
    '不良分類','管理レベル','シリアルナンバー(交換前)','報告書番号','離線した日','離線場所',
    'シリアルナンバー(交換後)','モジュール','列1','送電完了日','報告書番号2','備考',
    '報告年月日','採番'
]

def normalize_management_level(value):
    if not value:
        return 'S'
    v = str(value).upper().strip()
    return v if v in MANAGEMENT_LEVELS else 'S'

class ODMImageSelector:
    def __init__(self, parent, annotation, image_type, webodm_path, callback, app_ref=None):
        self.parent = parent
        self.annotation = annotation
        self.image_type = image_type
        self.webodm_path = webodm_path
        self.callback = callback
        self.app_ref = app_ref  # OrthoImageAnnotationSystem インスタンス参照（色設定取得用）
        
        self.coverage_image = None
        self.coverage_image_path = None
        self.ortho_image_size = None
        self.image_positions = []
        self.selected_image_path = None
        self.zoom_factor = 1.0
        
        self.create_selector_window()
        self.load_webodm_assets()

    def create_selector_window(self):
        """ODM画像選択ウィンドウを作成"""
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"ODM画像選択 - {self.image_type}")
        self.window.geometry("1000x800")
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # デバッグログ有効化フラグ（コンソール出力）
        self.debug = True
        
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        info_frame = ttk.LabelFrame(main_frame, text="選択情報", padding=5)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        self.info_label = ttk.Label(info_frame, text="WebODMアセットを読み込み中...")
        self.info_label.pack()
        
        # サムネイルプレビュー枠
        preview_frame = ttk.LabelFrame(main_frame, text="プレビュー", padding=5)
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        self.preview_label = tk.Label(preview_frame, text="画像を選択するとプレビューを表示します", anchor="center")
        self.preview_label.pack(fill=tk.X)
        self._odm_preview_imgtk = None  # 参照保持用
        
        image_frame = ttk.LabelFrame(main_frame, text="カバレッジ画像", padding=5)
        image_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas_frame = ttk.Frame(image_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white")
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="選択", command=self.confirm_selection).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="キャンセル", command=self.window.destroy).pack(side=tk.RIGHT)

    def debug_log(self, msg: str):
        """簡易デバッグ出力（コンソール）"""
        try:
            if getattr(self, 'debug', True):
                print(f"[DEBUG][ODM] {msg}")
        except Exception:
            pass

    def update_preview(self, image_path):
        """プレビューを更新（最大380x240）"""
        try:
            if not image_path or not os.path.exists(image_path):
                self.preview_label.config(text="プレビューなし", image="")
                self._odm_preview_imgtk = None
                return
            img = Image.open(image_path)
            max_w, max_h = 380, 240
            w, h = img.size
            scale = min(1.0, min(max_w / float(w), max_h / float(h)))
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            imgtk = ImageTk.PhotoImage(img)
            self.preview_label.config(image=imgtk, text="")
            self._odm_preview_imgtk = imgtk
            self.debug_log(f"preview updated size={new_size} for {os.path.basename(image_path)}")
        except Exception as e:
            self.preview_label.config(text=f"プレビュー失敗: {e}", image="")
            self._odm_preview_imgtk = None
            self.debug_log(f"preview failed: {e}")

    def load_webodm_assets(self):
        """WebODMアセットを読み込み、座標情報を解析する"""
        try:
            # 1. オルソ画像のパスとサイズ取得
            ortho_path = os.path.join(self.webodm_path, 'odm_orthophoto', 'odm_orthophoto.tif')
            with Image.open(ortho_path) as img:
                self.ortho_image_size = img.size
                try:
                    self.debug_log(f"orthophoto size via Pillow: {self.ortho_image_size}")
                except Exception:
                    pass

            # 2. カバレッジ画像の読み込み
            self.coverage_image_path = os.path.join(self.webodm_path, 'images', 'shot_coverage.png')
            self.coverage_image = Image.open(self.coverage_image_path)

            # 3. 座標情報の読み込みと解析
            geo_ref_path = os.path.join(self.webodm_path, 'odm_georeferencing', 'odm_georeferencing_model_geo.txt')
            self.image_positions = []
            with open(geo_ref_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        filename = parts[0]
                        image_path = os.path.join(self.webodm_path, 'images', filename)
                        if os.path.exists(image_path):
                            self.image_positions.append({
                                'filename': filename,
                                'path': image_path,
                                'x': float(parts[1]),
                                'y': float(parts[2])
                            })
            
            self.display_coverage_image()
            self.update_info()

        except FileNotFoundError as e:
            messagebox.showerror("エラー", f"必要なWebODMファイルが見つかりません: {e.filename}")
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("エラー", f"WebODMアセットの読み込みに失敗しました: {e}")
            self.window.destroy()

    def display_coverage_image(self):
        """カバレッジ画像と各種マーカーを表示"""
        if self.coverage_image:
            display_size = (int(self.coverage_image.width * self.zoom_factor), int(self.coverage_image.height * self.zoom_factor))
            resized_image = self.coverage_image.resize(display_size, Image.Resampling.LANCZOS)
            self.canvas_image = ImageTk.PhotoImage(resized_image)
            
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.canvas_image)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            self.draw_image_markers()
            self.draw_current_annotation()

    def draw_current_annotation(self):
        """アノテーション位置をスケーリングして正確に描画"""
        if not self.coverage_image or not self.ortho_image_size:
            return

        # スケール計算
        ortho_w, ortho_h = self.ortho_image_size
        coverage_w, coverage_h = self.coverage_image.size
        scale_x = coverage_w / ortho_w
        scale_y = coverage_h / ortho_h

        # アノテーション座標をカバレッジ画像上の座標に変換
        ann_x = self.annotation['x'] * scale_x * self.zoom_factor
        ann_y = self.annotation['y'] * scale_y * self.zoom_factor
        
        # ... (以降の描画ロジックは前回とほぼ同じ、座標変数だけ変更) ...
        defect_type = self.annotation.get('defect_type', 'ホットスポット')
        # 色マップはアプリ本体（app_ref）から取得。無ければデフォルト色群にフォールバック。
        default_colors = {
            "ホットスポット": "#FF0000",
            "クラスタ異常": "#FF8C00",
            "破損": "#FFD700",
            "ストリング異常": "#0000FF",
            "系統異常": "#8A2BE2",
            "影": "#008000",
        }
        if getattr(self, 'app_ref', None) and hasattr(self.app_ref, 'defect_types'):
            color = self.app_ref.defect_types.get(defect_type, default_colors.get(defect_type, "#FF0000"))
        else:
            color = default_colors.get(defect_type, "#FF0000")
        shape = self.annotation.get('shape', 'cross')
        
        if shape == "cross": self.draw_cross_annotation(ann_x, ann_y, color)
        # ... (他の形状も同様に呼び出す) ...

    # 注釈描画の簡易ヘルパー（最低限：十字）。他形状は必要に応じて追加可。
    def draw_cross_annotation(self, x, y, color):
        size = 12 * self.zoom_factor
        self.canvas.create_line(x, y - size, x, y + size, fill=color, width=2, tags="ann_preview")
        self.canvas.create_line(x - size, y, x + size, y, fill=color, width=2, tags="ann_preview")

    def draw_image_markers(self):
        """georeferencing情報から写真の位置マーカーを正確に描画"""
        if not self.ortho_image_size or not self.coverage_image:
            return

        ortho_w, ortho_h = self.ortho_image_size
        coverage_w, coverage_h = self.coverage_image.size
        scale_x = coverage_w / ortho_w
        scale_y = coverage_h / ortho_h

        for i, pos_info in enumerate(self.image_positions):
            # オルソ座標をカバレッジ座標に変換
            x = pos_info['x'] * scale_x * self.zoom_factor
            y = pos_info['y'] * scale_y * self.zoom_factor
            
            marker_size = 5 * self.zoom_factor
            self.canvas.create_oval(
                x - marker_size, y - marker_size, x + marker_size, y + marker_size,
                fill="blue", outline="white", width=1, tags=f"marker_{i}"
            )
            # 判別用ラベル（番号＋ファイル名）
            try:
                base = os.path.basename(pos_info.get('path') or pos_info.get('filename') or '')
                label = f"{i+1}: {base}" if base else f"{i+1}"
                self.canvas.create_text(
                    x + 10 * self.zoom_factor, y - 10 * self.zoom_factor,
                    text=label, anchor="w", fill="#003366",
                    font=("Arial", max(8, int(9 * self.zoom_factor))),
                    tags=f"label_{i}"
                )
            except Exception:
                pass

    def on_canvas_click(self, event):
        """キャンバスクリックで最も近い写真を選択"""
        if not self.coverage_image or not self.image_positions:
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        ortho_w, ortho_h = self.ortho_image_size
        coverage_w, coverage_h = self.coverage_image.size
        scale_x = coverage_w / ortho_w
        scale_y = coverage_h / ortho_h
        
        min_distance = float('inf')
        selected_index = -1
        
        for i, pos_info in enumerate(self.image_positions):
            marker_x = pos_info['x'] * scale_x * self.zoom_factor
            marker_y = pos_info['y'] * scale_y * self.zoom_factor
            
            distance = math.sqrt((canvas_x - marker_x)**2 + (canvas_y - marker_y)**2)
            
            if distance < 10 * self.zoom_factor and distance < min_distance:
                min_distance = distance
                selected_index = i
        
        if selected_index >= 0:
            self.select_image_by_index(selected_index)
    
    def select_image_by_index(self, index):
        """指定されたインデックスの画像を選択"""
        if 0 <= index < len(self.image_positions):
            selected_image = self.image_positions[index]
            self.selected_image_path = selected_image.get('path')
            
            # 選択状態を視覚的に表示
            self.canvas.delete("selected")
            
            ortho_w, ortho_h = self.ortho_image_size
            coverage_w, coverage_h = self.coverage_image.size
            scale_x = coverage_w / ortho_w
            scale_y = coverage_h / ortho_h
            x = selected_image.get('x', 0) * scale_x * self.zoom_factor
            y = selected_image.get('y', 0) * scale_y * self.zoom_factor
            marker_size = 15 * self.zoom_factor
            
            self.canvas.create_oval(
                x - marker_size, y - marker_size,
                x + marker_size, y + marker_size,
                fill="yellow", outline="black", width=3,
                tags="selected"
            )
            
            self.update_info()
    
    def on_mouse_wheel(self, event):
        """マウスホイールでズーム"""
        if self.coverage_image:
            if event.delta > 0:
                self.zoom_factor *= 1.1
            else:
                self.zoom_factor /= 1.1
            
            self.zoom_factor = max(0.1, min(5.0, self.zoom_factor))
            self.display_coverage_image()
    
    def update_info(self):
        """情報表示を更新"""
        info_text = ""
        if self.coverage_image_path:
            info_text += f"カバレッジ画像: {os.path.basename(self.coverage_image_path)}\n"
        
        if self.image_positions:
            info_text += f"画像数: {len(self.image_positions)}枚\n"
        
        if self.selected_image_path:
            info_text += f"選択画像: {os.path.basename(self.selected_image_path)}"
        
        self.info_label.config(text=info_text or "カバレッジ画像と画像フォルダを選択してください")
    
    def confirm_selection(self):
        """選択を確定"""
        if self.selected_image_path:
            self.callback(self.selected_image_path)
            self.window.destroy()
        else:
            messagebox.showwarning("警告", "画像を選択してください")



# --- ODMImageSelector extra methods (monkey patch) ---

def _odmselector_debug_log(self, msg: str):
    try:
        if getattr(self, 'debug', True):
            print(f"[DEBUG][ODM] {msg}")
    except Exception:
        pass

def _odmselector_update_preview(self, image_path):
    try:
        if not image_path or not os.path.exists(image_path):
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text="プレビューなし", image="")
            self._odm_preview_imgtk = None
            return
        img = Image.open(image_path)
        max_w, max_h = 380, 240
        w, h = img.size
        scale = min(1.0, min(max_w / float(w), max_h / float(h)))
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        imgtk = ImageTk.PhotoImage(img)
        if hasattr(self, 'preview_label'):
            self.preview_label.config(image=imgtk, text="")
        self._odm_preview_imgtk = imgtk
        _odmselector_debug_log(self, f"preview updated size={new_size} for {os.path.basename(image_path)}")
    except Exception as e:
        try:
            if hasattr(self, 'preview_label'):
                self.preview_label.config(text=f"プレビュー失敗: {e}", image="")
        except Exception:
            pass
        self._odm_preview_imgtk = None
        _odmselector_debug_log(self, f"preview failed: {e}")

def _odmselector_select_image_by_index(self, index):
    """指定されたインデックスの画像を選択（プレビュー＆ログ付き）"""
    if 0 <= index < len(self.image_positions):
        selected_image = self.image_positions[index]
        self.selected_image_path = selected_image.get('path')
        # 選択状態の視覚表示
        self.canvas.delete("selected")
        ortho_w, ortho_h = self.ortho_image_size
        coverage_w, coverage_h = self.coverage_image.size
        scale_x = coverage_w / ortho_w
        scale_y = coverage_h / ortho_h
        x = selected_image.get('x', 0) * scale_x * self.zoom_factor
        y = selected_image.get('y', 0) * scale_y * self.zoom_factor
        marker_size = 15 * self.zoom_factor
        self.canvas.create_oval(
            x - marker_size, y - marker_size,
            x + marker_size, y + marker_size,
            fill="yellow", outline="black", width=3,
            tags="selected"
        )
        # プレビュー更新
        try:
            if self.selected_image_path:
                _odmselector_update_preview(self, self.selected_image_path)
        except Exception:
            pass
        self.update_info()
        _odmselector_debug_log(self, f"selected index={index}, path={self.selected_image_path}")

# メソッドをクラスへ付与

def _odmselector_create_selector_window(self):
    """ODM画像選択ウィンドウを作成（プレビュー＋画像フォルダ選択ボタン付き）"""
    self.window = tk.Toplevel(self.parent)
    self.window.title(f"ODM画像選択 - {self.image_type}")
    self.window.geometry("1000x800")
    self.window.transient(self.parent)
    self.window.grab_set()

    # デバッグログ有効化フラグ
    self.debug = True

    main_frame = ttk.Frame(self.window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    info_frame = ttk.LabelFrame(main_frame, text="選択情報", padding=5)
    info_frame.pack(fill=tk.X, pady=(0, 10))
    self.info_label = ttk.Label(info_frame, text="WebODMアセットを読み込み中...")
    self.info_label.pack()

    # サムネイルプレビュー枠
    preview_frame = ttk.LabelFrame(main_frame, text="プレビュー", padding=5)
    preview_frame.pack(fill=tk.X, pady=(0, 10))
    self.preview_label = tk.Label(preview_frame, text="画像を選択するとプレビューを表示します", anchor="center")
    self.preview_label.pack(fill=tk.X)
    self._odm_preview_imgtk = None  # 参照保持

    image_frame = ttk.LabelFrame(main_frame, text="カバレッジ画像", padding=5)
    image_frame.pack(fill=tk.BOTH, expand=True)

    canvas_frame = ttk.Frame(image_frame)
    canvas_frame.pack(fill=tk.BOTH, expand=True)

    self.canvas = tk.Canvas(canvas_frame, bg="white")
    v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
    h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
    self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

    self.canvas.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")

    canvas_frame.grid_rowconfigure(0, weight=1)
    canvas_frame.grid_columnconfigure(0, weight=1)

    self.canvas.bind("<Button-1>", self.on_canvas_click)
    self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(10, 0))
    ttk.Button(button_frame, text="画像フォルダ選択", command=self.select_images_folder).pack(side=tk.LEFT, padx=(0, 10))
    ttk.Button(button_frame, text="選択", command=self.confirm_selection).pack(side=tk.RIGHT, padx=(10, 0))
    ttk.Button(button_frame, text="キャンセル", command=self.window.destroy).pack(side=tk.RIGHT)


def _odmselector_norm_key(name: str):
    """拡張子を除き、大小文字差を無視した照合キーを生成（DJI_XXXX.*対応）"""
    try:
        if not name:
            return ""
        base = os.path.basename(name)
        stem, _ext = os.path.splitext(base)
        return stem.lower()
    except Exception:
        return str(name).lower()


def _odmselector_select_images_folder(self):
    """画像フォルダを選択し、basename（拡張子除く）とgeoreferencingの照合でマーカーを展開"""
    try:
        folder = filedialog.askdirectory(title="座標付き画像フォルダを選択")
        if not folder:
            return
        target_exts = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}
        files = []
        for root, dirs, fnames in os.walk(folder):
            for fn in fnames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in target_exts:
                    files.append(os.path.join(root, fn))
        _odmselector_debug_log(self, f"scan folder done: {folder}, candidates={len(files)}")

        # georeferencing由来の basename（stem小文字） -> (px, py) インデックス
        geo_index = {}
        for p in getattr(self, 'image_positions', []):
            base = os.path.basename(p.get('filename') or p.get('path') or '')
            if not base:
                base = os.path.basename(p.get('path') or '')
            key = _odmselector_norm_key(base)
            if key:
                geo_index[key] = (float(p.get('x', 0)), float(p.get('y', 0)))
        self._geo_index = geo_index

        matched = []
        unmatched_samples = []
        for fp in files:
            key = _odmselector_norm_key(os.path.basename(fp))
            if key in geo_index:
                px, py = geo_index[key]
                matched.append({'filename': os.path.basename(fp), 'path': fp, 'x': float(px), 'y': float(py)})
            else:
                if len(unmatched_samples) < 5:
                    unmatched_samples.append(os.path.basename(fp))

        if matched:
            self.image_positions = matched
            self.display_coverage_image()
            self.update_info()
            try:
                if len(self.image_positions) > 0:
                    self.select_image_by_index(0)
            except Exception:
                pass
        else:
            messagebox.showwarning("警告", "このフォルダ内で位置情報に一致する画像は見つかりませんでした。")

        total = len(files)
        um = total - len(matched)
        _odmselector_debug_log(self, f"folder match: total={total}, matched={len(matched)}, unmatched={um}")
        if um > 0:
            sample_text = ", ".join(unmatched_samples)
            messagebox.showinfo("情報", f"未マッチ: {um}件\n例: {sample_text}")
    except Exception as e:
        _odmselector_debug_log(self, f"select_images_folder failed: {e}")
        messagebox.showerror("エラー", f"画像フォルダ選択処理でエラー: {e}")


def _odmselector_update_info(self):
    """情報表示を更新＋必要ならフォルダ選択を促す"""
    # geo index 構築（未構築時）
    try:
        if not hasattr(self, '_geo_index') or not self._geo_index:
            geo_index = {}
            for p in getattr(self, 'image_positions', []) or []:
                base = os.path.basename(p.get('filename') or p.get('path') or '')
                if not base:
                    base = os.path.basename(p.get('path') or '')
                key = _odmselector_norm_key(base)
                if key:
                    geo_index[key] = (float(p.get('x', 0)), float(p.get('y', 0)))
            self._geo_index = geo_index
            _odmselector_debug_log(self, f"geo index built in update_info: keys={len(self._geo_index)}")
    except Exception:
        pass

    info_text = ""
    if getattr(self, 'coverage_image_path', None):
        info_text += f"カバレッジ画像: {os.path.basename(self.coverage_image_path)}\n"
    if getattr(self, 'image_positions', None):
        info_text += f"画像数: {len(self.image_positions)}枚\n"
    if getattr(self, 'selected_image_path', None):
        info_text += f"選択画像: {os.path.basename(self.selected_image_path)}"
    self.info_label.config(text=info_text or "カバレッジ画像と画像フォルダを選択してください")
    # 初期マーカーが少ない場合のフォルダ選択促し（1度だけ）
    try:
        if not getattr(self, '_folder_prompted', False):
            cnt = len(self.image_positions) if isinstance(self.image_positions, list) else 0
            if cnt <= 2:
                self._folder_prompted = True
                if messagebox.askyesno("確認", "マーカー数が少ないため、画像フォルダを選択してマーカーを展開しますか？"):
                    if hasattr(self, 'select_images_folder'):
                        self.select_images_folder()
    except Exception:
        pass

ODMImageSelector.debug_log = _odmselector_debug_log
ODMImageSelector.update_preview = _odmselector_update_preview
ODMImageSelector.select_image_by_index = _odmselector_select_image_by_index
ODMImageSelector.select_images_folder = _odmselector_select_images_folder
ODMImageSelector._norm_key = _odmselector_norm_key
ODMImageSelector.update_info = _odmselector_update_info
ODMImageSelector.create_selector_window = _odmselector_create_selector_window

# --- Robust WebODM asset loader (monkey patch) ---

def load_webodm_assets_robust(self):
    """WebODMアセットを読み込み、座標情報を解析する（堅牢化版）"""
    import re
    try:
        self.debug_log(f"start load_webodm_assets: webodm_path={self.webodm_path}")
    except Exception:
        pass
    try:
        def find_first_existing(base_path, relative_paths):
            for rel in relative_paths:
                p = os.path.join(base_path, rel)
                if os.path.exists(p):
                    return p
            return None

        def read_world_file(raster_path):
            base, _ = os.path.splitext(raster_path)
            candidates = [base + '.tfw', base + '.wld']
            for wf in candidates:
                if os.path.exists(wf):
                    try:
                        with open(wf, 'r') as f:
                            vals = [float(line.strip()) for line in f if line.strip()]
                        if len(vals) >= 6:
                            return {
                                'A': vals[0],  # pixel size x
                                'B': vals[1],  # rotation
                                'D': vals[2],  # rotation
                                'E': vals[3],  # pixel size y (negative)
                                'C': vals[4],  # top-left x
                                'F': vals[5],  # top-left y
                            }
                    except Exception:
                        pass
            return None

        def world_to_pixel(gt, x, y):
            if not gt:
                return None
            A, B, D, E, C, F = gt['A'], gt['B'], gt['D'], gt['E'], gt['C'], gt['F']
            # no rotation
            if abs(B) < 1e-9 and abs(D) < 1e-9:
                px = (x - C) / A
                py = (F - y) / abs(E)
                return px, py
            det = A * E - B * D
            if abs(det) < 1e-12:
                return None
            px = (E * (x - C) - B * (y - F)) / det
            py = (-D * (x - C) + A * (y - F)) / det
            return px, py

        def extract_filename_and_xy(line):
            # filename
            m = re.search(r'([^\s,\"]+\.(?:jpg|jpeg|png|tif|tiff))', line, re.IGNORECASE)
            fname = m.group(1) if m else None
            # numbers
            nums = re.findall(r'[-+]?(?:\d*\.\d+|\d+)', line)
            if len(nums) >= 2:
                try:
                    return fname, float(nums[0]), float(nums[1])
                except Exception:
                    return fname, None, None
            return fname, None, None

        def resolve_image_path(base_path, filename):
            if not filename:
                return None
            candidates = []
            if os.path.isabs(filename):
                candidates.append(filename)
            else:
                candidates.append(os.path.join(base_path, filename))
                candidates.append(os.path.join(base_path, 'images', filename))
                candidates.append(os.path.join(base_path, 'images', os.path.basename(filename)))
            for c in candidates:
                if os.path.exists(c):
                    return c
            return None

        # 1) オルソ画像
        ortho_candidates = [
            os.path.join(self.webodm_path, 'odm_orthophoto', 'odm_orthophoto.tif'),
            os.path.join(self.webodm_path, 'odm_orthophoto', 'odm_orthophoto.tiff'),
            os.path.join(self.webodm_path, 'odm_orthophoto', 'odm_orthophoto.png'),
        ]
        self.ortho_path = next((p for p in ortho_candidates if os.path.exists(p)), None)
        if not self.ortho_path:
            raise FileNotFoundError(os.path.join(self.webodm_path, 'odm_orthophoto', 'odm_orthophoto.tif'))
        # オルソ画像サイズを堅牢に取得（Pillow失敗時にtifffile/rasterioフォールバック）
        self.ortho_image_size = None
        try:
            with Image.open(self.ortho_path) as img:
                self.ortho_image_size = img.size
                try:
                    self.debug_log(f"orthophoto size via Pillow: {self.ortho_image_size}")
                except Exception:
                    pass
        except Exception:
            try:
                import tifffile as tiff
                with tiff.TiffFile(self.ortho_path) as tf:
                    page = tf.pages[0]
                    w = getattr(page, 'imagewidth', None)
                    h = getattr(page, 'imagelength', None)
                    if w is not None and h is not None:
                        self.ortho_image_size = (int(w), int(h))
                    else:
                        shp = getattr(page, 'shape', None)
                        if shp:
                            if len(shp) == 2:
                                self.ortho_image_size = (int(shp[1]), int(shp[0]))
                            elif len(shp) == 3:
                                self.ortho_image_size = (int(shp[2]), int(shp[1]))
            except Exception:
                try:
                    import rasterio
                    with rasterio.open(self.ortho_path) as ds:
                        self.ortho_image_size = (int(ds.width), int(ds.height))
                except Exception:
                    pass
        if not self.ortho_image_size:
            # 最終手段: 実読込してサイズ取得（重い可能性あり）
            try:
                import tifffile as tiff, numpy as np
                arr = tiff.imread(self.ortho_path)
                if arr.ndim == 2:
                    h, w = arr.shape
                elif arr.ndim == 3:
                    if arr.shape[0] in (1, 3, 4) and arr.shape[-1] not in (3, 4):
                        # (bands, H, W) → (H, W, bands)
                        arr = np.transpose(arr, (1, 2, 0))
                    h, w = arr.shape[0], arr.shape[1]
                else:
                    raise RuntimeError('Unsupported TIFF shape')
                self.ortho_image_size = (int(w), int(h))
            except Exception as e:
                raise RuntimeError(f"orthophoto size detection failed: {e}")

        # 2) ワールドファイル
        geotransform = read_world_file(self.ortho_path)

        # 3) カバレッジ画像（任意）
        cov = find_first_existing(self.webodm_path, [
            'images/shot_coverage.png',
            'odm_report/assets/odm_orthophoto_coverage.png',
            'odm_report/odm_orthophoto_coverage.png',
            'odm_orthophoto/odm_orthophoto.png',
            'odm_orthophoto/odm_orthophoto_preview.png',
        ])
        if cov and os.path.exists(cov):
            try:
                self.coverage_image = Image.open(cov)
                self.coverage_image_path = cov
            except Exception:
                self.coverage_image = None
                self.coverage_image_path = None
        if not getattr(self, 'coverage_image', None):
            # orthophoto から低解像度プレビューを生成（tifffile→rasterio→最後にPillowの順で試行）
            preview_img = None
            # 1) tifffile で読み取り→8bit化→縮小
            try:
                import tifffile as tiff, numpy as np
                arr = tiff.imread(self.ortho_path)
                arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
                if arr.ndim == 3:
                    # (bands, H, W) を (H, W, bands) に補正
                    if arr.shape[0] in (1, 2, 3, 4) and arr.shape[-1] not in (1, 2, 3, 4):
                        arr = np.transpose(arr, (1, 2, 0))
                # min-max で 8bit 化
                if arr.dtype != np.uint8:
                    arrf = arr.astype(np.float32)
                    mn = float(np.nanmin(arrf))
                    mx = float(np.nanmax(arrf))
                    if mx > mn:
                        arr8 = ((arrf - mn) / (mx - mn) * 255.0).clip(0, 255).astype(np.uint8)
                    else:
                        # 同次元のゼロ配列を返す（2D なら(H,W)、3Dなら(H,W,C)）
                        if arr.ndim == 2:
                            arr8 = np.zeros(arr.shape, dtype=np.uint8)
                        else:
                            arr8 = np.zeros(arr.shape, dtype=np.uint8)
                else:
                    arr8 = arr
                # チャンネル処理（Pillowが扱えるRGBへ）
                if arr8.ndim == 2:
                    preview_img = Image.fromarray(arr8).convert('RGB')
                elif arr8.ndim == 3:
                    c = arr8.shape[2]
                    if c == 1:
                        preview_img = Image.fromarray(arr8[..., 0]).convert('RGB')
                    elif c == 2:
                        # 2chは Band1 グレースケールRGBで可視化（緑かぶり防止）
                        c0 = arr8[..., 0]
                        arr3 = np.dstack([c0, c0, c0])
                        preview_img = Image.fromarray(arr3)
                    elif c >= 3:
                        preview_img = Image.fromarray(arr8[..., :3])
                    else:
                        preview_img = Image.fromarray(arr8[..., 0]).convert('RGB')
                else:
                    preview_img = None
            except Exception:
                preview_img = None
            # 2) rasterio で縮小読み取り
            if preview_img is None:
                try:
                    import rasterio, numpy as np
                    from rasterio.enums import Resampling
                    with rasterio.open(self.ortho_path) as ds:
                        w, h = ds.width, ds.height
                        max_side = 2000
                        scale = min(1.0, max_side / float(max(w, h)))
                        out_w = max(1, int(w * scale))
                        out_h = max(1, int(h * scale))
                        arr = ds.read(out_shape=(min(ds.count, 3), out_h, out_w), resampling=Resampling.bilinear)
                        arr = arr.transpose(1, 2, 0)
                        # 正規化
                        arr = arr.astype(np.float32)
                        mn = float(np.nanmin(arr))
                        mx = float(np.nanmax(arr))
                        if mx > mn:
                            arr8 = ((arr - mn) / (mx - mn) * 255.0).clip(0, 255).astype(np.uint8)
                        else:
                            arr8 = np.zeros((out_h, out_w, 3), dtype=np.uint8)
                        if len(arr8.shape) == 3 and arr8.shape[2] == 2:
                            arr8 = np.dstack([arr8[...,0], arr8[...,0], arr8[...,0]])
                        preview_img = Image.fromarray(arr8)
                except Exception:
                    preview_img = None
            # 3) Pillow（PNGや非GeoTIFFの場合はそのまま）
            if preview_img is None:
                try:
                    with Image.open(self.ortho_path) as img:
                        w, h = img.size
                        max_side = 2000
                        scale = min(1.0, max_side / max(w, h))
                        preview_img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                except Exception:
                    preview_img = None
            if preview_img is not None:
                self.coverage_image = preview_img.convert('RGB')
                self.coverage_image_path = self.ortho_path
            else:
                self.coverage_image = None
                self.coverage_image_path = None

        # 4) 座標ファイル
        geo_candidates = [
            os.path.join(self.webodm_path, 'odm_georeferencing', 'odm_georeferencing_model_geo.txt'),
            os.path.join(self.webodm_path, 'odm_georeferencing', 'odm_georeferencing_model_geo.csv'),
            os.path.join(self.webodm_path, 'odm_georeferencing', 'odm_georeferencing_model.txt'),
            os.path.join(self.webodm_path, 'odm_georeferencing', 'odm_georeferencing_model.csv'),
            os.path.join(self.webodm_path, 'odm_georeferencing', 'odm_georeferencing_utm.txt'),
        ]
        geo_ref_path = next((p for p in geo_candidates if os.path.exists(p)), None)
        if not geo_ref_path:
            raise FileNotFoundError(os.path.join(self.webodm_path, 'odm_georeferencing', 'odm_georeferencing_model_geo.txt'))

        # 5) ファイル読込とXY抽出
        raw_positions = []
        with open(geo_ref_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                fname, x, y = extract_filename_and_xy(line)
                if x is None or y is None:
                    continue
                img_path = resolve_image_path(self.webodm_path, fname) if fname else None
                raw_positions.append({'filename': os.path.basename(fname) if fname else '', 'path': img_path, 'wx': x, 'wy': y})

        # 6) ピクセル座標へ
        self.image_positions = []
        ortho_w, ortho_h = self.ortho_image_size
        if geotransform:
            for p in raw_positions:
                res = world_to_pixel(geotransform, p['wx'], p['wy'])
                if not res:
                    continue
                px, py = res
                self.image_positions.append({'filename': p['filename'], 'path': p['path'], 'x': float(px), 'y': float(py)})
        else:
            xs = [p['wx'] for p in raw_positions]
            ys = [p['wy'] for p in raw_positions]
            if xs and ys:
                minx, maxx = min(xs), max(xs)
                miny, maxy = min(ys), max(ys)
                dx = max(maxx - minx, 1e-6)
                dy = max(maxy - miny, 1e-6)
                for p in raw_positions:
                    px = (p['wx'] - minx) / dx * ortho_w
                    py = (maxy - p['wy']) / dy * ortho_h  # y軸反転
                    self.image_positions.append({'filename': p['filename'], 'path': p['path'], 'x': float(px), 'y': float(py)})

        # 7) 表示
        self.display_coverage_image()
        self.update_info()

    except FileNotFoundError as e:
        messagebox.showerror("エラー", f"必要なWebODMファイルが見つかりません: {e.filename}")
        self.window.destroy()
    except Exception as e:
        messagebox.showerror("エラー", f"WebODMアセットの読み込みに失敗しました: {e}")
        self.window.destroy()

# 既存メソッドを差し替え
ODMImageSelector.load_webodm_assets = load_webodm_assets_robust

try:
    from openpyxl import load_workbook, Workbook
except ImportError:
    load_workbook = None
    Workbook = None

# 管理レベルと拡張出力用の定数/ユーティリティ
MANAGEMENT_LEVELS = ['S', 'A', 'B', 'N']

DEFECT_V2_HEADERS = [
    'エリア(工区)','接続箱No.','接続箱','回路No.','アレイ番号','モジュール場所',
    '不良分類','管理レベル','シリアルナンバー(交換前)','報告書番号','離線した日','離線場所',
    'シリアルナンバー(交換後)','モジュール','列1','送電完了日','報告書番号2','備考',
    '報告年月日','採番'
]

def normalize_management_level(value):
    if not value:
        return 'S'
    v = str(value).upper().strip()
    return v if v in MANAGEMENT_LEVELS else 'S'

class ThermalVisibleFileDialog:
    """サーモ画像と可視画像を同時に選択するカスタムダイアログ"""

    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
    THUMBNAIL_SIZE = (1000, 1000)
    PREVIEW_BASE_SIZE = (1000, 650)
    PREVIEW_MIN_ZOOM = 0.25
    PREVIEW_MAX_ZOOM = 3.0

    def __init__(self, parent, initial_dir=None, title="サーモ画像同時選択"):
        self.parent = parent
        self.result = None
        self.thermal_photo = None
        self.visible_photo = None
        self.display_mode = "list"
        self.files_in_current_dir = []
        self.thumbnail_cache = {}
        self.thumbnail_buttons = {}
        self.thumbnail_columns = 3
        self.selected_file = None
        self._suppress_listbox_event = False
        self.preview_zoom = 1.0
        self._preview_refresh_job = None
        self._updating_zoom_var = False

        self.layout_config_path = Path.home() / ".ortho_annotation_system_v7" / "layout.json"
        self.layout_preferences = {"main_ratio": 0.5, "preview_ratio": 1.0}
        self.load_layout_preferences()
        self.zoom_options = [
            ("50%", 0.5),
            ("75%", 0.75),
            ("100%", 1.0),
            ("125%", 1.25),
            ("150%", 1.5),
            ("200%", 2.0),
            ("300%", 3.0),
        ]
        self.page_size_options = [10, 50, 500, 400]
        self.page_size = 100
        self.current_page = 1

        if initial_dir:
            try:
                init_path = Path(initial_dir).expanduser()
            except Exception:
                init_path = Path.home()
        else:
            init_path = Path.home()

        if not init_path.exists() or not init_path.is_dir():
            init_path = Path.home()
        self.current_dir = init_path

        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("1920x1100")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.window.bind("<Configure>", self.on_window_configure)

        self.dir_var = tk.StringVar(value=str(self.current_dir))

        self.create_widgets()
        self.populate_file_list()
        self.bind_keyboard_shortcuts()
        self.window.after(200, self.restore_layout_preferences)

    def create_widgets(self):
        dir_frame = ttk.Frame(self.window)
        dir_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(dir_frame, text="フォルダ:").pack(side=tk.LEFT)
        ttk.Entry(dir_frame, textvariable=self.dir_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10)
        )
        ttk.Button(dir_frame, text="フォルダ選択", command=self.select_directory).pack(side=tk.LEFT)

        mode_frame = ttk.Frame(self.window)
        mode_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.list_view_button = ttk.Button(mode_frame, text="ファイル名表示", command=lambda: self.set_display_mode("list"))
        self.thumbnail_view_button = ttk.Button(mode_frame, text="サムネイル表示", command=lambda: self.set_display_mode("thumbnail"))
        self.list_view_button.pack(side=tk.LEFT, padx=(0, 5))
        self.thumbnail_view_button.pack(side=tk.LEFT)

        pagination_frame = ttk.Frame(self.window)
        pagination_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Label(pagination_frame, text="表示件数:").pack(side=tk.LEFT)
        self.page_size_var = tk.StringVar(value=str(self.page_size))
        self.page_size_combo = ttk.Combobox(
            pagination_frame,
            textvariable=self.page_size_var,
            state="readonly",
            width=5,
            values=[str(v) for v in self.page_size_options]
        )
        self.page_size_combo.pack(side=tk.LEFT, padx=(5, 10))
        self.page_size_combo.bind("<<ComboboxSelected>>", self.on_page_size_change)
        ttk.Frame(pagination_frame).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.prev_page_button = ttk.Button(pagination_frame, text="前へ", width=6, command=lambda: self.change_page(-1))
        self.prev_page_button.pack(side=tk.LEFT, padx=(0, 5))
        self.next_page_button = ttk.Button(pagination_frame, text="次へ", width=6, command=lambda: self.change_page(1))
        self.next_page_button.pack(side=tk.LEFT, padx=(0, 10))
        self.page_info_var = tk.StringVar(value="")
        ttk.Label(pagination_frame, textvariable=self.page_info_var).pack(side=tk.LEFT)

        self.main_paned = ttk.Panedwindow(self.window, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.main_paned.bind("<ButtonRelease-1>", lambda _evt: self.schedule_preview_refresh())

        list_frame = ttk.LabelFrame(self.main_paned, text="サーモ画像ファイル")
        self.main_paned.add(list_frame, weight=1)
        self.list_container = ttk.Frame(list_frame)
        self.list_container.pack(fill=tk.BOTH, expand=True)

        self.listbox_frame = ttk.Frame(self.list_container)
        self.listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.file_listbox = tk.Listbox(self.listbox_frame, exportselection=False)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar = ttk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.configure(yscrollcommand=list_scrollbar.set)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        self.thumbnail_frame = ttk.Frame(self.list_container)
        self.thumbnail_canvas = tk.Canvas(self.thumbnail_frame, highlightthickness=0)
        self.thumbnail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.thumbnail_scrollbar = ttk.Scrollbar(
            self.thumbnail_frame, orient=tk.VERTICAL, command=self.thumbnail_canvas.yview
        )
        self.thumbnail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.thumbnail_canvas.configure(yscrollcommand=self.thumbnail_scrollbar.set)
        self.thumbnail_inner = ttk.Frame(self.thumbnail_canvas)
        self.thumbnail_window = self.thumbnail_canvas.create_window((0, 0), window=self.thumbnail_inner, anchor="nw")
        self.thumbnail_inner.bind(
            "<Configure>",
            lambda _: self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))
        )
        self.thumbnail_canvas.bind("<Configure>", self._on_thumbnail_canvas_configure)
        self.thumbnail_frame.pack_forget()

        preview_wrapper = ttk.Frame(self.main_paned)
        self.main_paned.add(preview_wrapper, weight=1)

        preview_frame = ttk.LabelFrame(preview_wrapper, text="プレビュー")
        preview_frame.pack(fill=tk.BOTH, expand=True)

        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        preview_container = ttk.Frame(preview_frame)
        preview_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 0))
        preview_container.columnconfigure(0, weight=1)
        preview_container.rowconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(preview_container, highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        preview_scrollbar = ttk.Scrollbar(preview_container, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        preview_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preview_canvas.configure(yscrollcommand=preview_scrollbar.set)

        self.preview_inner = ttk.Frame(self.preview_canvas)
        self.preview_window = self.preview_canvas.create_window((0, 0), window=self.preview_inner, anchor="nw")
        self.preview_inner.bind(
            "<Configure>",
            lambda _: self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
        )
        self.preview_canvas.bind("<Configure>", self._on_preview_canvas_configure)

        self.preview_vertical_paned = ttk.Panedwindow(self.preview_inner, orient=tk.VERTICAL)
        self.preview_vertical_paned.pack(fill=tk.BOTH, expand=True)
        self.preview_vertical_paned.bind("<ButtonRelease-1>", lambda _evt: self.schedule_preview_refresh())

        thermal_section = ttk.Frame(self.preview_vertical_paned)
        self.preview_vertical_paned.add(thermal_section, weight=1)
        thermal_frame = ttk.LabelFrame(thermal_section, text="サーモ画像")
        thermal_frame.pack(fill=tk.BOTH, expand=True)
        self.thermal_preview = tk.Label(thermal_frame, text="ファイルを選択してください", anchor="center", justify="center")
        self.thermal_preview.pack(fill=tk.BOTH, expand=True)

        visible_section = ttk.Frame(self.preview_vertical_paned)
        self.preview_vertical_paned.add(visible_section, weight=1)
        visible_frame = ttk.LabelFrame(visible_section, text="可視画像")
        visible_frame.pack(fill=tk.BOTH, expand=True)
        self.visible_preview = tk.Label(visible_frame, text="対応する可視画像を表示します", anchor="center", justify="center")
        self.visible_preview.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.Frame(preview_frame)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        self.zoom_out_button = ttk.Button(
            controls_frame,
            text="🔍－",
            width=4,
            command=lambda: self.adjust_preview_zoom(factor=0.8)
        )
        self.zoom_out_button.pack(side=tk.LEFT)
        self.zoom_in_button = ttk.Button(
            controls_frame,
            text="🔍＋",
            width=4,
            command=lambda: self.adjust_preview_zoom(factor=1.25)
        )
        self.zoom_in_button.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(controls_frame, text="倍率:").pack(side=tk.LEFT, padx=(10, 5))
        self.zoom_var = tk.StringVar()
        self.zoom_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.zoom_var,
            state="readonly",
            width=7,
            values=[label for label, _ in self.zoom_options]
        )
        self.zoom_combo.pack(side=tk.LEFT)
        self.zoom_combo.bind("<<ComboboxSelected>>", self.on_zoom_combo_change)

        self.visible_status_var = tk.StringVar(value="")
        ttk.Label(preview_frame, textvariable=self.visible_status_var, foreground="#666666").grid(
            row=2, column=0, sticky="ew", padx=5, pady=(0, 5)
        )

        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(button_frame, text="決定", command=self.on_confirm).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="キャンセル", command=self.on_cancel).pack(side=tk.RIGHT)

        self.update_mode_buttons()
        self.update_zoom_display()

    def populate_file_list(self, rescan=True):
        if rescan or not hasattr(self, "files_in_current_dir"):
            if not self.current_dir.exists():
                self.files_in_current_dir = []
            else:
                self.files_in_current_dir = [
                    p for p in sorted(self.current_dir.iterdir())
                    if p.is_file() and p.suffix.lower() in self.IMAGE_EXTS and p.stem[-1:].upper() == "T"
                ]
        self.ensure_current_page_valid()
        self.refresh_views()
        self.ensure_selection_in_current_page()

    def select_directory(self):
        selected_dir = filedialog.askdirectory(parent=self.window, initialdir=str(self.current_dir))
        if selected_dir:
            path = Path(selected_dir)
            if path.exists():
                self.current_dir = path
                self.dir_var.set(str(self.current_dir))
                self.selected_file = None
                self.current_page = 1
                self.thumbnail_cache.clear()
                self.populate_file_list()

    def clear_previews(self):
        self.thermal_photo = None
        self.visible_photo = None
        self.thermal_preview.config(image="", text="ファイルを選択してください")
        self.visible_preview.config(image="", text="対応する可視画像を表示します")
        self.visible_status_var.set("")
        if hasattr(self, "preview_canvas"):
            self.preview_canvas.yview_moveto(0)

    def set_display_mode(self, mode: str):
        if mode not in ("list", "thumbnail"):
            return
        if mode == self.display_mode:
            return
        self.display_mode = mode
        if mode == "list":
            self.thumbnail_frame.pack_forget()
            self.listbox_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.listbox_frame.pack_forget()
            self.thumbnail_frame.pack(fill=tk.BOTH, expand=True)
        self.update_mode_buttons()
        self.refresh_views()
        self.ensure_selection_in_current_page()

    def update_mode_buttons(self):
        if self.display_mode == "list":
            self.list_view_button.state(["disabled"])
            self.thumbnail_view_button.state(["!disabled"])
        else:
            self.thumbnail_view_button.state(["disabled"])
            self.list_view_button.state(["!disabled"])

    def bind_keyboard_shortcuts(self):
        if not hasattr(self, "window"):
            return
        self.window.bind("<Left>", self.on_key_left)
        self.window.bind("<Right>", self.on_key_right)
        self.window.bind("<Up>", self.on_key_up)
        self.window.bind("<Down>", self.on_key_down)

    def on_key_left(self, event):
        if self.display_mode != "thumbnail":
            return
        self.move_thumbnail_selection(delta_row=0, delta_col=-1)
        return "break"

    def on_key_right(self, event):
        if self.display_mode != "thumbnail":
            return
        self.move_thumbnail_selection(delta_row=0, delta_col=1)
        return "break"

    def on_key_up(self, event):
        if self.display_mode != "thumbnail":
            return
        self.move_thumbnail_selection(delta_row=-1, delta_col=0)
        return "break"

    def on_key_down(self, event):
        if self.display_mode != "thumbnail":
            return
        self.move_thumbnail_selection(delta_row=1, delta_col=0)
        return "break"

    def move_thumbnail_selection(self, delta_row=0, delta_col=0):
        page_files = self.get_page_files()
        if not page_files:
            return
        columns = max(1, self.thumbnail_columns)
        if self.selected_file in page_files:
            current_index = page_files.index(self.selected_file)
        else:
            current_index = 0
        new_index = current_index + delta_row * columns + delta_col
        new_index = max(0, min(new_index, len(page_files) - 1))
        target = page_files[new_index]
        self.set_selected_file(target)

    def load_layout_preferences(self):
        try:
            if self.layout_config_path.exists():
                with self.layout_config_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    main_ratio = data.get("main_ratio")
                    preview_ratio = data.get("preview_ratio")
                    if isinstance(main_ratio, (int, float)):
                        self.layout_preferences["main_ratio"] = float(main_ratio)
                    if isinstance(preview_ratio, (int, float)):
                        self.layout_preferences["preview_ratio"] = float(preview_ratio)
        except Exception:
            pass

    def restore_layout_preferences(self, attempt=0):
        if not hasattr(self, "main_paned") or not hasattr(self, "preview_vertical_paned"):
            return
        main_ratio = float(self.layout_preferences.get("main_ratio", 0.5))
        preview_ratio = float(self.layout_preferences.get("preview_ratio", 0.5))
        main_ratio = max(0.1, min(0.9, main_ratio))
        preview_ratio = max(0.1, min(0.9, preview_ratio))
        # 保存済みの preview_ratio をそのまま使う（固定上書きを廃止）
        main_width = self.main_paned.winfo_width()
        preview_height = self.preview_vertical_paned.winfo_height()
        if (main_width <= 1 or preview_height <= 1) and attempt < 10:
            self.window.after(200, lambda: self.restore_layout_preferences(attempt + 1))
            return
        try:
            if main_width > 1:
                self.main_paned.sashpos(0, int(main_width * main_ratio))
        except tk.TclError:
            pass
        try:
            if preview_height > 1:
                self.preview_vertical_paned.sashpos(0, int(preview_height * preview_ratio))
                # 固定位置の上書きを撤廃（比率ベースの配置に一本化）
        except tk.TclError:
            pass

    def save_layout_preferences(self):
        if not hasattr(self, "main_paned") or not hasattr(self, "preview_vertical_paned"):
            return
        try:
            main_width = self.main_paned.winfo_width()
            if main_width > 0:
                pos = self.main_paned.sashpos(0)
                if isinstance(pos, int):
                    self.layout_preferences["main_ratio"] = max(0.1, min(0.9, pos / main_width))
            preview_height = self.preview_vertical_paned.winfo_height()
            if preview_height > 0:
                pos_v = self.preview_vertical_paned.sashpos(0)
                if isinstance(pos_v, int):
                    self.layout_preferences["preview_ratio"] = max(0.1, min(0.9, pos_v / preview_height))
        except tk.TclError:
            pass
        try:
            self.layout_config_path.parent.mkdir(parents=True, exist_ok=True)
            with self.layout_config_path.open("w", encoding="utf-8") as f:
                json.dump(self.layout_preferences, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def refresh_views(self):
        self.refresh_listbox()
        self.refresh_thumbnail_view()
        self.update_pagination_controls()

    def get_total_pages(self):
        if not hasattr(self, "files_in_current_dir") or not self.files_in_current_dir:
            return 0
        if self.page_size <= 0:
            return 1
        return math.ceil(len(self.files_in_current_dir) / self.page_size)

    def get_page_files(self):
        if not hasattr(self, "files_in_current_dir") or not self.files_in_current_dir:
            return []
        if self.page_size <= 0:
            return list(self.files_in_current_dir)
        total_pages = self.get_total_pages()
        if total_pages == 0:
            return []
        page = max(1, min(self.current_page, total_pages))
        start = (page - 1) * self.page_size
        end = start + self.page_size
        return self.files_in_current_dir[start:end]

    def ensure_current_page_valid(self):
        total_pages = self.get_total_pages()
        if total_pages == 0:
            self.current_page = 1
            if getattr(self, "selected_file", None) is not None:
                self.selected_file = None
            return
        self.current_page = max(1, min(self.current_page, total_pages))
        if self.page_size > 0 and self.selected_file and self.selected_file in self.files_in_current_dir:
            page_index = self.files_in_current_dir.index(self.selected_file) // self.page_size + 1
            if page_index != self.current_page:
                self.current_page = page_index
        elif self.selected_file and self.selected_file not in self.files_in_current_dir:
            self.selected_file = None

    def ensure_selection_in_current_page(self):
        page_files = self.get_page_files()
        if not page_files:
            self.set_selected_file(None)
            return
        if self.selected_file in page_files:
            self.set_selected_file(self.selected_file)
        else:
            self.set_selected_file(page_files[0])

    def update_pagination_controls(self):
        total_files = len(self.files_in_current_dir) if hasattr(self, "files_in_current_dir") else 0
        total_pages = self.get_total_pages()
        if hasattr(self, "page_size_var") and self.page_size_var.get() != str(self.page_size):
            self.page_size_var.set(str(self.page_size))
        if total_pages == 0:
            page_text = "ページ 0 / 0 (0件)"
        else:
            page_text = f"ページ {self.current_page} / {total_pages} ({total_files}件)"
        if hasattr(self, "page_info_var"):
            self.page_info_var.set(page_text)
        if hasattr(self, "prev_page_button"):
            if total_pages <= 1 or self.current_page <= 1:
                self.prev_page_button.state(["disabled"])
            else:
                self.prev_page_button.state(["!disabled"])
        if hasattr(self, "next_page_button"):
            if total_pages <= 1 or self.current_page >= total_pages:
                self.next_page_button.state(["disabled"])
            else:
                self.next_page_button.state(["!disabled"])

    def change_page(self, delta):
        total_pages = self.get_total_pages()
        if total_pages <= 1:
            return
        new_page = max(1, min(self.current_page + delta, total_pages))
        if new_page == self.current_page:
            return
        self.current_page = new_page
        self.selected_file = None
        self.populate_file_list(rescan=False)

    def on_page_size_change(self, event=None):
        try:
            new_size = int(self.page_size_var.get())
        except (ValueError, TypeError):
            self.page_size_var.set(str(self.page_size))
            return
        if new_size <= 0:
            new_size = self.page_size_options[0]
        if new_size == self.page_size:
            return
        self.page_size = new_size
        self.current_page = 1
        self.populate_file_list(rescan=False)

    def refresh_listbox(self):
        self._suppress_listbox_event = True
        self.file_listbox.delete(0, tk.END)
        page_files = self.get_page_files()
        for file_path in page_files:
            self.file_listbox.insert(tk.END, file_path.name)
        if self.selected_file and self.selected_file in page_files:
            index = page_files.index(self.selected_file)
            self.file_listbox.selection_set(index)
            self.file_listbox.see(index)
        self._suppress_listbox_event = False

    def refresh_thumbnail_view(self):
        for child in self.thumbnail_inner.winfo_children():
            child.destroy()
        self.thumbnail_buttons.clear()
        page_files = self.get_page_files()
        if not page_files:
            ttk.Label(self.thumbnail_inner, text="サーモ画像が見つかりません").grid(row=0, column=0, padx=10, pady=10)
            bbox = self.thumbnail_canvas.bbox("all")
            self.thumbnail_canvas.configure(scrollregion=bbox if bbox else (0, 0, 0, 0))
            return
        for idx, file_path in enumerate(page_files):
            photo = self.get_thumbnail_image(file_path)
            btn = tk.Button(
                self.thumbnail_inner,
                image=photo,
                text=file_path.name,
                compound="top",
                wraplength=self.THUMBNAIL_SIZE[0] + 10,
                relief=tk.RAISED,
                bd=2,
                justify="center",
                command=lambda p=file_path: self.on_thumbnail_click(p)
            )
            btn.grid(row=idx // self.thumbnail_columns, column=idx % self.thumbnail_columns, padx=5, pady=5, sticky="nsew")
            self.thumbnail_buttons[file_path] = btn
        for col in range(self.thumbnail_columns):
            self.thumbnail_inner.grid_columnconfigure(col, weight=1)
        if self.selected_file:
            self.update_thumbnail_selection(self.selected_file)
        self.thumbnail_canvas.yview_moveto(0)
        bbox = self.thumbnail_canvas.bbox("all")
        self.thumbnail_canvas.configure(scrollregion=bbox if bbox else (0, 0, 0, 0))

    def _on_thumbnail_canvas_configure(self, event):
        self.thumbnail_canvas.itemconfigure(self.thumbnail_window, width=event.width)

    def _on_preview_canvas_configure(self, event):
        if hasattr(self, "preview_window"):
            self.preview_canvas.itemconfigure(self.preview_window, width=event.width)
            # 高さもキャンバスに追従
            try:
                self.preview_canvas.itemconfigure(self.preview_window, height=event.height)
            except tk.TclError:
                pass

    def on_file_select(self, event=None):
        if self._suppress_listbox_event:
            return
        selection = self.file_listbox.curselection()
        if not selection:
            self.set_selected_file(None)
            return
        index = selection[0]
        page_files = self.get_page_files()
        if index >= len(page_files):
            return
        self.set_selected_file(page_files[index])

    def on_thumbnail_click(self, file_path: Path):
        self.set_selected_file(file_path)

    def set_selected_file(self, thermal_path, **_):
        thermal_path = Path(thermal_path) if thermal_path is not None else None
        self.selected_file = thermal_path
        self.update_listbox_selection(thermal_path)
        self.update_thumbnail_selection(thermal_path)
        if thermal_path:
            self.update_previews(thermal_path)
        else:
            self.clear_previews()

    def update_listbox_selection(self, thermal_path):
        self._suppress_listbox_event = True
        self.file_listbox.selection_clear(0, tk.END)
        if thermal_path:
            page_files = self.get_page_files()
            if thermal_path in page_files:
                index = page_files.index(thermal_path)
                self.file_listbox.selection_set(index)
                self.file_listbox.see(index)
        self._suppress_listbox_event = False

    def update_thumbnail_selection(self, thermal_path):
        for path, button in self.thumbnail_buttons.items():
            if thermal_path and path == thermal_path:
                button.configure(relief=tk.SUNKEN, bd=3)
            else:
                button.configure(relief=tk.RAISED, bd=2)

    def update_previews(self, thermal_path: Path):
        thermal_path = Path(thermal_path)
        if not thermal_path.exists():
            self.thermal_photo = None
            self.visible_photo = None
            self.thermal_preview.config(image="", text="ファイルが存在しません")
            self.visible_preview.config(image="", text="対応する可視画像を表示します")
            self.visible_status_var.set("")
            return
        self.visible_status_var.set("")
        thermal_size = self.get_preview_size(self.thermal_preview)
        self.thermal_photo = self.load_preview_image(thermal_path, size=thermal_size, allow_upscale=True)
        if self.thermal_photo:
            self.thermal_preview.config(image=self.thermal_photo, text="")
        else:
            self.thermal_preview.config(image="", text="プレビューできません")

        visible_path = self.find_visible_counterpart(thermal_path)
        if visible_path and visible_path.exists():
            visible_size = self.get_preview_size(self.visible_preview)
            self.visible_photo = self.load_preview_image(visible_path, size=visible_size, allow_upscale=True)
            if self.visible_photo:
                self.visible_preview.config(image=self.visible_photo, text="")
            else:
                self.visible_preview.config(image="", text="プレビューできません")
            self.visible_status_var.set(f"可視画像: {visible_path.name}")
        else:
            self.visible_photo = None
            self.visible_preview.config(image="", text="同名ファイルが見つかりません")
            self.visible_status_var.set("")

        if hasattr(self, "preview_canvas"):
            self.preview_canvas.yview_moveto(0)

    def get_preview_size(self, target_widget):
        base_width, base_height = self.PREVIEW_BASE_SIZE
        if target_widget is not None:
            try:
                target_widget.update_idletasks()
            except Exception:
                pass
            current_width = target_widget.winfo_width()
            current_height = target_widget.winfo_height()
            if isinstance(current_width, int) and current_width > 1:
                base_width = max(base_width, current_width)
            if isinstance(current_height, int) and current_height > 1:
                base_height = max(base_height, current_height)
        return (
            max(1, int(base_width * self.preview_zoom)),
            max(1, int(base_height * self.preview_zoom)),
        )

    def load_preview_image(self, path: Path, size=None, allow_upscale=True):
        try:
            with Image.open(path) as img:
                img = img.copy()
                img = img.convert("RGBA")
            target_size = size or self.PREVIEW_BASE_SIZE
            max_w, max_h = target_size
            if max_w <= 0:
                max_w = 1
            if max_h <= 0:
                max_h = 1
            orig_w, orig_h = img.size
            if orig_w <= 0 or orig_h <= 0:
                return None
            scale_w = max_w / orig_w
            scale_h = max_h / orig_h
            scale = min(scale_w, scale_h)
            if not allow_upscale:
                scale = min(scale, 1.0)
            if scale <= 0:
                scale = 1.0
            new_width = max(1, int(orig_w * scale))
            new_height = max(1, int(orig_h * scale))
            resample = Image.Resampling.LANCZOS if scale <= 1.0 else Image.Resampling.BICUBIC
            img = img.resize((new_width, new_height), resample=resample)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def get_thumbnail_image(self, path: Path):
        key = (str(path), self.THUMBNAIL_SIZE)
        if key in self.thumbnail_cache:
            return self.thumbnail_cache[key]
        try:
            with Image.open(path) as img:
                img = img.copy()
                img = img.convert("RGBA")
            img.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        except Exception:
            img = Image.new("RGB", self.THUMBNAIL_SIZE, color="#cccccc")
        photo = ImageTk.PhotoImage(img)
        self.thumbnail_cache[key] = photo
        return photo

    def adjust_preview_zoom(self, factor=None, absolute=None):
        if absolute is not None:
            new_zoom = absolute
        elif factor is not None:
            new_zoom = self.preview_zoom * factor
        else:
            return
        new_zoom = max(self.PREVIEW_MIN_ZOOM, min(self.PREVIEW_MAX_ZOOM, new_zoom))
        if abs(new_zoom - self.preview_zoom) < 1e-3:
            return
        self.preview_zoom = new_zoom
        self.update_zoom_display()
        self.refresh_current_previews()

    def update_zoom_display(self):
        if not hasattr(self, "zoom_var"):
            return
        label = None
        for option_label, value in self.zoom_options:
            if abs(value - self.preview_zoom) < 1e-3:
                label = option_label
                break
        if label is None:
            label = f"{int(self.preview_zoom * 100)}%"
        self._updating_zoom_var = True
        self.zoom_var.set(label)
        self._updating_zoom_var = False

        if hasattr(self, "zoom_out_button"):
            if self.preview_zoom <= self.PREVIEW_MIN_ZOOM + 1e-3:
                self.zoom_out_button.state(["disabled"])
            else:
                self.zoom_out_button.state(["!disabled"])
        if hasattr(self, "zoom_in_button"):
            if self.preview_zoom >= self.PREVIEW_MAX_ZOOM - 1e-3:
                self.zoom_in_button.state(["disabled"])
            else:
                self.zoom_in_button.state(["!disabled"])

    def on_zoom_combo_change(self, event=None):
        if self._updating_zoom_var:
            return
        value_str = self.zoom_var.get().replace("%", "").strip()
        try:
            value = float(value_str) / 100.0
        except ValueError:
            self.update_zoom_display()
            return
        self.adjust_preview_zoom(absolute=value)

    def refresh_current_previews(self):
        self._preview_refresh_job = None
        if self.selected_file:
            self.update_previews(self.selected_file)

    def schedule_preview_refresh(self, delay=120):
        if not hasattr(self, "window"):
            return
        if getattr(self, "_preview_refresh_job", None) is not None:
            try:
                self.window.after_cancel(self._preview_refresh_job)
            except Exception:
                pass
        try:
            self._preview_refresh_job = self.window.after(delay, self.refresh_current_previews)
        except Exception:
            self._preview_refresh_job = None

    def on_window_configure(self, event=None):
        if event is not None and event.widget is not self.window:
            return
        self.schedule_preview_refresh()

    @staticmethod
    def find_visible_counterpart(thermal_path: Path):
        try:
            stem = thermal_path.stem
            if not stem:
                return None
            if stem[-1].upper() != "T":
                return None
            counterpart_stem = stem[:-1] + "V"
            visible_dir = thermal_path.parent.parent / "可視画像"
            visible_path = visible_dir / f"{counterpart_stem}{thermal_path.suffix}"
            if visible_path.exists():
                return visible_path
            return None
        except Exception:
            return None

    def on_confirm(self):
        if not self.selected_file:
            messagebox.showwarning("警告", "サーモ画像を選択してください。", parent=self.window)
            return
        thermal_path = Path(self.selected_file)
        visible_path = self.find_visible_counterpart(thermal_path)
        if not visible_path or not visible_path.exists():
            messagebox.showwarning("警告", "同名ファイルが見つかりません。", parent=self.window)
            return
        self.result = (str(thermal_path), str(visible_path))
        self.save_layout_preferences()
        self.window.destroy()

    def on_cancel(self):
        self.result = None
        self.save_layout_preferences()
        self.window.destroy()

    def show(self):
        self.window.wait_window()
        return self.result


class OrthoImageAnnotationSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("太陽光発電所 オルソ画像アノテーションシステム v2.2")
        self.root.geometry("1200x900")


        # 変数の初期化
        self.current_image = None
        self.image_path = None
        self.annotations = []
        self.next_id = 1
        self.project_name = ""
        self.project_path = ""
        self.canvas_image = None
        self.zoom_factor = 1.0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.webodm_path = None  # WebODMフォルダのパスを保持する変数を追加
        self.last_thermal_visible_dir = None  # サーモ・可視画像同時選択用の直近フォルダ

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.annotation_icon_dir = os.path.join(base_dir, "アノテーション画像フォルダ")
        self.annotation_icon_cache = {}
        self.annotation_icon_tk_cache = {}
        self.canvas_icon_refs = []  # キャンバス上でTkイメージを保持
        self.annotation_default_icon_size = 64
        self._icon_warning_shown = False
        self._icon_dir_missing_warned = False
        self.missing_icon_types = set()

        # 不具合分類と色の設定
        self.defect_types = {
            "ホットスポット": "#FF0000",  # 赤
            "クラスタ異常": "#FF8C00",    # オレンジ
            "破損": "#FFD700",           # 黄
            "ストリング異常": "#0000FF",  # 青
            "系統異常": "#8A2BE2",       # 紫
            "影": "#008000"              # 緑
        }

        # アノテーション形状の設定
        self.annotation_shapes = {
            "十字": "cross",
            "矢印": "arrow",
            "円形": "circle",
            "四角": "rectangle"
        }

        self.annotation_scale_vars = {
            "overall": tk.StringVar(value="1.0"),
            "thermal": tk.StringVar(value="1.0"),
            "visible": tk.StringVar(value="1.0"),
        }
        self.scale_entries = {}
        
        # 画像拡張設定（個別全体図保存時に使用）
        self.image_extension_ratio = 1/3  # デフォルト: 元画像の高さの1/3を上下に追加

        self.initialize_annotation_icons()

        self.setup_ui()
        self.create_or_load_project()

    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 画像表示エリア
        image_frame = ttk.LabelFrame(main_frame, text="オルソ画像表示", padding=10)
        image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # キャンバスとスクロールバー
        canvas_frame = ttk.Frame(image_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="white", width=800, height=600)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        # キャンバスイベント
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)

        # コントロールパネル
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # ボタン群
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(button_frame, text="画像選択", command=self.select_image).pack(side=tk.LEFT, padx=(0, 5))
        # WebODMフォルダ選択ボタンを追加
        self.webodm_button = ttk.Button(button_frame, text="WebODMフォルダ選択", command=self.select_webodm_folder)
        self.webodm_button.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="画像リセット", command=self.reset_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="保存", command=self.save_project).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="中止", command=self.quit_application).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="色設定", command=self.customize_colors).pack(side=tk.LEFT, padx=(0, 5))

        scale_frame = ttk.Frame(button_frame)
        scale_frame.pack(side=tk.LEFT, padx=(5, 0))

        scale_config = [
            ("全体", "overall"),
            ("サーモ", "thermal"),
            ("可視", "visible"),
        ]
        for label, key in scale_config:
            ttk.Label(scale_frame, text=f"{label}×").pack(side=tk.LEFT)
            entry = ttk.Entry(scale_frame, width=5, textvariable=self.annotation_scale_vars[key], justify="right")
            entry.pack(side=tk.LEFT, padx=(0, 5))
            self.scale_entries[key] = entry

        # 設定選択エリア
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(side=tk.RIGHT)

        # 不良分類選択
        ttk.Label(settings_frame, text="不良分類:").pack(side=tk.LEFT, padx=(0, 5))
        self.defect_var = tk.StringVar(value=list(self.defect_types.keys())[0])
        self.defect_combo = ttk.Combobox(settings_frame, textvariable=self.defect_var, 
                                        values=list(self.defect_types.keys()), 
                                        state="readonly", width=15)
        self.defect_combo.pack(side=tk.LEFT, padx=(0, 10))

        # 形状選択
        ttk.Label(settings_frame, text="形状:").pack(side=tk.LEFT, padx=(0, 5))
        self.shape_var = tk.StringVar(value=list(self.annotation_shapes.keys())[0])
        self.shape_combo = ttk.Combobox(settings_frame, textvariable=self.shape_var, 
                                       values=list(self.annotation_shapes.keys()), 
                                       state="readonly", width=10)
        self.shape_combo.pack(side=tk.LEFT)

        # 不具合テーブル
        table_frame = ttk.LabelFrame(main_frame, text="不具合テーブル", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview - 列を追加
        columns = ("ID", "エリア番号", "PCS番号", "接続箱番号", "回路番号", "アレイ№", "モジュール位置", "シリアル№", "不良分類", "形状", "サーモ画像", "可視画像", "備考", "報告年月日")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)

        # 列の設定
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "ID":
                self.tree.column(col, width=50, anchor="center")
            elif col in ["エリア番号", "PCS番号", "接続箱番号", "回路番号", "アレイ№"]:
                self.tree.column(col, width=80, anchor="center")
            elif col in ["モジュール位置", "シリアル№"]:
                self.tree.column(col, width=100, anchor="center")
            elif col in ["不良分類", "形状"]:
                self.tree.column(col, width=100, anchor="center")
            elif col in ["サーモ画像", "可視画像"]:
                self.tree.column(col, width=120, anchor="center")
            elif col == "報告年月日":
                self.tree.column(col, width=100, anchor="center")
            else:
                self.tree.column(col, width=150, anchor="w")

    # （後半部分は変更なし）

        # スクロールバー
        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # テーブルイベント
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Delete>", self.delete_annotation)

    def select_webodm_folder(self):
        """WebODMのアセットフォルダを選択し、オルソ画像を自動で読み込む"""
        folder_path = filedialog.askdirectory(title="WebODMアセットフォルダを選択")
        if not folder_path:
            return

        # WebODMの主要なファイルの存在をチェック
        geo_ref_path = os.path.join(folder_path, 'odm_georeferencing', 'odm_georeferencing_model_geo.txt')
        coverage_path = os.path.join(folder_path, 'images', 'shot_coverage.png')
        ortho_path = os.path.join(folder_path, 'odm_orthophoto', 'odm_orthophoto.tif')

        if os.path.exists(geo_ref_path) and os.path.exists(ortho_path):
            self.webodm_path = folder_path
            messagebox.showinfo("成功", f"WebODMフォルダを設定しました:\n{folder_path}\nオルソ画像を自動で読み込みます。")
            # メインのオルソ画像を自動で読み込む
            self.load_image(ortho_path)
        else:
            messagebox.showerror("エラー", "選択されたフォルダに必要なWebODMアセットが見つかりません。\n- odm_georeferencing/odm_georeferencing_model_geo.(txt|csv)\n- odm_orthophoto/odm_orthophoto.(tif|tiff|png)\nを確認してください。")
            self.webodm_path = None


    def create_or_load_project(self):
        """新しいプロジェクトを作成または既存プロジェクトを読み込み"""
        dialog = tk.Toplevel(self.root)
        dialog.title("プロジェクト選択")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # プロジェクト選択フレーム
        project_frame = ttk.LabelFrame(dialog, text="プロジェクト", padding=10)
        project_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 新規プロジェクト
        new_project_frame = ttk.Frame(project_frame)
        new_project_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(new_project_frame, text="新規プロジェクト名:").pack(side=tk.LEFT)
        self.project_name_entry = ttk.Entry(new_project_frame, width=20)
        self.project_name_entry.pack(side=tk.LEFT, padx=(5, 0))

        # ボタンフレーム
        button_frame = ttk.Frame(project_frame)
        button_frame.pack(fill=tk.X, pady=10)

        def create_new_project():
            project_name = self.project_name_entry.get().strip()
            if not project_name:
                project_name = f"Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.project_name = project_name
            self.project_path = os.path.join(os.getcwd(), self.project_name)
            
            # プロジェクトフォルダ作成
            os.makedirs(self.project_path, exist_ok=True)
            os.makedirs(os.path.join(self.project_path, "アノテーション設定フォルダ"), exist_ok=True)
            os.makedirs(os.path.join(self.project_path, "サーモ画像フォルダ"), exist_ok=True)
            os.makedirs(os.path.join(self.project_path, "可視画像フォルダ"), exist_ok=True)
            os.makedirs(os.path.join(self.project_path, "不具合一覧表フォルダ"), exist_ok=True)
            os.makedirs(os.path.join(self.project_path, "アノテーション入り画像フォルダ"), exist_ok=True)
            os.makedirs(os.path.join(self.project_path, "全体図位置フォルダ"), exist_ok=True)  # 追加

            self.root.title(f"太陽光発電所 オルソ画像アノテーションシステム v2.1.2 - {self.project_name}")
            dialog.destroy()

        def load_existing_project():
            folder_path = filedialog.askdirectory(title="既存プロジェクトフォルダを選択")
            if folder_path:
                self.project_path = folder_path
                self.project_name = os.path.basename(folder_path)
                
                # アノテーション設定フォルダが存在するかチェック
                annotation_folder = os.path.join(self.project_path, "アノテーション設定フォルダ")
                if os.path.exists(annotation_folder):
                    # 既存のアノテーションを読み込み
                    self.load_annotations()
                    
                    # 画像パスが保存されていれば自動で読み込み
                    if self.image_path and os.path.exists(self.image_path):
                        self.load_image(self.image_path)
                    
                    self.root.title(f"太陽光発電所 オルソ画像アノテーションシステム v2.1 - {self.project_name}")
                    dialog.destroy()
                else:
                    messagebox.showerror("エラー", "有効なプロジェクトフォルダではありません。")

        ttk.Button(button_frame, text="新規作成", command=create_new_project).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="既存プロジェクト読み込み", command=load_existing_project).pack(side=tk.LEFT)

    def select_image(self):
        """画像を選択して表示"""
        file_path = filedialog.askopenfilename(
            title="オルソ画像を選択",
            filetypes=[("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"), ("すべてのファイル", "*.*")]
        )

        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path):
        """画像を読み込んで表示"""
        try:
            self.image_path = file_path
            self.current_image = Image.open(file_path)
            self.zoom_factor = 1.0
            self.display_image()

        except Exception as e:
            # Pillowで読めないGeoTIFFなどに対するフォールバック
            try:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.tif', '.tiff']:
                    # まずtifffileで試す（float/BIGTIFF/圧縮に強い）
                    pil_img = self._read_tiff_with_tifffile(file_path)
                    if pil_img is None:
                        # 次にOpenCV（日本語パス対策: np.fromfile + imdecode）
                        try:
                            data = np.fromfile(file_path, dtype=np.uint8)
                            img_cv = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
                        except Exception:
                            img_cv = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
                        if img_cv is not None:
                            # 16/32bit想定 → 8bit正規化
                            if img_cv.dtype != np.uint8:
                                img_cv = cv2.normalize(img_cv, None, 0, 255, cv2.NORM_MINMAX)
                                img_cv = img_cv.astype(np.uint8)
                            if len(img_cv.shape) == 2:
                                pil_img = Image.fromarray(img_cv).convert('RGB')
                            elif len(img_cv.shape) == 3:
                                c = img_cv.shape[2]
                                if c == 3:
                                    pil_img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
                                elif c == 4:
                                    pil_img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGRA2RGBA))
                                elif c > 4:
                                    pil_img = Image.fromarray(cv2.cvtColor(img_cv[:, :, :3], cv2.COLOR_BGR2RGB))
                    if pil_img is not None:
                        self.current_image = pil_img
                        self.zoom_factor = 1.0
                        self.display_image()
                        return
                # WebODMのプレビューへフォールバック
                if getattr(self, 'webodm_path', None):
                    for p in [
                        os.path.join(self.webodm_path, 'odm_orthophoto', 'odm_orthophoto.png'),
                        os.path.join(self.webodm_path, 'odm_orthophoto', 'odm_orthophoto_preview.png'),
                    ]:
                        if os.path.exists(p):
                            self.image_path = p
                            self.current_image = Image.open(p)
                            self.zoom_factor = 1.0
                            self.display_image()
                            return
            except Exception:
                pass
            messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {str(e)}")

    def _read_tiff_with_tifffile(self, file_path):
        """tifffileでTIFFを読む（float/BIGTIFF/各種圧縮に強い）→ PIL.Imageに変換"""
        try:
            import tifffile as tiff
            arr = tiff.imread(file_path)
            # 正規化して8bitへ（NaN/Inf対応）
            if arr.dtype != np.uint8:
                arrf = arr.astype(np.float32)
                finite = np.isfinite(arrf)
                if not finite.any():
                    arr8 = np.zeros(arr.shape[:2], dtype=np.uint8)
                else:
                    vmin = float(arrf[finite].min())
                    vmax = float(arrf[finite].max())
                    if vmax - vmin < 1e-12:
                        arr8 = np.zeros(arr.shape[:2], dtype=np.uint8)
                    else:
                        arr8 = np.clip((arrf - vmin) / (vmax - vmin) * 255.0, 0, 255).astype(np.uint8)
            else:
                arr8 = arr
            if arr8.ndim == 2:
                return Image.fromarray(arr8).convert('RGB')
            elif arr8.ndim == 3:
                c = arr8.shape[2]
                if c == 3:
                    return Image.fromarray(arr8)
                elif c >= 4:
                    return Image.fromarray(arr8[:, :, :3])
                else:
                    # 1ch/2chなどは先頭chをRGB化
                    return Image.fromarray(arr8[:, :, 0]).convert('RGB')
        except Exception:
            return None

    def _read_tiff_with_opencv_unicode(self, file_path):
        """np.fromfile + cv2.imdecodeで日本語パス/float系も正規化してPIL化"""
        try:
            data = np.fromfile(file_path, dtype=np.uint8)
            if data is None or data.size == 0:
                return None
            img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
            if img is None:
                img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                return None
            if img.dtype != np.uint8:
                img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
                img = img.astype(np.uint8)
            if len(img.shape) == 2:
                return Image.fromarray(img).convert('RGB')
            elif len(img.shape) == 3:
                c = img.shape[2]
                if c == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    return Image.fromarray(img)
                elif c == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
                    return Image.fromarray(img)
                elif c > 4:
                    img = img[:, :, :3]
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    return Image.fromarray(img)
            return None
        except Exception:
            return None

    def display_image(self):
        """画像をキャンバスに表示"""
        if self.current_image:
            # ズーム適用
            display_size = (
                int(self.current_image.width * self.zoom_factor),
                int(self.current_image.height * self.zoom_factor)
            )
            resized_image = self.current_image.resize(display_size, Image.Resampling.LANCZOS)
            self.canvas_image = ImageTk.PhotoImage(resized_image)

            # キャンバスクリア
            self.canvas.delete("all")

            # 画像表示
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.canvas_image)

            # スクロール領域設定
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            # アノテーション描画
            self.draw_annotations()

    def initialize_annotation_icons(self, reset_warning=True):
        """アノテーションアイコンを初期化し、フォルダから読み込む"""
        if reset_warning:
            self._icon_warning_shown = False
        self.missing_icon_types.clear()
        self.annotation_icon_cache.clear()
        self.annotation_icon_tk_cache.clear()

        icon_dir = self.annotation_icon_dir
        if not os.path.isdir(icon_dir):
            if not self._icon_dir_missing_warned:
                messagebox.showwarning(
                    "アノテーションアイコン",
                    "プログラムと同じフォルダにある『アノテーション画像フォルダ』からアイコンを読み込めませんでした。\n"
                    "フォルダ配置とアクセス権限を確認してください。"
                )
                self._icon_dir_missing_warned = True
            return

        self._icon_dir_missing_warned = False

        for defect_type in self.defect_types.keys():
            self.load_annotation_icon(defect_type)

    def get_annotation_icon_path(self, defect_type):
        sanitized = str(defect_type or "").strip()
        if not sanitized:
            return None
        sanitized = sanitized.replace("/", "_").replace("\\", "_")
        return os.path.join(self.annotation_icon_dir, f"{sanitized}.svg")

    def load_annotation_icon(self, defect_type):
        if defect_type in self.annotation_icon_cache:
            return self.annotation_icon_cache[defect_type]

        path = self.get_annotation_icon_path(defect_type)
        if not path or not os.path.exists(path):
            self.annotation_icon_cache[defect_type] = None
            self._register_missing_icon(defect_type, f"ファイルが見つかりません: {path}")
            return None

        if not _CAIROSVG_AVAILABLE:
            self.annotation_icon_cache[defect_type] = None
            self._register_missing_icon(defect_type, "cairosvg がインストールされていません")
            return None

        try:
            png_bytes = cairosvg.svg2png(url=path, output_width=256)
            image = Image.open(BytesIO(png_bytes)).convert("RGBA")
            self.annotation_icon_cache[defect_type] = image
            return image
        except Exception as e:
            self.annotation_icon_cache[defect_type] = None
            self._register_missing_icon(defect_type, f"SVG変換に失敗しました: {e}")
            return None

    def _register_missing_icon(self, defect_type, message):
        if defect_type in self.missing_icon_types:
            return
        self.missing_icon_types.add(defect_type)
        print(f"[WARN] annotation icon missing for '{defect_type}': {message}")
        if not self._icon_warning_shown:
            messagebox.showwarning(
                "アノテーションアイコン",
                "アノテーション用SVGアイコンを読み込めませんでした。\n"
                "フォルダ『アノテーション画像フォルダ』と cairosvg のインストール状況を確認してください。"
            )
            self._icon_warning_shown = True

    def get_tk_icon(self, defect_type, size):
        size = max(16, int(size))
        key = (defect_type, size)
        if key in self.annotation_icon_tk_cache:
            return self.annotation_icon_tk_cache[key]

        base_icon = self.load_annotation_icon(defect_type)
        if base_icon is None:
            return None

        if base_icon.size != (size, size):
            icon_image = base_icon.resize((size, size), Image.Resampling.LANCZOS)
        else:
            icon_image = base_icon

        tk_icon = ImageTk.PhotoImage(icon_image)
        self.annotation_icon_tk_cache[key] = tk_icon
        return tk_icon

    def _get_annotation_scale(self, key):
        var = self.annotation_scale_vars.get(key)
        if var is None:
            var = self.annotation_scale_vars.get("overall")
        if var is None:
            return 1.0
        value = var.get()
        try:
            scale = float(value)
            if not math.isfinite(scale) or scale <= 0:
                raise ValueError
            return scale
        except (TypeError, ValueError):
            scale = 1.0
            try:
                var.set("1.0")
            except Exception:
                pass
            return scale

    def _draw_id_label_on_image(self, draw, x, y, annotation_id, color, image_size, scale_multiplier=1.0, icon_height=None):
        img_w, img_h = image_size
        base_font_size = max(12, min(24, int(min(img_w, img_h) / 50))) if img_w and img_h else 12
        font_size = max(8, int(round(base_font_size * scale_multiplier)))
        font_size = min(font_size, 128)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("Arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
        stroke_width = max(1, int(round(2 * scale_multiplier)))
        offset = 25 * scale_multiplier
        if icon_height:
            offset = max(offset, (icon_height / 2) + 6 * scale_multiplier)
        text_x = x + offset
        text_y = y - offset
        if img_w:
            text_x = max(0, min(img_w - 1, text_x))
        if img_h:
            text_y = max(0, min(img_h - 1, text_y))
        draw.text(
            (text_x, text_y),
            f"ID{annotation_id}",
            fill=color,
            stroke_width=stroke_width,
            stroke_fill="white",
            font=font,
        )

    def draw_annotations(self):
        """アノテーションを描画"""
        self.canvas_icon_refs.clear()
        for annotation in self.annotations:
            self.canvas.delete(f"annotation_{annotation['id']}")
            x = annotation["x"] * self.zoom_factor
            y = annotation["y"] * self.zoom_factor
            defect_type = annotation.get("defect_type")
            color = self.defect_types.get(defect_type, "#FF0000")

            icon_size = max(24, int(self.annotation_default_icon_size * self.zoom_factor))
            tk_icon = self.get_tk_icon(defect_type, icon_size)

            if tk_icon is None:
                icon_path = self.get_annotation_icon_path(defect_type)
                if icon_path and os.path.isfile(icon_path):
                    self.initialize_annotation_icons(reset_warning=False)
                    tk_icon = self.get_tk_icon(defect_type, icon_size)

            if tk_icon:
                self.canvas.create_image(
                    x, y,
                    image=tk_icon,
                    anchor=tk.CENTER,
                    tags=f"annotation_{annotation['id']}"
                )
                self.canvas_icon_refs.append(tk_icon)

                label_offset = (tk_icon.height() / 2) + 12 * self.zoom_factor
                self.draw_id_text(x, y - label_offset, color, annotation['id'])
                continue

            shape = annotation.get("shape", "cross")

            # 形状に応じて描画
            if shape == "cross":
                self.draw_cross(x, y, color, annotation['id'])
            elif shape == "arrow":
                self.draw_arrow(x, y, color, annotation['id'])
            elif shape == "circle":
                self.draw_circle(x, y, color, annotation['id'])
            elif shape == "rectangle":
                self.draw_rectangle(x, y, color, annotation['id'])

    def draw_annotation_icon_on_image(self, image, draw, x, y, defect_type, color, fallback_shape, scale_multiplier=1.0):
        try:
            scale_multiplier = float(scale_multiplier)
        except (TypeError, ValueError):
            scale_multiplier = 1.0
        if not math.isfinite(scale_multiplier) or scale_multiplier <= 0:
            scale_multiplier = 1.0

        base_icon = self.load_annotation_icon(defect_type)
        if base_icon is not None:
            icon_w, icon_h = base_icon.size
            base_length = max(image.width, image.height)
            min_dim = max(1, min(image.width, image.height))
            base_target = min(max(24, int(base_length * 0.05)), max(16, min_dim), 128)
            target_edge = max(4, int(round(base_target * scale_multiplier)))
            target_edge = min(target_edge, min_dim)
            scale = target_edge / max(icon_w, icon_h) if max(icon_w, icon_h) else 1.0
            resized_size = (
                max(1, int(round(icon_w * scale))),
                max(1, int(round(icon_h * scale)))
            )
            icon_image = base_icon.resize(resized_size, Image.Resampling.LANCZOS) if resized_size != base_icon.size else base_icon

            paste_x = int(round(x - icon_image.width / 2))
            paste_y = int(round(y - icon_image.height / 2))
            paste_x = max(0, min(image.width - icon_image.width, paste_x))
            paste_y = max(0, min(image.height - icon_image.height, paste_y))

            image.paste(icon_image, (paste_x, paste_y), icon_image)
            return icon_image.height

        if fallback_shape == "cross":
            return self.draw_cross_on_image(draw, x, y, color, scale_multiplier)
        elif fallback_shape == "arrow":
            return self.draw_arrow_on_image(draw, x, y, color, scale_multiplier)
        elif fallback_shape == "circle":
            return self.draw_circle_on_image(draw, x, y, color, scale_multiplier)
        elif fallback_shape == "rectangle":
            return self.draw_rectangle_on_image(draw, x, y, color, scale_multiplier)
        else:
            return self.draw_cross_on_image(draw, x, y, color, scale_multiplier)

    def draw_cross(self, x, y, color, annotation_id):
        """十字形状を描画"""
        size = 20 * self.zoom_factor
        self.canvas.create_line(
            x, y - size, x, y + size,
            fill=color, width=3, tags=f"annotation_{annotation_id}"
        )
        self.canvas.create_line(
            x - size, y, x + size, y,
            fill=color, width=3, tags=f"annotation_{annotation_id}"
        )
        self.draw_id_text(x, y - size - 15 * self.zoom_factor, color, annotation_id)

    def draw_arrow(self, x, y, color, annotation_id):
        """矢印形状を描画"""
        size = 20 * self.zoom_factor
        # 矢印の軸
        self.canvas.create_line(
            x, y - size, x, y + size,
            fill=color, width=3, tags=f"annotation_{annotation_id}"
        )
        # 矢印の先端
        self.canvas.create_polygon(
            x, y - size,
            x - 8 * self.zoom_factor, y - size + 15 * self.zoom_factor,
            x + 8 * self.zoom_factor, y - size + 15 * self.zoom_factor,
            fill=color, tags=f"annotation_{annotation_id}"
        )
        self.draw_id_text(x, y - size - 15 * self.zoom_factor, color, annotation_id)

    def draw_circle(self, x, y, color, annotation_id):
        """円形状を描画"""
        radius = 25 * self.zoom_factor
        self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius,
            outline=color, width=3, tags=f"annotation_{annotation_id}"
        )
        self.draw_id_text(x, y - radius - 15 * self.zoom_factor, color, annotation_id)

    def draw_rectangle(self, x, y, color, annotation_id):
        """四角形状を描画"""
        size = 20 * self.zoom_factor
        self.canvas.create_rectangle(
            x - size, y - size, x + size, y + size,
            outline=color, width=3, tags=f"annotation_{annotation_id}"
        )
        self.draw_id_text(x, y - size - 15 * self.zoom_factor, color, annotation_id)

    def draw_id_text(self, x, y, color, annotation_id):
        """ID番号を描画"""
        text_size = max(10, int(12 * self.zoom_factor))
        
        # 背景付きテキスト表示
        text_id = self.canvas.create_text(
            x, y,
            text=f"ID{annotation_id}",
            fill="white",
            font=("Arial", text_size, "bold"),
            anchor="center",
            tags=f"annotation_{annotation_id}"
        )

        # テキストの背景
        bbox = self.canvas.bbox(text_id)
        if bbox:
            self.canvas.create_rectangle(
                bbox[0] - 2, bbox[1] - 1,
                bbox[2] + 2, bbox[3] + 1,
                fill=color, outline=color,
                tags=f"annotation_{annotation_id}"
            )
            # テキストを前面に移動
            self.canvas.tag_raise(text_id)

    def _confirm_id_change(self, old_id, new_id, parent=None):
        if old_id == new_id:
            return True
        try:
            old_id_str = f"ID{int(old_id)}"
        except (TypeError, ValueError):
            old_id_str = f"ID{old_id}"
        confirm_message = (
            f"{old_id_str} を ID{new_id} に変更します。\n"
            "重複しているIDがある場合は、後続のID番号を自動で繰り上げます。\n"
            "よろしいですか？"
        )
        return messagebox.askokcancel("ID番号の変更", confirm_message, parent=parent)

    def apply_annotation_id_change(self, annotation, new_id, parent=None, notify_conflicts=True):
        if annotation not in self.annotations:
            return
        try:
            new_id_int = int(new_id)
        except (TypeError, ValueError):
            raise ValueError("ID番号は整数で指定してください。")

        if new_id_int <= 0:
            raise ValueError("ID番号は 1 以上である必要があります。")

        previous_ids = {id(ann): ann.get('id') for ann in self.annotations}
        annotation['id'] = new_id_int
        self._resolve_id_conflicts(annotation)

        changed_annotations = []
        for ann in self.annotations:
            previous_id = previous_ids.get(id(ann))
            if previous_id is not None and previous_id != ann.get('id'):
                changed_annotations.append((ann, previous_id, ann.get('id')))

        if changed_annotations:
            for target_annotation, old_id, updated_id in changed_annotations:
                self._update_annotation_files_for_id_change(target_annotation, old_id, updated_id)

        order_map = {id(ann): idx for idx, ann in enumerate(self.annotations)}
        self.annotations.sort(key=lambda ann: (ann.get('id', 0), order_map.get(id(ann), 0)))

        if self.annotations:
            self.next_id = max(ann.get('id', 0) for ann in self.annotations) + 1
        else:
            self.next_id = 1

        self.update_table()
        self.draw_annotations()
        self._select_tree_item_by_id(annotation.get('id'))

        if notify_conflicts and len(changed_annotations) > 1:
            info_lines = [
                f"ID{old_id} → ID{updated_id}"
                for ann_obj, old_id, updated_id in changed_annotations
                if ann_obj is not annotation
            ]
            if info_lines:
                messagebox.showinfo(
                    "ID番号の更新",
                    "重複していたIDを次番号へ繰り上げました:\n" + "\n".join(info_lines),
                    parent=parent
                )

    def _resolve_id_conflicts(self, primary_annotation):
        order_map = {id(ann): idx for idx, ann in enumerate(self.annotations)}
        sorted_candidates = sorted(
            self.annotations,
            key=lambda ann: (
                ann.get('id', 0),
                0 if ann is primary_annotation else 1,
                order_map.get(id(ann), 0)
            )
        )

        seen_ids = set()
        for ann in sorted_candidates:
            current_id = int(ann.get('id', 0) or 0)
            if current_id <= 0:
                current_id = 1
            while current_id in seen_ids:
                current_id += 1
            if current_id != ann.get('id'):
                ann['id'] = current_id
            seen_ids.add(current_id)

    def _is_path_inside_project(self, path):
        if not path or not self.project_path:
            return False
        try:
            project_root = os.path.abspath(self.project_path)
            target_path = os.path.abspath(path)
            return os.path.commonpath([project_root, target_path]) == project_root
        except Exception:
            return False

    def _rename_file_with_new_id(self, path, old_id, new_id):
        if not path:
            return path
        try:
            resolved_path = os.path.abspath(path)
        except Exception:
            resolved_path = path
        if not os.path.exists(resolved_path):
            return path
        if not self._is_path_inside_project(resolved_path):
            return path

        directory, filename = os.path.split(resolved_path)
        match = re.search(r"ID(\d+)", filename)
        if not match:
            return path

        original_digits = match.group(1)
        new_digits = str(new_id).zfill(len(original_digits))
        new_filename = f"{filename[:match.start(1)]}{new_digits}{filename[match.end(1):]}"
        new_path = os.path.join(directory, new_filename)

        if new_path == resolved_path:
            return path

        try:
            os.makedirs(directory, exist_ok=True)
            os.replace(resolved_path, new_path)
            return new_path
        except Exception as e:
            print(f"[WARN] ファイル名を変更できませんでした: {resolved_path} -> {new_path} ({e})")
            return path

    def _update_annotation_files_for_id_change(self, annotation, old_id, new_id):
        if old_id == new_id:
            return
        for key in [
            "thermal_image",
            "visible_image",
            "thermal_annotated_image",
            "visible_annotated_image"
        ]:
            path = annotation.get(key)
            new_path = self._rename_file_with_new_id(path, old_id, new_id)
            if new_path and new_path != path:
                annotation[key] = new_path

    def find_annotation_by_id(self, annotation_id):
        for annotation in self.annotations:
            try:
                if int(annotation.get('id')) == int(annotation_id):
                    return annotation
            except (TypeError, ValueError):
                continue
        return None

    def _select_tree_item_by_id(self, annotation_id):
        if annotation_id is None:
            return
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if values and str(values[0]) == str(annotation_id):
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
                break

    def prompt_id_change_from_table(self, annotation):
        if not annotation:
            return
        old_id = annotation.get('id')
        new_id = simpledialog.askinteger(
            "ID番号の編集",
            f"ID{old_id} を新しい番号に変更します。\n1以上の整数を入力してください。",
            initialvalue=old_id,
            minvalue=1,
            parent=self.root
        )
        if new_id is None or new_id == old_id:
            return
        if not self._confirm_id_change(old_id, new_id, parent=self.root):
            return
        try:
            self.apply_annotation_id_change(annotation, new_id, parent=self.root)
        except ValueError as e:
            messagebox.showwarning("警告", str(e), parent=self.root)

    def on_tree_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        item = self.tree.item(row_id)
        values = item.get("values")
        if not values:
            return
        try:
            annotation_id = int(values[0])
        except (TypeError, ValueError):
            return

        annotation = self.find_annotation_by_id(annotation_id)
        if not annotation:
            return

        column_id = self.tree.identify_column(event.x)
        if column_id == "#1":
            self.prompt_id_change_from_table(annotation)
        else:
            self.edit_annotation_dialog(annotation)

    def on_canvas_click(self, event):
        """キャンバスクリック時の処理"""
        if self.current_image:
            # キャンバス座標を画像座標に変換
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)

            image_x = canvas_x / self.zoom_factor
            image_y = canvas_y / self.zoom_factor

            # 画像範囲内かチェック
            if 0 <= image_x <= self.current_image.width and 0 <= image_y <= self.current_image.height:
                self.add_annotation(image_x, image_y)

    def add_annotation(self, x, y):
        """アノテーションを追加"""
        defect_type = self.defect_var.get()
        shape = self.annotation_shapes[self.shape_var.get()]

        annotation = {
            "id": self.next_id,
            "x": x,
            "y": y,
            "defect_type": defect_type,
            "shape": shape,
            "area_no": "",
            "pcs_no": "",
            "junction_box_no": "",
            "circuit_no": "",
            "array_no": "",           # 追加
            "module_position": "",    # 追加
            "serial_no": "",          # 追加
            "thermal_image": "",
            "visible_image": "",
            "remarks": "",
            "found_by": None,
            "management_level": 'S',
            "report_date": datetime.now().strftime('%Y-%m-%d')  # 追加（現在日付を自動設定）
        }

        self.annotations.append(annotation)
        self.next_id += 1

        self.update_table()
        self.draw_annotations()

    def on_canvas_double_click(self, event):
        """ダブルクリックでアノテーション編集"""
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # 最も近いアノテーションを検索
        min_distance = float('inf')
        selected_annotation = None

        for annotation in self.annotations:
            ann_x = annotation["x"] * self.zoom_factor
            ann_y = annotation["y"] * self.zoom_factor
            distance = ((canvas_x - ann_x) ** 2 + (canvas_y - ann_y) ** 2) ** 0.5

            if distance < 30 and distance < min_distance:
                min_distance = distance
                selected_annotation = annotation

        if selected_annotation:
            self.edit_annotation_dialog(selected_annotation)

    def on_canvas_right_click(self, event):
        """右クリックでアノテーション削除"""
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # 最も近いアノテーションを検索
        min_distance = float('inf')
        selected_annotation = None

        for annotation in self.annotations:
            ann_x = annotation["x"] * self.zoom_factor
            ann_y = annotation["y"] * self.zoom_factor
            distance = ((canvas_x - ann_x) ** 2 + (canvas_y - ann_y) ** 2) ** 0.5

            if distance < 30 and distance < min_distance:
                min_distance = distance
                selected_annotation = annotation

        if selected_annotation:
            if messagebox.askyesno("確認", f"ID{selected_annotation['id']}のアノテーションを削除しますか？"):
                self.delete_annotation_by_id(selected_annotation['id'])

    def delete_annotation_by_id(self, annotation_id):
        """指定されたIDのアノテーションを削除し、ID番号を振り直し"""
        # キャンバスからアノテーション画像を削除
        self.canvas.delete(f"annotation_{annotation_id}")
        
        # アノテーションを削除
        self.annotations = [ann for ann in self.annotations if ann['id'] != annotation_id]

        # ID番号を振り直し
        self.reassign_ids()

        # 表示を更新
        self.update_table()
        self.draw_annotations()

    def reassign_ids(self):
        """ID番号を1から連番で振り直し"""
        if not self.annotations:
            self.next_id = 1
            return

        order_map = {id(ann): idx for idx, ann in enumerate(self.annotations)}
        self.annotations.sort(key=lambda ann: (ann.get('id', 0), order_map.get(id(ann), 0)))

        changed = []
        for index, annotation in enumerate(self.annotations, 1):
            current_id = annotation.get('id')
            if current_id != index:
                changed.append((annotation, current_id, index))
                annotation['id'] = index

        if changed:
            for ann, old_id, new_id in changed:
                self._update_annotation_files_for_id_change(ann, old_id, new_id)

        self.next_id = len(self.annotations) + 1

    def delete_annotation(self, event):
        """テーブルからアノテーション削除"""
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item[0])
            annotation_id = int(item['values'][0])

            if messagebox.askyesno("確認", f"ID{annotation_id}のアノテーションを削除しますか？"):
                self.delete_annotation_by_id(annotation_id)

    def edit_annotation(self, event):
        """テーブルからアノテーション編集"""
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item[0])
            annotation_id = int(item['values'][0])

            annotation = next((ann for ann in self.annotations if ann['id'] == annotation_id), None)
            if annotation:
                self.edit_annotation_dialog(annotation)

    def edit_annotation_dialog_legacy(self, annotation):
        """アノテーション編集ダイアログ"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"ID{annotation['id']} 編集")
        dialog.geometry("400x750")  # 高さを増加
        dialog.transient(self.root)
        dialog.grab_set()

        # 入力フィールド - 項目を追加
        fields = [
            ("エリア番号", "area_no"),
            ("PCS番号", "pcs_no"),
            ("接続箱番号", "junction_box_no"),
            ("回路番号", "circuit_no"),
            ("アレイ№", "array_no"),           # 追加
            ("モジュール位置", "module_position"), # 追加
            ("シリアル№", "serial_no"),         # 追加
            ("備考", "remarks"),
            ("報告年月日", "report_date")        # 追加
        ]

        entries = {}

        for i, (label, key) in enumerate(fields):
            ttk.Label(dialog, text=f"{label}:").grid(row=i, column=0, sticky="w", padx=10, pady=5)
            
            if key == "report_date":
                # 日付入力用のエントリ（カレンダー形式にしたい場合は別途実装）
                entry = ttk.Entry(dialog, width=30)
                # 既存の日付があればそれを、なければ現在日付を設定
                current_date = annotation.get(key, datetime.now().strftime('%Y-%m-%d'))
                entry.insert(0, current_date)
            else:
                entry = ttk.Entry(dialog, width=30)
                entry.insert(0, annotation.get(key, ""))
            
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[key] = entry

        # 不良分類選択
        # 管理レベル選択
        ttk.Label(dialog, text="管理レベル:").grid(row=len(fields), column=0, sticky="w", padx=10, pady=5)
        mgmt_var = tk.StringVar(value=(annotation.get("management_level") or 'S'))
        mgmt_combo = ttk.Combobox(dialog, values=['S','A','B','N'], state="readonly", width=27, textvariable=mgmt_var)
        mgmt_combo.grid(row=len(fields), column=1, padx=10, pady=5)

        # 不良分類選択
        ttk.Label(dialog, text="不良分類:").grid(row=len(fields)+1, column=0, sticky="w", padx=10, pady=5)
        defect_combo = ttk.Combobox(dialog, values=list(self.defect_types.keys()), 
                                state="readonly", width=27)
        defect_combo.set(annotation.get("defect_type", ""))
        defect_combo.grid(row=len(fields)+1, column=1, padx=10, pady=5)

        # 形状選択
        ttk.Label(dialog, text="形状:").grid(row=len(fields)+2, column=0, sticky="w", padx=10, pady=5)
        shape_combo = ttk.Combobox(dialog, values=list(self.annotation_shapes.keys()), 
                                state="readonly", width=27)
        current_shape = annotation.get("shape", "cross")
        shape_name = next((k for k, v in self.annotation_shapes.items() if v == current_shape), "十字")
        shape_combo.set(shape_name)
        shape_combo.grid(row=len(fields)+2, column=1, padx=10, pady=5)

        # 画像選択ボタン（ODM機能付き）
        def select_thermal_visible_pair():
            candidates = [
                annotation.get("thermal_image"),
                annotation.get("visible_image"),
                self.last_thermal_visible_dir
            ]
            initial_dir = None
            for candidate in candidates:
                if not candidate:
                    continue
                candidate_dir = candidate if os.path.isdir(candidate) else os.path.dirname(candidate)
                if candidate_dir and os.path.isdir(candidate_dir):
                    initial_dir = candidate_dir
                    break
            selector = ThermalVisibleFileDialog(dialog, initial_dir=initial_dir)
            result = selector.show()
            if result:
                thermal_path, visible_path = result
                annotation["thermal_image"] = thermal_path
                annotation["visible_image"] = visible_path
                self.last_thermal_visible_dir = os.path.dirname(thermal_path)
                thermal_label.config(text=f"サーモ画像: {os.path.basename(thermal_path)}")
                visible_label.config(text=f"可視画像: {os.path.basename(visible_path)}")

        def select_thermal_image():
            file_path = filedialog.askopenfilename(
                title="サーモ画像を選択",
                filetypes=[("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif")]
            )
            if file_path:
                annotation["thermal_image"] = file_path
                self.last_thermal_visible_dir = os.path.dirname(file_path)
                thermal_label.config(text=f"サーモ画像: {os.path.basename(file_path)}")


        def select_thermal_image_odm():
            # WebODMフォルダが選択されているかチェック
            if not self.webodm_path:
                messagebox.showwarning("警告", "メイン画面で「WebODMフォルダ選択」ボタンからアセットフォルダを先に選択してください。")
                return
            
            def callback(selected_path):
                annotation["thermal_image"] = selected_path
                self.last_thermal_visible_dir = os.path.dirname(selected_path)
                thermal_label.config(text=f"サーモ画像: {os.path.basename(selected_path)}")
            
            # ODMImageSelectorにwebodm_pathを渡す
            ODMImageSelector(dialog, annotation, "thermal", self.webodm_path, callback, app_ref=self)



        def select_visible_image():
            file_path = filedialog.askopenfilename(
                title="可視画像を選択",
                filetypes=[("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif")]
            )
            if file_path:
                annotation["visible_image"] = file_path
                self.last_thermal_visible_dir = os.path.dirname(file_path)
                visible_label.config(text=f"可視画像: {os.path.basename(file_path)}")

        def select_visible_image_odm():
            # WebODMフォルダが選択されているかチェック
            if not self.webodm_path:
                messagebox.showwarning("警告", "メイン画面で「WebODMフォルダ選択」ボタンからアセットフォルダを先に選択してください。")
                return

            def callback(selected_path):
                annotation["visible_image"] = selected_path
                self.last_thermal_visible_dir = os.path.dirname(selected_path)
                visible_label.config(text=f"可視画像: {os.path.basename(selected_path)}")
            
            # ODMImageSelectorにwebodm_pathを渡す
            ODMImageSelector(dialog, annotation, "visible", self.webodm_path, callback, app_ref=self)


        # サーモ画像選択
        thermal_frame = ttk.Frame(dialog)
        thermal_frame.grid(row=len(fields)+3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Button(thermal_frame, text="サーモ画像選択", command=select_thermal_image).pack(side=tk.LEFT, padx=(0, 10))
        odm_button_group = ttk.Frame(thermal_frame)
        odm_button_group.pack(side=tk.LEFT)
        ttk.Button(odm_button_group, text="ODM選択", command=select_thermal_image_odm).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(odm_button_group, text="サーモ画像同時選択", command=select_thermal_visible_pair).pack(side=tk.LEFT)

        thermal_label = ttk.Label(dialog, text=f"サーモ画像: {os.path.basename(annotation.get('thermal_image', ''))}")
        thermal_label.grid(row=len(fields)+4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # 可視画像選択
        visible_frame = ttk.Frame(dialog)
        visible_frame.grid(row=len(fields)+5, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        ttk.Button(visible_frame, text="可視画像選択", command=select_visible_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(visible_frame, text="ODM選択", command=select_visible_image_odm).pack(side=tk.LEFT)
        
        visible_label = ttk.Label(dialog, text=f"可視画像: {os.path.basename(annotation.get('visible_image', ''))}")
        visible_label.grid(row=len(fields)+6, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # ボタン
        def save_changes():
            for key, entry in entries.items():
                annotation[key] = entry.get()
            annotation["defect_type"] = defect_combo.get() or annotation.get("defect_type", "")
            annotation["shape"] = self.annotation_shapes.get(shape_combo.get(), annotation.get("shape", "cross"))
            annotation["management_level"] = (mgmt_var.get() or 'S')

            new_id_str = id_var.get().strip()
            if not new_id_str:
                messagebox.showwarning("警告", "ID番号を入力してください。", parent=dialog)
                return
            if not new_id_str.isdigit():
                messagebox.showwarning("警告", "ID番号は1以上の整数で入力してください。", parent=dialog)
                return

            new_id = int(new_id_str)
            if new_id <= 0:
                messagebox.showwarning("警告", "ID番号は1以上の整数で入力してください。", parent=dialog)
                return

            if new_id != annotation.get("id"):
                if not self._confirm_id_change(annotation.get("id"), new_id, parent=dialog):
                    return
                try:
                    self.apply_annotation_id_change(annotation, new_id, parent=dialog)
                except ValueError as e:
                    messagebox.showwarning("警告", str(e), parent=dialog)
                    return
            else:
                self.update_table()
                self.draw_annotations()

            dialog.destroy()


        def cancel_changes():
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=len(fields)+7, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=cancel_changes).pack(side=tk.LEFT, padx=5)

    def edit_annotation_dialog(self, annotation):
        """アノテーション編集ダイアログ"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"ID{annotation['id']} 編集")
        dialog.geometry("980x780")
        dialog.transient(self.root)
        dialog.grab_set()

        annotation.setdefault("thermal_overlays", [])
        annotation.setdefault("visible_overlays", [])

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        form_frame = ttk.Frame(main_frame)
        form_frame.grid(row=0, column=0, sticky="ns")
        form_frame.columnconfigure(1, weight=1)

        fields = [
            ("エリア番号", "area_no"),
            ("PCS番号", "pcs_no"),
            ("接続箱番号", "junction_box_no"),
            ("回路番号", "circuit_no"),
            ("アレイ№", "array_no"),
            ("モジュール位置", "module_position"),
            ("シリアル№", "serial_no"),
            ("備考", "remarks"),
            ("報告年月日", "report_date")
        ]

        entries = {}
        current_row = 0

        ttk.Label(form_frame, text="ID番号:").grid(row=current_row, column=0, sticky="w", padx=10, pady=5)
        id_var = tk.StringVar(value=str(annotation.get("id", "")))

        def _validate_id_input(new_value):
            return new_value.isdigit() or new_value == ""

        id_entry = ttk.Entry(
            form_frame,
            width=30,
            textvariable=id_var,
            validate="key",
            validatecommand=(form_frame.register(_validate_id_input), "%P")
        )
        id_entry.grid(row=current_row, column=1, padx=10, pady=5, sticky="ew")
        current_row += 1

        for label, key in fields:
            ttk.Label(form_frame, text=f"{label}:").grid(row=current_row, column=0, sticky="w", padx=10, pady=5)
            if key == "report_date":
                entry = ttk.Entry(form_frame, width=30)
                current_date = annotation.get(key, datetime.now().strftime('%Y-%m-%d'))
                entry.insert(0, current_date)
            else:
                entry = ttk.Entry(form_frame, width=30)
                entry.insert(0, annotation.get(key, ""))
            entry.grid(row=current_row, column=1, padx=10, pady=5, sticky="ew")
            entries[key] = entry
            current_row += 1

        ttk.Label(form_frame, text="管理レベル:").grid(row=current_row, column=0, sticky="w", padx=10, pady=5)
        mgmt_var = tk.StringVar(value=(annotation.get("management_level") or 'S'))
        mgmt_combo = ttk.Combobox(form_frame, values=['S', 'A', 'B', 'N'], state="readonly", width=27, textvariable=mgmt_var)
        mgmt_combo.grid(row=current_row, column=1, padx=10, pady=5, sticky="ew")
        current_row += 1

        ttk.Label(form_frame, text="不良分類:").grid(row=current_row, column=0, sticky="w", padx=10, pady=5)
        defect_combo = ttk.Combobox(form_frame, values=list(self.defect_types.keys()), state="readonly", width=27)
        defect_combo.set(annotation.get("defect_type", ""))
        defect_combo.grid(row=current_row, column=1, padx=10, pady=5, sticky="ew")
        current_row += 1

        ttk.Label(form_frame, text="形状:").grid(row=current_row, column=0, sticky="w", padx=10, pady=5)
        shape_combo = ttk.Combobox(form_frame, values=list(self.annotation_shapes.keys()), state="readonly", width=27)
        current_shape = annotation.get("shape", "cross")
        shape_name = next((k for k, v in self.annotation_shapes.items() if v == current_shape), "十字")
        shape_combo.set(shape_name)
        shape_combo.grid(row=current_row, column=1, padx=10, pady=5, sticky="ew")
        current_row += 1

        preview_container = ttk.Frame(main_frame)
        preview_container.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
        preview_container.columnconfigure(0, weight=1)
        preview_container.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(preview_container)
        notebook.grid(row=0, column=0, sticky="nsew")

        outer = self

        class ImageAnnotationPreview:
            def __init__(self, parent, image_type, annotation_dict, defect_combo_ref, shape_combo_ref, initial_path, overlay_points):
                self.outer = outer
                self.annotation = annotation_dict
                self.image_type = image_type
                self.defect_combo = defect_combo_ref
                self.shape_combo = shape_combo_ref
                self.annotation_key = f"{image_type}_overlays"
                self.annotated_path_key = f"{image_type}_annotated_image"
                self.canvas_width = 520
                self.canvas_height = 520
                self.frame = ttk.Frame(parent)

                self.status_var = tk.StringVar(value="画像を選択してください。")
                ttk.Label(self.frame, textvariable=self.status_var, justify="left", wraplength=self.canvas_width).pack(fill=tk.X, pady=(0, 6))

                self.canvas = tk.Canvas(self.frame, width=self.canvas_width, height=self.canvas_height, bg="#1f1f1f", highlightthickness=0)
                self.canvas.pack(fill=tk.BOTH, expand=True)

                ttk.Label(self.frame, text="左クリック: アノテーション追加 / 右クリック: 削除", foreground="#666666").pack(fill=tk.X, pady=(6, 8))

                control_frame = ttk.Frame(self.frame)
                control_frame.pack(fill=tk.X)
                ttk.Button(control_frame, text="決定", command=self.confirm).pack(side=tk.RIGHT, padx=(8, 0))
                ttk.Button(control_frame, text="キャンセル", command=self.cancel).pack(side=tk.RIGHT)

                self.canvas.bind("<Button-1>", self.on_left_click)
                self.canvas.bind("<Button-3>", self.on_right_click)

                self.image_path = None
                self.tk_image = None
                self.display_scale = 1.0
                self.offset_x = 0
                self.offset_y = 0
                self.display_width = 0
                self.display_height = 0
                self.original_points = []
                self.working_points = []
                self.icon_refs = []

                self.update_source(initial_path, overlay_points or [])

            def update_source(self, path, overlay_points=None):
                if overlay_points is None:
                    overlay_points = []
                self.image_path = path if path else None
                self.original_points = copy.deepcopy(overlay_points)
                self.working_points = copy.deepcopy(overlay_points)
                self._render_image()

            def _render_image(self):
                self.canvas.delete("all")
                self.tk_image = None
                self.display_scale = 1.0
                self.offset_x = 0
                self.offset_y = 0
                self.display_width = 0
                self.display_height = 0

                if not self.image_path or not os.path.exists(self.image_path):
                    self.status_var.set("画像未選択です。")
                    self.canvas.create_text(self.canvas_width / 2, self.canvas_height / 2, text="画像が選択されていません", fill="#aaaaaa")
                    return

                try:
                    with Image.open(self.image_path) as img:
                        img = img.convert("RGBA")
                        width, height = img.size
                        scale = min(self.canvas_width / width, self.canvas_height / height, 1.0)
                        display_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                        display_image = img.resize(display_size, Image.Resampling.LANCZOS) if scale != 1.0 else img.copy()
                except Exception as e:
                    self.status_var.set(f"画像を読み込めません: {e}")
                    self.canvas.create_text(self.canvas_width / 2, self.canvas_height / 2, text="読み込み失敗", fill="#ff6666")
                    return

                self.display_width, self.display_height = display_size
                self.display_scale = width and (display_size[0] / width) or 1.0
                self.offset_x = (self.canvas_width - self.display_width) / 2
                self.offset_y = (self.canvas_height - self.display_height) / 2

                self.canvas.create_rectangle(0, 0, self.canvas_width, self.canvas_height, fill="#1f1f1f", outline="")
                self.tk_image = ImageTk.PhotoImage(display_image)
                self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.tk_image, tags="base_image")
                self.status_var.set(f"{os.path.basename(self.image_path)} / {width}x{height}px")
                self.redraw_overlays()

            def _current_color(self):
                defect_name = self.defect_combo.get() or self.annotation.get("defect_type")
                return self.outer.defect_types.get(defect_name, "#FF0000")

            def _current_shape_code(self):
                shape_label = self.shape_combo.get()
                if shape_label in self.outer.annotation_shapes:
                    return self.outer.annotation_shapes[shape_label]
                return self.annotation.get("shape", "cross")

            def redraw_overlays(self):
                self.canvas.delete("overlay")
                if not self.tk_image:
                    return

                self.icon_refs = []
                color = self._current_color()
                shape_code = self._current_shape_code()
                defect_name = self.defect_combo.get() or self.annotation.get("defect_type")
                icon_size = max(24, int(self.outer.annotation_default_icon_size * 0.9))
                tk_icon = self.outer.get_tk_icon(defect_name, icon_size)

                for point in self.working_points:
                    disp_x = point["x"] * self.display_scale + self.offset_x
                    disp_y = point["y"] * self.display_scale + self.offset_y

                    if tk_icon:
                        self.canvas.create_image(
                            disp_x,
                            disp_y,
                            image=tk_icon,
                            anchor=tk.CENTER,
                            tags="overlay"
                        )
                        self.icon_refs.append(tk_icon)
                        label_y = disp_y - (tk_icon.height() / 2) - 6
                        self.canvas.create_text(
                            disp_x,
                            label_y,
                            text=f"ID{self.annotation['id']}",
                            fill="white",
                            font=("Arial", 10, "bold"),
                            tags="overlay"
                        )
                    else:
                        self._draw_shape_on_canvas(disp_x, disp_y, color, shape_code)

            def _draw_shape_on_canvas(self, x, y, color, shape_code):
                size = 14
                if shape_code == "cross":
                    self.canvas.create_line(x, y - size, x, y + size, fill=color, width=2, tags="overlay")
                    self.canvas.create_line(x - size, y, x + size, y, fill=color, width=2, tags="overlay")
                elif shape_code == "arrow":
                    self.canvas.create_line(x, y - size, x, y + size, fill=color, width=2, tags="overlay")
                    self.canvas.create_polygon(x, y - size, x - 6, y - size + 12, x + 6, y - size + 12, fill=color, outline=color, tags="overlay")
                elif shape_code == "circle":
                    radius = size
                    self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, outline=color, width=2, tags="overlay")
                elif shape_code == "rectangle":
                    self.canvas.create_rectangle(x - size, y - size, x + size, y + size, outline=color, width=2, tags="overlay")

                self.canvas.create_text(x, y - size - 6, text=f"ID{self.annotation['id']}", fill="white", font=("Arial", 10, "bold"), tags="overlay")

            def on_left_click(self, event):
                if not self.tk_image:
                    return
                canvas_x = self.canvas.canvasx(event.x)
                canvas_y = self.canvas.canvasy(event.y)
                norm_x = canvas_x - self.offset_x
                norm_y = canvas_y - self.offset_y
                if norm_x < 0 or norm_y < 0 or norm_x > self.display_width or norm_y > self.display_height:
                    return
                original_x = norm_x / self.display_scale
                original_y = norm_y / self.display_scale
                self.working_points.append({"x": original_x, "y": original_y})
                self.redraw_overlays()
                self.status_var.set(f"アノテーションを追加しました ({len(self.working_points)}件)")

            def on_right_click(self, event):
                if not self.tk_image or not self.working_points:
                    return
                canvas_x = self.canvas.canvasx(event.x)
                canvas_y = self.canvas.canvasy(event.y)
                norm_x = canvas_x - self.offset_x
                norm_y = canvas_y - self.offset_y
                if norm_x < 0 or norm_y < 0 or norm_x > self.display_width or norm_y > self.display_height:
                    return

                min_index = None
                min_distance = float('inf')
                for idx, point in enumerate(self.working_points):
                    disp_x = point["x"] * self.display_scale
                    disp_y = point["y"] * self.display_scale
                    distance = math.hypot(norm_x - disp_x, norm_y - disp_y)
                    if distance < 18 and distance < min_distance:
                        min_distance = distance
                        min_index = idx

                if min_index is not None:
                    self.working_points.pop(min_index)
                    self.redraw_overlays()
                    self.status_var.set("アノテーションを削除しました。")

            def confirm(self):
                if not self.image_path or not os.path.exists(self.image_path):
                    messagebox.showwarning("警告", "画像が選択されていません。")
                    return

                try:
                    with Image.open(self.image_path) as src:
                        working_image = src.convert("RGBA")
                except Exception as e:
                    messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")
                    return

                draw = ImageDraw.Draw(working_image)
                color = self._current_color()
                shape_code = self._current_shape_code()
                defect_name = self.defect_combo.get() or self.annotation.get("defect_type")
                scale_key = self.image_type if self.image_type in ("thermal", "visible") else "overall"
                annotation_scale = self.outer._get_annotation_scale(scale_key)

                for point in self.working_points:
                    x = point["x"]
                    y = point["y"]
                    icon_height = self.outer.draw_annotation_icon_on_image(
                        working_image,
                        draw,
                        x,
                        y,
                        defect_name,
                        color,
                        shape_code,
                        annotation_scale
                    )

                    self.outer._draw_id_label_on_image(
                        draw,
                        x,
                        y,
                        self.annotation['id'],
                        color,
                        working_image.size,
                        annotation_scale,
                        icon_height,
                    )

                if getattr(self.outer, "project_path", None):
                    base_dir = os.path.join(self.outer.project_path, "アノテーション入り画像フォルダ")
                else:
                    base_dir = os.path.join(os.path.dirname(self.image_path), "annotated")
                
                # 画像タイプに応じてサブフォルダを作成
                if self.image_type == "thermal":
                    type_dir = os.path.join(base_dir, "サーモ画像フォルダ")
                elif self.image_type == "visible":
                    type_dir = os.path.join(base_dir, "可視画像フォルダ")
                else:
                    type_dir = base_dir
                
                os.makedirs(type_dir, exist_ok=True)

                name, ext = os.path.splitext(os.path.basename(self.image_path))
                if not ext:
                    ext = ".png"
                output_path = os.path.join(type_dir, f"ID{self.annotation['id']}_{name}_{self.image_type}_annotated{ext}")

                try:
                    file_ext = os.path.splitext(output_path)[1].lower()
                    save_image = working_image
                    if file_ext in (".jpg", ".jpeg") and save_image.mode not in ("RGB", "L"):
                        save_image = save_image.convert("RGB")
                    save_image.save(output_path)
                except Exception as e:
                    messagebox.showerror("エラー", f"注釈付き画像の保存に失敗しました: {e}")
                    return

                self.annotation[self.annotated_path_key] = output_path
                self.annotation[self.annotation_key] = copy.deepcopy(self.working_points)
                self.original_points = copy.deepcopy(self.working_points)
                self.status_var.set(f"保存完了: {os.path.basename(output_path)}")
                messagebox.showinfo("保存完了", f"アノテーション入り画像を保存しました。\n{output_path}")

            def cancel(self):
                self.working_points = copy.deepcopy(self.original_points)
                self.redraw_overlays()
                self.status_var.set("編集内容を破棄しました。")
            
            def has_unsaved_changes(self):
                """未保存の変更があるかチェック"""
                if not self.image_path:
                    return False
                # working_pointsとoriginal_pointsを比較
                if len(self.working_points) != len(self.original_points):
                    return True
                # 各ポイントを比較（順序も含めて）
                for wp, op in zip(self.working_points, self.original_points):
                    if wp.get("x") != op.get("x") or wp.get("y") != op.get("y"):
                        return True
                return False

        thermal_preview = ImageAnnotationPreview(
            notebook,
            "thermal",
            annotation,
            defect_combo,
            shape_combo,
            annotation.get("thermal_image"),
            annotation.get("thermal_overlays", [])
        )
        notebook.add(thermal_preview.frame, text="サーモ画像")

        visible_preview = ImageAnnotationPreview(
            notebook,
            "visible",
            annotation,
            defect_combo,
            shape_combo,
            annotation.get("visible_image"),
            annotation.get("visible_overlays", [])
        )
        notebook.add(visible_preview.frame, text="可視画像")

        def refresh_preview_style(event=None):
            thermal_preview.redraw_overlays()
            visible_preview.redraw_overlays()

        defect_combo.bind("<<ComboboxSelected>>", refresh_preview_style)
        shape_combo.bind("<<ComboboxSelected>>", refresh_preview_style)

        def format_image_label(prefix, path):
            return f"{prefix}: {os.path.basename(path)}" if path else f"{prefix}: 未選択"

        thermal_label_var = tk.StringVar(value=format_image_label("サーモ画像", annotation.get("thermal_image")))
        visible_label_var = tk.StringVar(value=format_image_label("可視画像", annotation.get("visible_image")))

        def select_thermal_visible_pair():
            candidates = [
                annotation.get("thermal_image"),
                annotation.get("visible_image"),
                self.last_thermal_visible_dir
            ]
            initial_dir = None
            for candidate in candidates:
                if not candidate:
                    continue
                candidate_dir = candidate if os.path.isdir(candidate) else os.path.dirname(candidate)
                if candidate_dir and os.path.isdir(candidate_dir):
                    initial_dir = candidate_dir
                    break
            selector = ThermalVisibleFileDialog(dialog, initial_dir=initial_dir)
            result = selector.show()
            if result:
                thermal_path, visible_path = result

                prev_thermal = annotation.get("thermal_image")
                annotation["thermal_image"] = thermal_path
                if prev_thermal != thermal_path:
                    annotation["thermal_overlays"] = []
                thermal_preview.update_source(thermal_path, annotation.get("thermal_overlays", []))
                thermal_label_var.set(format_image_label("サーモ画像", thermal_path))

                prev_visible = annotation.get("visible_image")
                annotation["visible_image"] = visible_path
                if prev_visible != visible_path:
                    annotation["visible_overlays"] = []
                visible_preview.update_source(visible_path, annotation.get("visible_overlays", []))
                visible_label_var.set(format_image_label("可視画像", visible_path))

                self.last_thermal_visible_dir = os.path.dirname(thermal_path)

        def select_thermal_image():
            file_path = filedialog.askopenfilename(
                title="サーモ画像を選択",
                filetypes=[("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif")]
            )
            if file_path:
                prev_thermal = annotation.get("thermal_image")
                annotation["thermal_image"] = file_path
                if prev_thermal != file_path:
                    annotation["thermal_overlays"] = []
                thermal_preview.update_source(file_path, annotation.get("thermal_overlays", []))
                thermal_label_var.set(format_image_label("サーモ画像", file_path))
                self.last_thermal_visible_dir = os.path.dirname(file_path)

        def select_thermal_image_odm():
            if not self.webodm_path:
                messagebox.showwarning("警告", "メイン画面で「WebODMフォルダ選択」ボタンからアセットフォルダを先に選択してください。")
                return

            def callback(selected_path):
                prev_thermal = annotation.get("thermal_image")
                annotation["thermal_image"] = selected_path
                if prev_thermal != selected_path:
                    annotation["thermal_overlays"] = []
                thermal_preview.update_source(selected_path, annotation.get("thermal_overlays", []))
                thermal_label_var.set(format_image_label("サーモ画像", selected_path))
                self.last_thermal_visible_dir = os.path.dirname(selected_path)

            ODMImageSelector(dialog, annotation, "thermal", self.webodm_path, callback, app_ref=self)

        def select_visible_image():
            file_path = filedialog.askopenfilename(
                title="可視画像を選択",
                filetypes=[("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif")]
            )
            if file_path:
                prev_visible = annotation.get("visible_image")
                annotation["visible_image"] = file_path
                if prev_visible != file_path:
                    annotation["visible_overlays"] = []
                visible_preview.update_source(file_path, annotation.get("visible_overlays", []))
                visible_label_var.set(format_image_label("可視画像", file_path))
                self.last_thermal_visible_dir = os.path.dirname(file_path)

        def select_visible_image_odm():
            if not self.webodm_path:
                messagebox.showwarning("警告", "メイン画面で「WebODMフォルダ選択」ボタンからアセットフォルダを先に選択してください。")
                return

            def callback(selected_path):
                prev_visible = annotation.get("visible_image")
                annotation["visible_image"] = selected_path
                if prev_visible != selected_path:
                    annotation["visible_overlays"] = []
                visible_preview.update_source(selected_path, annotation.get("visible_overlays", []))
                visible_label_var.set(format_image_label("可視画像", selected_path))
                self.last_thermal_visible_dir = os.path.dirname(selected_path)

            ODMImageSelector(dialog, annotation, "visible", self.webodm_path, callback, app_ref=self)

        thermal_frame = ttk.Frame(form_frame)
        thermal_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        ttk.Button(thermal_frame, text="サーモ画像選択", command=select_thermal_image).pack(side=tk.LEFT, padx=(0, 10))
        odm_button_group = ttk.Frame(thermal_frame)
        odm_button_group.pack(side=tk.LEFT)
        ttk.Button(odm_button_group, text="ODM選択", command=select_thermal_image_odm).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(odm_button_group, text="サーモ画像同時選択", command=select_thermal_visible_pair).pack(side=tk.LEFT)
        current_row += 1

        ttk.Label(form_frame, textvariable=thermal_label_var).grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        current_row += 1

        visible_frame = ttk.Frame(form_frame)
        visible_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        ttk.Button(visible_frame, text="可視画像選択", command=select_visible_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(visible_frame, text="ODM選択", command=select_visible_image_odm).pack(side=tk.LEFT)
        current_row += 1

        ttk.Label(form_frame, textvariable=visible_label_var).grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        current_row += 1

        def save_changes():
            """フォーム項目を保存し、未保存の画像アノテーションがあれば確認する"""
            # サーモ画像と可視画像の未保存変更をチェック
            thermal_has_changes = thermal_preview.has_unsaved_changes()
            visible_has_changes = visible_preview.has_unsaved_changes()
            
            # 未保存の画像アノテーションがある場合、確認ダイアログを表示
            if thermal_has_changes or visible_has_changes:
                unsaved_types = []
                if thermal_has_changes:
                    unsaved_types.append("サーモ画像")
                if visible_has_changes:
                    unsaved_types.append("可視画像")
                
                message = f"{' と '.join(unsaved_types)}のタブに未保存のアノテーションがあります。\n\n保存しますか？"
                
                result = messagebox.askyesnocancel(
                    "未保存の変更",
                    message,
                    parent=dialog
                )
                
                if result is None:  # キャンセル - ダイアログを閉じない
                    return
                elif result:  # はい - 未保存の画像アノテーションを保存
                    if thermal_has_changes:
                        thermal_preview.confirm()
                    if visible_has_changes:
                        visible_preview.confirm()
                # いいえの場合は保存せずに続行
            
            # フォーム項目を保存
            for key, entry in entries.items():
                annotation[key] = entry.get()
            annotation["defect_type"] = defect_combo.get() or annotation.get("defect_type", "")
            annotation["shape"] = self.annotation_shapes.get(shape_combo.get(), annotation.get("shape", "cross"))
            annotation["management_level"] = (mgmt_var.get() or 'S')

            self.update_table()
            self.draw_annotations()
            dialog.destroy()

        def check_unsaved_and_close():
            """未保存の変更をチェックしてダイアログを閉じる"""
            # サーモ画像と可視画像の両方で未保存変更をチェック
            thermal_has_changes = thermal_preview.has_unsaved_changes()
            visible_has_changes = visible_preview.has_unsaved_changes()
            
            if thermal_has_changes or visible_has_changes:
                # 未保存の変更がある場合、確認ダイアログを表示
                unsaved_types = []
                if thermal_has_changes:
                    unsaved_types.append("サーモ画像")
                if visible_has_changes:
                    unsaved_types.append("可視画像")
                
                message = f"{' と '.join(unsaved_types)}のタブに未保存のアノテーションがあります。\n\n保存しますか？"
                
                result = messagebox.askyesnocancel(
                    "未保存の変更",
                    message,
                    parent=dialog
                )
                
                if result is None:  # キャンセル
                    return
                elif result:  # はい（保存する）
                    # 未保存の変更があるタブの保存を実行
                    if thermal_has_changes:
                        thermal_preview.confirm()
                    if visible_has_changes:
                        visible_preview.confirm()
                # いいえの場合は何もせずにダイアログを閉じる
            
            dialog.destroy()
        
        def cancel_changes():
            check_unsaved_and_close()

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=current_row, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=cancel_changes).pack(side=tk.LEFT, padx=5)

        dialog.protocol("WM_DELETE_WINDOW", check_unsaved_and_close)

    def update_table(self):
        """テーブルを更新"""
        # 既存のアイテムをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)

        # アノテーションをIDでソート
        sorted_annotations = sorted(self.annotations, key=lambda x: x['id'])

        # テーブルに追加
        for annotation in sorted_annotations:
            shape_name = next((k for k, v in self.annotation_shapes.items() 
                            if v == annotation.get("shape", "cross")), "十字")
            
            # サーモ画像のファイル名を命名規則に従って生成
            thermal_filename = ""
            if annotation.get('thermal_image'):
                src_path = annotation['thermal_image']
                if os.path.exists(src_path):
                    thermal_filename = f"ID{annotation['id']}_{annotation['defect_type']}_サーモ異常{os.path.splitext(src_path)[1]}"
            
            # 可視画像のファイル名を命名規則に従って生成
            visible_filename = ""
            if annotation.get('visible_image'):
                src_path = annotation['visible_image']
                if os.path.exists(src_path):
                    visible_filename = f"ID{annotation['id']}_{annotation['defect_type']}_可視異常{os.path.splitext(src_path)[1]}"
            
            values = (
                annotation['id'],
                annotation.get('area_no', ''),
                annotation.get('pcs_no', ''),
                annotation.get('junction_box_no', ''),
                annotation.get('circuit_no', ''),
                annotation.get('array_no', ''),           # 追加
                annotation.get('module_position', ''),    # 追加
                annotation.get('serial_no', ''),          # 追加
                annotation.get('defect_type', ''),
                shape_name,
                thermal_filename,
                visible_filename,
                annotation.get('remarks', ''),
                annotation.get('report_date', '')         # 追加
            )
            self.tree.insert("", tk.END, values=values)

    def on_mouse_wheel(self, event):
        """マウスホイールでズーム"""
        if self.current_image:
            # ズーム倍率を調整
            if event.delta > 0:
                self.zoom_factor *= 1.1
            else:
                self.zoom_factor /= 1.1

            # ズーム倍率の制限
            self.zoom_factor = max(0.1, min(5.0, self.zoom_factor))

            self.display_image()

    def start_pan(self, event):
        """パン開始"""
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def do_pan(self, event):
        """パン実行"""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y

        self.canvas.scan_dragto(dx, dy, gain=1)

    def reset_image(self):
        """画像をリセット"""
        if messagebox.askyesno("確認", "画像をリセットしますか？アノテーションもすべて削除されます。"):
            self.current_image = None
            self.image_path = None
            self.annotations = []
            self.next_id = 1
            self.canvas.delete("all")
            self.update_table()

    def customize_colors(self):
        """色をカスタマイズ"""
        dialog = tk.Toplevel(self.root)
        dialog.title("色設定")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()

        color_vars = {}

        for i, (defect_type, color) in enumerate(self.defect_types.items()):
            ttk.Label(dialog, text=f"{defect_type}:").grid(row=i, column=0, sticky="w", padx=10, pady=5)

            color_var = tk.StringVar(value=color)
            color_vars[defect_type] = color_var

            def choose_color(dt=defect_type, cv=color_var):
                color = colorchooser.askcolor(initialcolor=cv.get())[1]
                if color:
                    cv.set(color)

            ttk.Button(dialog, text="色選択", command=choose_color).grid(row=i, column=1, padx=10, pady=5)

        def apply_colors():
            for defect_type, color_var in color_vars.items():
                self.defect_types[defect_type] = color_var.get()
            self.draw_annotations()
            dialog.destroy()

        ttk.Button(dialog, text="適用", command=apply_colors).grid(row=len(self.defect_types), 
                                                                  column=0, columnspan=2, pady=20)

    def save_project(self):
        """プロジェクトを保存"""
        if not self.annotations:
            messagebox.showwarning("警告", "保存するアノテーションがありません。")
            return

        try:
            # アノテーション設定を保存
            annotation_data = {
                "project_name": self.project_name,
                "image_path": self.image_path,
                "annotations": self.annotations,
                "defect_types": self.defect_types,
                "annotation_shapes": self.annotation_shapes,
                "created_date": datetime.now().isoformat()
            }

            annotation_file = os.path.join(self.project_path, "アノテーション設定フォルダ", "annotations.json")
            with open(annotation_file, 'w', encoding='utf-8') as f:
                json.dump(annotation_data, f, ensure_ascii=False, indent=2)

            # 不具合一覧表をCSV形式で保存
            self.export_to_csv()

            # 不具合一覧表をExcel形式で保存
            self.export_to_excel()

            # 関連画像をコピー
            self.copy_related_images()

            # アノテーション入り画像を保存
            self.save_annotated_image()

            # 各不具合IDごとの個別全体図を保存
            self.save_individual_annotated_images()

            # 拡張版（v2）CSV/XLSXの出力（メイン保存と同一タイミング）
            try:
                self.export_v2_csv()
                self.export_v2_xlsx()
            except Exception as e:
                print(f"[WARN] v2出力でエラー: {e}")

            messagebox.showinfo("成功", f"プロジェクト '{self.project_name}' を保存しました。")

        except Exception as e:
            messagebox.showerror("エラー", f"保存に失敗しました: {str(e)}")

    def save_annotated_image(self):
        """アノテーション入り画像を保存"""
        if not self.current_image:
            return

        # 元画像をコピー
        annotated_image = self.current_image.copy()
        draw = ImageDraw.Draw(annotated_image)
        overall_scale = self._get_annotation_scale("overall")

        # アノテーションを描画
        for annotation in self.annotations:
            x = annotation["x"]
            y = annotation["y"]
            defect_type = annotation.get("defect_type")
            color = self.defect_types.get(defect_type, "#FF0000")
            shape = annotation.get("shape", "cross")

            icon_height = self.draw_annotation_icon_on_image(
                annotated_image,
                draw,
                x,
                y,
                defect_type,
                color,
                shape,
                overall_scale
            )

            # ID番号を描画
            self._draw_id_label_on_image(
                draw,
                x,
                y,
                annotation['id'],
                color,
                annotated_image.size,
                overall_scale,
                icon_height,
            )

        # 保存
        output_path = os.path.join(self.project_path, "アノテーション入り画像フォルダ", 
                                  f"{self.project_name}_annotated.png")
        annotated_image.save(output_path)

    def _create_extended_image(self, original_image):
        """
        画像の上下に白色背景を追加して拡張する
        
        Args:
            original_image: 元画像（PIL Image）
        
        Returns:
            tuple: (拡張画像, 上部オフセット)
        """
        width, height = original_image.size
        
        # 拡張サイズを計算
        total_extension = int(height * self.image_extension_ratio)
        top_extension = total_extension // 2
        bottom_extension = total_extension - top_extension
        
        # 拡張後の画像サイズ
        new_height = height + top_extension + bottom_extension
        
        # 元画像のモードに合わせて白色背景の新画像を作成
        if original_image.mode == 'RGBA':
            extended_image = Image.new('RGBA', (width, new_height), (255, 255, 255, 255))
        else:
            extended_image = Image.new(original_image.mode, (width, new_height), (255, 255, 255))
        
        # 元画像を上部オフセット位置にペースト
        extended_image.paste(original_image, (0, top_extension))
        
        return extended_image, top_extension

    def save_individual_annotated_images(self):
        """各不具合IDごとに、そのIDのアノテーションのみを配置した全体図を個別に保存"""
        if not self.current_image:
            return
        
        if not self.annotations:
            return
        
        # 全体図位置フォルダのパスを取得
        output_folder = os.path.join(self.project_path, "全体図位置フォルダ")
        os.makedirs(output_folder, exist_ok=True)
        
        overall_scale = self._get_annotation_scale("overall")
        
        # 各不具合IDごとにループ処理
        for annotation in self.annotations:
            try:
                # 画像を拡張（上下に白色背景を追加）
                extended_image, top_offset = self._create_extended_image(self.current_image)
                annotated_image = extended_image.copy()
                draw = ImageDraw.Draw(annotated_image)
                
                # 現在のIDのアノテーションのみを描画（座標を調整）
                x = annotation["x"]
                defect_y = annotation["y"] + top_offset  # 不具合の位置（上部オフセット分だけ調整）
                defect_type = annotation.get("defect_type", "不具合")
                color = self.defect_types.get(defect_type, "#FF0000")
                shape = annotation.get("shape", "cross")
                
                # アノテーションの高さを事前計算（アノテーション下部を不具合位置に合わせるため）
                # アイコンがある場合はアイコンの高さを推定、ない場合は形状の高さを推定
                base_icon = self.load_annotation_icon(defect_type)
                if base_icon is not None:
                    # アイコンの高さを推定（draw_annotation_icon_on_imageと同じロジック）
                    icon_w, icon_h = base_icon.size
                    base_length = max(annotated_image.width, annotated_image.height)
                    min_dim = max(1, min(annotated_image.width, annotated_image.height))
                    base_target = min(max(24, int(base_length * 0.05)), max(16, min_dim), 128)
                    target_edge = max(4, int(round(base_target * overall_scale)))
                    target_edge = min(target_edge, min_dim)
                    scale = target_edge / max(icon_w, icon_h) if max(icon_w, icon_h) else 1.0
                    estimated_height = max(1, int(round(icon_h * scale)))
                else:
                    # アイコンがない場合は形状の高さを推定
                    if shape in ["cross", "arrow", "rectangle"]:
                        estimated_height = max(6, int(round(20 * overall_scale))) * 2
                    elif shape == "circle":
                        estimated_height = max(6, int(round(25 * overall_scale))) * 2
                    else:
                        estimated_height = max(6, int(round(20 * overall_scale))) * 2
                
                # アノテーション描画位置を計算（下部が不具合位置に来るように上方向に調整）
                annotation_y = defect_y - estimated_height / 2
                
                # アノテーションアイコン/シェイプを描画
                icon_height = self.draw_annotation_icon_on_image(
                    annotated_image,
                    draw,
                    x,
                    annotation_y,
                    defect_type,
                    color,
                    shape,
                    overall_scale
                )
                
                # ID番号を描画
                self._draw_id_label_on_image(
                    draw,
                    x,
                    annotation_y,
                    annotation['id'],
                    color,
                    annotated_image.size,
                    overall_scale,
                    icon_height,
                )
                
                # ファイル名を生成: ID{id:03d}_全体図_{不具合名}.jpg
                annotation_id = annotation.get('id', 0)
                # ファイル名として不適切な文字を置換
                safe_defect_type = defect_type.replace("/", "_").replace("\\", "_").replace(":", "_")
                filename = f"ID{annotation_id:03d}_全体図_{safe_defect_type}.jpg"
                output_path = os.path.join(output_folder, filename)
                
                # JPEG保存前にRGBモードに変換（RGBAの場合）
                if annotated_image.mode == 'RGBA':
                    # 白背景に合成してRGBに変換
                    rgb_image = Image.new('RGB', annotated_image.size, (255, 255, 255))
                    rgb_image.paste(annotated_image, mask=annotated_image.split()[3])
                    annotated_image = rgb_image
                elif annotated_image.mode != 'RGB':
                    # その他のモードもRGBに変換
                    annotated_image = annotated_image.convert('RGB')
                
                # JPEG形式で保存（品質95%で高品質を保持）
                annotated_image.save(output_path, 'JPEG', quality=95)
                
            except Exception as e:
                # エラーが発生しても他のIDの処理は続行
                print(f"[WARN] ID{annotation.get('id', '?')}の全体図生成に失敗しました: {e}")
                continue

    def draw_cross_on_image(self, draw, x, y, color, scale_multiplier=1.0):
        """画像上に十字を描画"""
        size = max(6, int(round(20 * scale_multiplier)))
        line_width = max(1, int(round(3 * scale_multiplier)))
        draw.line([(x, y - size), (x, y + size)], fill=color, width=line_width)
        draw.line([(x - size, y), (x + size, y)], fill=color, width=line_width)
        return size * 2

    def draw_arrow_on_image(self, draw, x, y, color, scale_multiplier=1.0):
        """画像上に矢印を描画"""
        size = max(6, int(round(20 * scale_multiplier)))
        line_width = max(1, int(round(3 * scale_multiplier)))
        head_offset = max(6, int(round(15 * scale_multiplier)))
        head_width = max(4, int(round(8 * scale_multiplier)))
        draw.line([(x, y - size), (x, y + size)], fill=color, width=line_width)
        draw.polygon([
            (x, y - size),
            (x - head_width, y - size + head_offset),
            (x + head_width, y - size + head_offset)
        ], fill=color)
        return size * 2

    def draw_circle_on_image(self, draw, x, y, color, scale_multiplier=1.0):
        """画像上に円を描画"""
        radius = max(6, int(round(25 * scale_multiplier)))
        line_width = max(1, int(round(3 * scale_multiplier)))
        draw.ellipse([(x - radius, y - radius), (x + radius, y + radius)], outline=color, width=line_width)
        return radius * 2

    def draw_rectangle_on_image(self, draw, x, y, color, scale_multiplier=1.0):
        """画像上に四角を描画"""
        size = max(6, int(round(20 * scale_multiplier)))
        line_width = max(1, int(round(3 * scale_multiplier)))
        draw.rectangle([(x - size, y - size), (x + size, y + size)], outline=color, width=line_width)
        return size * 2

    def export_to_csv(self):
        """CSV形式で不具合一覧表を出力"""
        csv_file = os.path.join(self.project_path, "不具合一覧表フォルダ", "defect_list.csv")

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # ヘッダー - 項目を追加
            headers = ["ID", "エリア番号", "PCS番号", "接続箱番号", "回路番号", "アレイ№", "モジュール位置", "シリアル№",
                    "不良分類", "形状", "サーモ画像", "可視画像", "備考", "報告年月日", "X座標", "Y座標"]
            writer.writerow(headers)

            # データ
            for annotation in sorted(self.annotations, key=lambda x: x['id']):
                shape_name = next((k for k, v in self.annotation_shapes.items() 
                                if v == annotation.get("shape", "cross")), "十字")
                
                # サーモ画像のファイル名を命名規則に従って生成
                thermal_filename = ""
                if annotation.get('thermal_image'):
                    src_path = annotation['thermal_image']
                    if os.path.exists(src_path):
                        thermal_filename = f"ID{annotation['id']}_{annotation['defect_type']}_サーモ異常{os.path.splitext(src_path)[1]}"
                
                # 可視画像のファイル名を命名規則に従って生成
                visible_filename = ""
                if annotation.get('visible_image'):
                    src_path = annotation['visible_image']
                    if os.path.exists(src_path):
                        visible_filename = f"ID{annotation['id']}_{annotation['defect_type']}_可視異常{os.path.splitext(src_path)[1]}"
                
                row = [
                    annotation['id'],
                    annotation.get('area_no', ''),
                    annotation.get('pcs_no', ''),
                    annotation.get('junction_box_no', ''),
                    annotation.get('circuit_no', ''),
                    annotation.get('array_no', ''),           # 追加
                    annotation.get('module_position', ''),    # 追加
                    annotation.get('serial_no', ''),          # 追加
                    annotation.get('defect_type', ''),
                    shape_name,
                    thermal_filename,
                    visible_filename,
                    annotation.get('remarks', ''),
                    annotation.get('report_date', ''),        # 追加
                    annotation['x'],
                    annotation['y']
                ]
                writer.writerow(row)

    def export_to_excel(self):
        """Excel形式で不具合一覧表を出力"""
        excel_file = os.path.join(self.project_path, "不具合一覧表フォルダ", "defect_list.xlsx")

        # データフレーム作成
        data = []
        for annotation in sorted(self.annotations, key=lambda x: x['id']):
            shape_name = next((k for k, v in self.annotation_shapes.items() 
                            if v == annotation.get("shape", "cross")), "十字")
            
            # サーモ画像のファイル名を命名規則に従って生成
            thermal_filename = ""
            if annotation.get('thermal_image'):
                src_path = annotation['thermal_image']
                if os.path.exists(src_path):
                    thermal_filename = f"ID{annotation['id']}_{annotation['defect_type']}_サーモ異常{os.path.splitext(src_path)[1]}"
            
            # 可視画像のファイル名を命名規則に従って生成
            visible_filename = ""
            if annotation.get('visible_image'):
                src_path = annotation['visible_image']
                if os.path.exists(src_path):
                    visible_filename = f"ID{annotation['id']}_{annotation['defect_type']}_可視異常{os.path.splitext(src_path)[1]}"
            
            data.append({
                "ID": annotation['id'],
                "エリア番号": annotation.get('area_no', ''),
                "PCS番号": annotation.get('pcs_no', ''),
                "接続箱番号": annotation.get('junction_box_no', ''),
                "回路番号": annotation.get('circuit_no', ''),
                "アレイ№": annotation.get('array_no', ''),           # 追加
                "モジュール位置": annotation.get('module_position', ''), # 追加
                "シリアル№": annotation.get('serial_no', ''),          # 追加
                "不良分類": annotation.get('defect_type', ''),
                "形状": shape_name,
                "サーモ画像": thermal_filename,
                "可視画像": visible_filename,
                "備考": annotation.get('remarks', ''),
                "報告年月日": annotation.get('report_date', ''),        # 追加
                "X座標": annotation['x'],
                "Y座標": annotation['y']
            })

        df = pd.DataFrame(data)
        df.to_excel(excel_file, index=False, engine='openpyxl')

    # ------------- 拡張フォーマット（v2）出力 -------------
    def to_v2_row(self, annotation: dict):
        def g(key):
            v = annotation.get(key)
            if v is None:
                return None
            if isinstance(v, str) and v.strip() == '':
                return None
            return v
        return [
            g('area_no'),                            # エリア(工区)
            g('junction_box_no'),                    # 接続箱No.
            None,                                    # 接続箱（該当なし）
            g('circuit_no'),                         # 回路No.
            g('array_no'),                           # アレイ番号
            g('module_position'),                    # モジュール場所
            g('defect_type'),                        # 不良分類
            normalize_management_level(annotation.get('management_level')),  # 管理レベル
            g('serial_no'),                          # シリアルナンバー(交換前)
            g('report_no'),                          # 報告書番号
            g('disconnect_date'),                    # 離線した日
            g('disconnect_location'),                # 離線場所
            g('serial_after'),                       # シリアルナンバー(交換後)
            None,                                    # モジュール
            None,                                    # 列1
            g('reenergize_date'),                    # 送電完了日
            g('report_no2'),                         # 報告書番号2
            g('remarks'),                            # 備考
            g('report_date'),                        # 報告年月日
            g('id'),                                 # 採番
        ]

    def export_v2_csv(self):
        csv_file = os.path.join(self.project_path, "不具合一覧表フォルダ", "defect_list_v2.csv")
        os.makedirs(os.path.dirname(csv_file), exist_ok=True)
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f, lineterminator='\r\n')
            w.writerow(DEFECT_V2_HEADERS)
            for annotation in sorted(self.annotations, key=lambda x: x['id']):
                row = self.to_v2_row(annotation)
                w.writerow(['' if v is None else v for v in row])

    def export_v2_xlsx(self):
        excel_file = os.path.join(self.project_path, "不具合一覧表フォルダ", "defect_list.xlsx")
        os.makedirs(os.path.dirname(excel_file), exist_ok=True)
        try:
            wb = load_workbook(excel_file)
        except Exception:
            wb = Workbook()
        if 'defect_list_v2' in wb.sheetnames:
            wb.remove(wb['defect_list_v2'])
        ws = wb.create_sheet('defect_list_v2')
        ws.append(DEFECT_V2_HEADERS)
        for annotation in sorted(self.annotations, key=lambda x: x['id']):
            ws.append(self.to_v2_row(annotation))
        if 'Sheet' in wb.sheetnames and len(wb.sheetnames) > 1:
            try:
                wb.remove(wb['Sheet'])
            except Exception:
                pass
        wb.save(excel_file)

    def copy_related_images(self):
        """関連画像をプロジェクトフォルダにコピー"""
        for annotation in self.annotations:
            # サーモ画像のコピー
            if annotation.get('thermal_image'):
                src_path = annotation['thermal_image']
                if os.path.exists(src_path):
                    filename = f"ID{annotation['id']:03d}_{annotation['defect_type']}_サーモ異常{os.path.splitext(src_path)[1]}"
                    dst_path = os.path.join(self.project_path, "サーモ画像フォルダ", filename)
                    shutil.copy2(src_path, dst_path)

            # 可視画像のコピー
            if annotation.get('visible_image'):
                src_path = annotation['visible_image']
                if os.path.exists(src_path):
                    filename = f"ID{annotation['id']:03d}_{annotation['defect_type']}_可視異常{os.path.splitext(src_path)[1]}"
                    dst_path = os.path.join(self.project_path, "可視画像フォルダ", filename)
                    shutil.copy2(src_path, dst_path)

    def load_annotations(self):
        """アノテーションを読み込み"""
        try:
            annotation_file = os.path.join(self.project_path, "アノテーション設定フォルダ", "annotations.json")
            if os.path.exists(annotation_file):
                with open(annotation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.annotations = data.get('annotations', [])
                for ann in self.annotations:
                    try:
                        ann['id'] = int(ann.get('id', 0))
                    except (TypeError, ValueError):
                        ann['id'] = 0
                self.defect_types.update(data.get('defect_types', {}))
                self.annotation_shapes.update(data.get('annotation_shapes', {}))
                self.image_path = data.get('image_path', '')

                self.initialize_annotation_icons(reset_warning=False)

                if hasattr(self, 'defect_combo'):
                    defect_keys = list(self.defect_types.keys()) or [self.defect_var.get()]
                    self.defect_combo['values'] = defect_keys
                    if self.defect_var.get() not in self.defect_types and defect_keys:
                        self.defect_var.set(defect_keys[0])
                if hasattr(self, 'shape_combo'):
                    shape_keys = list(self.annotation_shapes.keys()) or [self.shape_var.get()]
                    self.shape_combo['values'] = shape_keys
                    if self.shape_var.get() not in self.annotation_shapes and shape_keys:
                        self.shape_var.set(shape_keys[0])

                # 次のIDを設定
                if self.annotations:
                    max_id = max(ann['id'] for ann in self.annotations)
                    self.next_id = max_id + 1
                else:
                    self.next_id = 1

                self.update_table()
                if self.current_image:
                    self.draw_annotations()

        except Exception as e:
            messagebox.showerror("エラー", f"アノテーションの読み込みに失敗しました: {str(e)}")

    def quit_application(self):
        """アプリケーションを終了"""
        if self.annotations:
            result = messagebox.askyesnocancel("確認", "変更を保存しますか？")
            if result is True:  # Yes
                self.save_project()
                self.root.quit()
            elif result is False:  # No
                self.root.quit()
            # Cancel の場合は何もしない
        else:
            self.root.quit()

    
def main():
    """メイン関数"""
    root = tk.Tk()
    app = OrthoImageAnnotationSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()
