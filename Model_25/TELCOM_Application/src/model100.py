# transparent_editor.py
import tkinter as tk
import tkinter.font as tkfont
from PIL import Image, ImageTk
import os, sys, platform, time
import serial, threading
from openai import OpenAI

# ---------- 配置 ----------

# 串口配置
SERIAL_PORT = "COM5"
BAUDRATE = 9600
BYTESIZE = 8
PARITY = "N"
STOPBITS = 1

# 图形界面配置
WINDOW_W, WINDOW_H = 1280, 480
BG_FILENAME = "Background.png"

TEXT_X, TEXT_Y = 110, 100
TEXT_W_PIXELS, TEXT_H_PIXELS = 1060, 270
TEXT_COLS, TEXT_ROWS = 40, 8
TEXT_SIZE_RATIO = 1.3
TEXT_SPACING = 5
LINE_SPACING = -6
PREFERRED_FONTS = ["Another Mans Treasure MIA Raw", "Consolas", "Courier New", "Courier", "Menlo", "Monaco"]

# 退出区域
EXIT_X, EXIT_Y, EXIT_W, EXIT_H = 1059, 403, 88, 22

# DEEPSEEK
API_KEY = "YOUR API KEY"

# -------------------------

def find_max_mono_font(root, family_candidates, max_width_px, max_height_px, cols, rows, max_try=120):
    """
    返回一个 tkfont.Font 对象（等宽字体首选），尽可能大的字号以满足 cols x rows
    在指定像素框内显示。
    """
    for family in family_candidates:
        for size in range(min(max_try, 200), 4, -1):
            try:
                f = tkfont.Font(root=root, family=family, size=size)
            except tk.TclError:
                # 系统上可能没有这个字体
                break
            char_w = f.measure("0")
            line_h = f.metrics("linespace")
            if char_w * cols <= max_width_px * TEXT_SIZE_RATIO and line_h * rows <= max_height_px * TEXT_SIZE_RATIO:
                return f
    # 回退到系统默认等宽近似（尝试最后一个候选字体小字号），或默认字号
    try:
        return tkfont.Font(root=root, family=family_candidates[-1], size=12)
    except Exception:
        return tkfont.Font(root=root, size=12)

class TransparentTextEditor:
    def __init__(self, root):
        self.root = root

        # 串口初始化
        try:
            self.ser = serial.Serial(port = SERIAL_PORT, baudrate = BAUDRATE, bytesize = BYTESIZE, parity = PARITY, stopbits = STOPBITS, timeout=0.3)
        except Exception as e:
            print(f"串口打开失败: {e}")
            self.ser = None

        # 启动串口读取线程
        if self.ser:
            self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.serial_thread.start()
        self.buffer = ""

        # GUI初始化
        # 背景画布
        self.canvas = tk.Canvas(root, width=WINDOW_W, height=WINDOW_H, highlightthickness=0, bd=0, takefocus=1)
        self.canvas.pack()

        # 加载背景图
        if not os.path.exists(BG_FILENAME):
            print(f"错误：找不到背景图片 '{BG_FILENAME}'。请将图片放在脚本同目录并命名为 {BG_FILENAME}")
            sys.exit(1)
        pil_img = Image.open(BG_FILENAME)
        if pil_img.size != (WINDOW_W, WINDOW_H):
            pil_img = pil_img.resize((WINDOW_W, WINDOW_H), Image.LANCZOS)
        self.bg_img = ImageTk.PhotoImage(pil_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.bg_img)

        # 选定字体（尽量等宽并最大化）
        self.font = find_max_mono_font(root, PREFERRED_FONTS, TEXT_W_PIXELS, TEXT_H_PIXELS, TEXT_COLS, TEXT_ROWS)
        # 字符宽高（以单字符为准）
        self.char_width = max(1, self.font.measure("0"))
        self.line_height = max(1, self.font.metrics("linespace")) + LINE_SPACING

        # 文本存储：单一字符串 + 光标索引（相对于 raw_text 的位置）
        self.raw_text = ""      # 原始文本，包含换行符 '\n'
        self.cursor_index = 0   # 插入点在 raw_text 中的位置 (0..len(raw_text))

        # 可视化配置
        self.view_start = 0      # display_lines 的起始可视行索引
        self.cursor_visible = True

        # 闪烁周期（ms）
        self.blink_period = 500

        # 滚动条（放在文本区右侧）
        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.scroll_command)
        # 将 scrollbar 放到文本区域右侧外面一点（像素坐标）
        #sb_x = TEXT_X + TEXT_W_PIXELS + 6
        #self.scrollbar.place(x=sb_x, y=TEXT_Y, height=TEXT_H_PIXELS)


        # 事件绑定
        # 使用 root 捕获键盘事件（确保程序窗口有焦点）
        #root.bind_all("<Key>", self.on_key, add=True)
        # 处理粘贴 (Windows/Linux: Control-v, macOS: Command-v)
        #root.bind_all("<Control-v>", self.on_paste, add=True)
        #root.bind_all("<Command-v>", self.on_paste, add=True)  # macOS

        # 改为绑定到 canvas（需要在创建 self.canvas 之后执行）
        # 使 canvas 成为可聚焦控件并接收键盘事件
        self.canvas.focus_set()
        self.canvas.bind("<Key>", self.on_key)
        # 同时保留对粘贴的处理（如果之前用 root.bind_all("<Control-v>"...)，改为 canvas）
        self.canvas.bind("<Control-v>", self.on_paste)
        # macOS 的 Command-v 可选
        self.canvas.bind("<Command-v>", self.on_paste)

        # 鼠标单击用于设置光标
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        # 鼠标滚轮
        if platform.system() == "Windows":
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        elif platform.system() == "Darwin":
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # macOS also uses MouseWheel but delta scale differs
        else:
            # Linux: Button-4 / Button-5
            self.canvas.bind("<Button-4>", lambda e: self.on_mouse_wheel(e, step= -1))
            self.canvas.bind("<Button-5>", lambda e: self.on_mouse_wheel(e, step= 1))

        # 初始化显示（必须在 scrollbar 创建、事件绑定、字体测量之后）
        self.rebuild_display()
        # 启动光标闪烁（要在 view_start 等属性初始化之后）
        self.blink_id = None  # 初始化
        self.blink_cursor()

        # 确保窗口能接收键盘焦点
        #root.focus_force()

        # DEEPSEEK 初始化
        self.deepseek_mode = False  # 是否进入 DeepSeek 模式
        if platform.system() == "Linux":
            self.focus_on_cavans()


    def focus_on_cavans(self):

        def _ensure_focus():
            try:
                # 先让窗口置顶、更新并请求焦点
                self.root.update_idletasks()
                self.root.lift()
                # 临时置顶以确保窗口管理器把焦点给我们（有时需要）
                try:
                    self.root.attributes("-topmost", True)
                    self.root.attributes("-topmost", False)
                except Exception:
                    pass
                # 强制给 canvas 焦点
                self.canvas.focus_set()
                self.root.focus_force()
                # 全局抓取（可选、若你希望阻止输入落到其他窗口）
                try:
                    self.root.grab_set_global()   # 某些WM会强制失焦，因此用全局抓取()
                except Exception:
                    # 在某些 Wayland/WM 上会失败，这里忽略异常
                    pass
            except Exception:
                pass
            
        # 安排一次延后执行（确保窗口已 map）
        self.root.after(100, _ensure_focus)
        # 同时防护：当用户用鼠标点击文本区时重新设焦点
        self.canvas.bind("<Button-1>", lambda e: (self.canvas.focus_set(), self.on_mouse_click(e)))
        self.canvas.bind("<ButtonRelease-1>", lambda e: (self.canvas.focus_set()))
        # 当窗口获得焦点时确保 canvas 也获得焦点
        self.root.bind("<FocusIn>", lambda e: self.canvas.focus_set())
 
    # ---------------- 文本与显示行重建 ----------------
    def rebuild_display(self):
        """
        根据 raw_text 和 TEXT_COLS（每行最大字符数）生成 display_lines（列表）和 line_ranges（每行对应的 raw_text 索引范围）。
        line_ranges[i] = (start_raw_index, end_raw_index_exclusive)
        """
        s = self.raw_text
        n = len(s)
        self.display_lines = []
        self.line_ranges = []

        if n == 0:
            # 空文本，显示一行空白
            self.display_lines.append("")
            self.line_ranges.append((0, 0))
            return

        i = 0
        while i < n:
            next_nl = s.find("\n", i)
            if next_nl == -1:
                # 段落到末尾
                segment = s[i:n]
                if len(segment) == 0:
                    # 末尾正好是空，不添加额外行（已在上次 newline 处理）
                    pass
                else:
                    for k in range(0, len(segment), TEXT_COLS):
                        start_raw = i + k
                        end_raw = min(i + k + TEXT_COLS, n)
                        self.display_lines.append(s[start_raw:end_raw])
                        self.line_ranges.append((start_raw, end_raw))
                break
            else:
                segment = s[i:next_nl]
                if len(segment) == 0:
                    # 空行
                    self.display_lines.append("")
                    self.line_ranges.append((i, i))
                else:
                    for k in range(0, len(segment), TEXT_COLS):
                        start_raw = i + k
                        end_raw = min(i + k + TEXT_COLS, next_nl)
                        self.display_lines.append(s[start_raw:end_raw])
                        self.line_ranges.append((start_raw, end_raw))
                # 如果换行符在文本末尾（raw_text 最后一位是 '\n'），需要额外一个空行来表示末尾空行
                if next_nl == n - 1:
                    self.display_lines.append("")
                    self.line_ranges.append((n, n))
                i = next_nl + 1

        # 边界保护：至少有一行
        if not self.display_lines:
            self.display_lines.append("")
            self.line_ranges.append((0, 0))

    def raw_index_to_display_pos(self, raw_idx):
        """
        将 raw_text 的索引映射为 (display_line_index, column_in_that_line)
        """
        # clamp
        if raw_idx < 0:
            raw_idx = 0
        if raw_idx > len(self.raw_text):
            raw_idx = len(self.raw_text)

        for i, (a, b) in enumerate(self.line_ranges):
            # 区间是 [a, b)
            if raw_idx >= a and raw_idx <= b:
                col = raw_idx - a
                return i, col
        # 没找到（理论上不该发生） -> 放到最后一行行尾
        last = len(self.display_lines) - 1
        last_start, last_end = self.line_ranges[last]
        return last, last_end - last_start

    def display_pos_to_raw_index(self, display_line_idx, col):
        """
        将显示行索引和列映射为 raw_text 的索引
        """
        if display_line_idx < 0:
            display_line_idx = 0
        if display_line_idx >= len(self.display_lines):
            display_line_idx = len(self.display_lines) - 1
        start, end = self.line_ranges[display_line_idx]
        col = max(0, min(col, end - start))
        return start + col

    # ----------------- 插入 / 删除 / 光标移动 -----------------
    def insert_text_at_cursor(self, text_to_insert: str):
        if not text_to_insert:
            return
        # 插入
        s = self.raw_text
        pos = self.cursor_index
        self.raw_text = s[:pos] + text_to_insert + s[pos:]
        # 更新光标位置
        self.cursor_index += len(text_to_insert)
        # 重建显示，并确保光标可见
        self.rebuild_display()
        self.ensure_cursor_visible()
        self.refresh()

    def backspace(self):
        if self.cursor_index <= 0:
            return
        s = self.raw_text
        pos = self.cursor_index
        self.raw_text = s[:pos-1] + s[pos:]
        self.cursor_index -= 1
        self.rebuild_display()
        self.ensure_cursor_visible()
        self.refresh()

    def move_left(self):
        if self.cursor_index > 0:
            self.cursor_index -= 1
            self.rebuild_display()
            self.ensure_cursor_visible()
            self.refresh()

    def move_right(self):
        if self.cursor_index < len(self.raw_text):
            self.cursor_index += 1
            self.rebuild_display()
            self.ensure_cursor_visible()
            self.refresh()

    def move_up(self):
        self.rebuild_display()
        line, col = self.raw_index_to_display_pos(self.cursor_index)
        if line > 0:
            prev_len = len(self.display_lines[line - 1])
            new_col = min(col, prev_len)
            self.cursor_index = self.display_pos_to_raw_index(line - 1, new_col)
            self.ensure_cursor_visible()
            self.refresh()

    def move_down(self):
        self.rebuild_display()
        line, col = self.raw_index_to_display_pos(self.cursor_index)
        if line < len(self.display_lines) - 1:
            next_len = len(self.display_lines[line + 1])
            new_col = min(col, next_len)
            self.cursor_index = self.display_pos_to_raw_index(line + 1, new_col)
            self.ensure_cursor_visible()
            self.refresh()

    # ----------------- UI / 滚动 / 刷新 -----------------
    def ensure_cursor_visible(self):
        """
        确保光标所在的 display_line 在可视区域内；如果不在则调整 self.view_start
        """
        self.rebuild_display()
        line_idx, _ = self.raw_index_to_display_pos(self.cursor_index)
        max_start = max(0, len(self.display_lines) - TEXT_ROWS)
        if line_idx < self.view_start:
            self.view_start = max(0, min(line_idx, max_start))
        elif line_idx >= self.view_start + TEXT_ROWS:
            self.view_start = max(0, min(line_idx - TEXT_ROWS + 1, max_start))
        # 更新 scrollbar 位置
        self.update_scrollbar()

    def update_scrollbar(self):
        total = len(self.display_lines)
        if total <= TEXT_ROWS:
            self.scrollbar.set(0.0, 1.0)
        else:
            a = self.view_start / total
            b = min(1.0, (self.view_start + TEXT_ROWS) / total)
            self.scrollbar.set(a, b)

    def scroll_command(self, *args):
        """
        被 scrollbar 调用：
        args 格式可能为 ('moveto', fraction) 或 ('scroll', number, 'units'/'pages')
        """
        total = len(self.display_lines)
        if total == 0:
            return
        cmd = args[0]
        if cmd == "moveto":
            frac = float(args[1])
            new_start = int(frac * total)
            new_start = max(0, min(new_start, max(0, total - TEXT_ROWS)))
            self.view_start = new_start
        elif cmd == "scroll":
            amount = int(args[1])
            what = args[2] if len(args) > 2 else "units"
            if what == "units":
                self.view_start += amount
            else:  # pages
                self.view_start += amount * TEXT_ROWS
            self.view_start = max(0, min(self.view_start, max(0, total - TEXT_ROWS)))
        self.refresh()

    def on_mouse_wheel(self, event, step=None):
        # Windows/macOS: event.delta, Linux: event parameter step
        if step is None:
            # Windows: delta is multiple of 120 (positive away from user)
            delta = 0
            if hasattr(event, "delta"):
                delta = event.delta
            # macOS delta smaller scale, normalize:
            step = -int(delta / 120) if delta != 0 else 0
        # 向上滚动 step < 0 ? adjust sign
        self.view_start += step
        self.view_start = max(0, min(self.view_start, max(0, len(self.display_lines) - TEXT_ROWS)))
        self.refresh()

    def on_mouse_click(self, event):
        x, y = event.x, event.y
        # 仅在文本区内才定位光标
        if not (TEXT_X <= x <= TEXT_X + TEXT_W_PIXELS and TEXT_Y <= y <= TEXT_Y + TEXT_H_PIXELS):
            return
        rel_x = x - TEXT_X
        rel_y = y - TEXT_Y
        clicked_row = int(rel_y // self.line_height)
        clicked_row = max(0, min(clicked_row, TEXT_ROWS - 1))
        target_display_idx = self.view_start + clicked_row
        if target_display_idx >= len(self.display_lines):
            # 放到最后一行行尾
            self.cursor_index = len(self.raw_text)
        else:
            clicked_col = int(rel_x // self.char_width)
            clicked_col = max(0, clicked_col)
            self.cursor_index = self.display_pos_to_raw_index(target_display_idx, clicked_col)
        self.ensure_cursor_visible()
        self.refresh()

    def on_key(self, event):
        # 处理按键（尽量覆盖常见的）
        # 注意：Ctrl/Alt 组合键仍会触发但 event.char 可能为空
        key = event.keysym
        if key == "BackSpace":
            self.backspace()
            return "break"
        elif key == "Left":
            self.move_left()
            return "break"
        elif key == "Right":
            self.move_right()
            return "break"
        elif key == "Up":
            self.move_up()
            return "break"
        elif key == "Down":
            self.move_down()
            return "break"
        elif key == "Return":
            self.insert_text_at_cursor("\n")
            self.send_serial("\n\r")  # 发送字符到串口
            return "break"
        else:
            ch = event.char
            # printable characters（排除 control keys）
            if ch and ord(ch) >= 32:
                self.insert_text_at_cursor(ch)
                self.send_serial(ch)  # 发送字符到串口
                return "break"
        # 未处理的按键交给系统
        return

    def on_paste(self, event):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        # 将粘贴的内容直接插入（保留换行）
        self.insert_text_at_cursor(text)
        return "break"

    def blink_cursor(self):
        self.cursor_visible = not self.cursor_visible
        self.refresh()
        self.blink_id = self.root.after(self.blink_period, self.blink_cursor)

    def refresh(self):
        """
        根据 current view_start 和 display_lines 绘制当前可视文本区以及光标。
        """
        self.rebuild_display()
        # 清除旧的文本/光标
        self.canvas.delete("text")
        # 绘制每一行（最多 TEXT_ROWS 行）
        for i in range(TEXT_ROWS):
            display_idx = self.view_start + i
            if display_idx < len(self.display_lines):
                line_text = self.display_lines[display_idx]
            else:
                line_text = ""
            # 文本左上角放置，留一点内边距
            for j in range(len(line_text)):
                px = TEXT_X + 2 + j * (self.char_width + TEXT_SPACING)
                py = TEXT_Y + i * self.line_height + 1
                # create_text 支持 font 对象或(fontname, size) 元组
                self.canvas.create_text(px, py, anchor="nw", text=line_text[j], font=self.font, tags="text")
        # 绘制光标
        if self.cursor_visible:
            line_idx, col = self.raw_index_to_display_pos(self.cursor_index)
            if self.view_start <= line_idx < self.view_start + TEXT_ROWS:
                vis_row = line_idx - self.view_start
                cx = TEXT_X + col * (self.char_width + TEXT_SPACING)
                cy1 = TEXT_Y + vis_row * self.line_height + 2
                cy2 = cy1 + self.line_height - 4
                self.canvas.create_line(cx, cy1, cx, cy2, width=2, tags="text")
        # 更新滚动条
        self.update_scrollbar()


# ----------------- 串口处理 -----------------
    def read_serial(self):
        while True:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                    if data:
                        if data != "\r":
                            self.buffer += data
                            self.insert_text_at_cursor(data)
                        if data == "\n" :
                            # 检查是否进入 DeepSeek 模式
                            if "##DEEPSEEK##" in self.buffer:
                                self.deepseek_mode = True
                                self.buffer = ""
                                self.insert_text_at_cursor("Enter DeepSeek mode...\n")
                                self.send_serial("Enter DeepSeek mode...\r\n")
                                continue

                            # 检查是否退出 DeepSeek 模式
                            if "##EXIT##" in self.buffer:
                                self.deepseek_mode = False
                                self.buffer = ""
                                self.insert_text_at_cursor("Exit DeepSeek mode...\n")
                                self.send_serial("Exit DeepSeek mode...\r\n")
                                continue


                            # 如果在 DeepSeek 模式，直接发送数据给 DeepSeek API
                            if self.deepseek_mode and self.buffer :
                                text_to_send = self.buffer
                                self.buffer = ""
                                self.insert_text_at_cursor("Message sent, please wait...\n")
                                self.send_serial("Message sent, please wait...\r\n")
                                response_text = self.deepseek_process(text_to_send)
                                if response_text:
                                    self.send_response_slowly(response_text, delay=5)  # 每字符间隔 0.005s
            except Exception as e:
                print(f"串口读取错误: {e}")
                break
            
    def send_response_slowly(self, text, delay=5):
        """
        逐字符显示和发送
        delay 单位是毫秒，5 表示 0.005s
        """
        def send_next(i=0):
            if i < len(text):
                c = text[i]
                # 显示到屏幕
                self.insert_text_at_cursor(c)
                # 发送到串口
                self.send_serial(c)
                # 安排下一次调用
                self.root.after(delay, send_next, i+1)
            else:
                self.insert_text_at_cursor("\n")
                self.send_serial("\r\n")  # 最后输出换行结束

        send_next(0)  # 从第一个字符开始

    def send_serial(self, text):
        if self.ser:
            try:
                self.ser.write(text.encode())
            except Exception as e:
                print(f"串口发送错误: {e}")

# ----------------- DEEPSEEK处理 -----------------
    def deepseek_process(self, text):
        try:
            client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": text},
                ],
                stream=False
            )

            # 返回内容
            return response.choices[0].message.content
        except Exception as e:
            print(f"DeepSeek API 请求失败: {e}")
            return "[DeepSeek Error]\n"

# ----------------- 主程序 -----------------
def main():
    root = tk.Tk()
    root.title("NEO Model 100")
    root.geometry(f"{WINDOW_W}x{WINDOW_H}")
    root.resizable(False, False)
    root.overrideredirect(True)  # 无边框窗口

    app = TransparentTextEditor(root)

    exit_rect = app.canvas.create_rectangle(
        EXIT_X, EXIT_Y, EXIT_X+EXIT_W, EXIT_Y+EXIT_H,
        outline="", fill="", tags="exit"  # 透明区域
    )

    # 关闭窗口事件
    def custom_exit_dialog(event=None,):
        x = 540
        y = 190
        dialog = tk.Toplevel(app.root)
        dialog.geometry(f"200x100+{x}+{y}")   # 自定义坐标
        dialog.overrideredirect(True)        # 允许 WM 管理这个小窗口
        dialog.wm_attributes("-topmost", True)   # 强制置顶
        dialog.transient(app.root)                # 绑定主窗口

        label = tk.Label(dialog, text="是否退出程序？", font=("Arial", 12))
        label.pack(pady=10)

        def do_exit():
            if hasattr(app, "blink_id") and app.blink_id is not None:
                app.root.after_cancel(app.blink_id)  # 安全取消定时器
                app.blink_id = None
            app.canvas.delete("all")  # 清空CANVAS
            del app.bg_img  # 释放 PhotoImage
            app.root.quit()
            app.root.after(100, app.root.destroy)  # 延迟销毁

        def cancel():
            dialog.destroy()
            app.focus_on_cavans()

        btn_ok = tk.Button(dialog, text="确定", command=do_exit)
        btn_ok.pack(side="left", padx=20, pady=10)

        btn_cancel = tk.Button(dialog, text="取消", command=cancel)
        btn_cancel.pack(side="right", padx=20, pady=10)
        
        # 先让窗口绘制出来
        dialog.update_idletasks()

        dialog.grab_set()                     # 模态
        dialog.lift()                         # 提升 Z 序
        dialog.focus_force()                  # 获取焦点
        dialog.attributes("-topmost", True)   # 永远在最上层

        return dialog

    app.canvas.tag_bind("exit", "<Button-1>", custom_exit_dialog)

    root.mainloop()

if __name__ == "__main__":
    main()