#!/usr/bin/env python3
# 素材预处理：彩色底 JPG -> 纯黑白透明 PNG（统一黑白版画风）
import os
from PIL import Image, ImageOps, ImageFilter, ImageDraw

SRC = "/Users/panshaoye/Desktop/Zcode 图片素材包"
PACK = os.path.join(SRC, "人物+怪物")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets")
os.makedirs(OUT, exist_ok=True)


def load_gray(path):
    img = Image.open(path).convert("L")
    return ImageOps.autocontrast(img, cutoff=1)


def process_region(path, box=None, thr=128, fg=(0, 0, 0, 255), hole=(255, 255, 255, 255),
                   maxside=340, erase=None):
    """通用管线：阈值二值化 -> 边界泛洪判定外部背景(透明) -> 主体按极性填 fg/内部孔洞填 hole。"""
    g = load_gray(path)
    if box:
        g = g.crop(box)
    mask = g.point(lambda p: 255 if p >= thr else 0, mode="L")  # 255=亮 0=暗
    # 从四角+边中点泛洪：与边界同极性的连通区 = 外部背景
    ext = mask.copy()
    w, h = ext.size
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
             (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    for s in seeds:
        if ext.getpixel(s) in (0, 255):
            ImageDraw.floodfill(ext, s, 128, thresh=0)
    mp = mask.load()
    ep = ext.load()
    # 统计 enclosed 区域主体极性
    dark = light = 0
    for y in range(h):
        for x in range(w):
            if ep[x, y] != 128:
                if mp[x, y] == 0:
                    dark += 1
                else:
                    light += 1
    if dark == 0 and light == 0:
        return None
    subject_dark = dark >= light
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    fgp = fg
    hlp = hole
    for y in range(h):
        for x in range(w):
            if ep[x, y] == 128:
                continue
            is_dark = mp[x, y] == 0
            if is_dark == subject_dark:
                op[x, y] = fgp
            else:
                op[x, y] = hlp
    if erase:
        d = ImageDraw.Draw(out)
        d.rectangle(erase, fill=(0, 0, 0, 0))
    bb = out.getbbox()
    if not bb:
        return None
    out = out.crop(bb)
    w2, h2 = out.size
    scale = min(1.0, maxside / max(w2, h2))
    if scale < 1.0:
        out = out.resize((max(1, int(w2 * scale)), max(1, int(h2 * scale))), Image.NEAREST)
    return out


def save(img, name):
    img.save(os.path.join(OUT, name))
    print(f"{name:24s} {img.size[0]}x{img.size[1]}")


B = (0, 0, 0, 255)     # 黑墨
W = (255, 255, 255, 255)  # 纸白

# ---- 主角（三张最左侧图）----
save(process_region(os.path.join(SRC, "8c341e7fec2f9f6034833062081cfafd.jpg"),
                    thr=110, maxside=420, erase=(0.55, 0.90, 1.0, 1.0)), "hero_reaper.png")  # 钟形盔刺客(去右下签名)
save(process_region(os.path.join(SRC, "84cb18d04fdb978f62ffbb16a697cac0.jpg"),
                    thr=120, maxside=520), "hero_moon.png")    # 月下间谍(黑底白月)
save(process_region(os.path.join(SRC, "dcd8b73db15c5493f2914e7de1cfe909.jpg"),
                    thr=120, maxside=460), "hero_spy.png")     # 礼帽间谍

# ---- 怪物/守卫 ----
P = lambda n: os.path.join(PACK, n)
save(process_region(P("74fc9b594eccacbe445047b46817157f.jpg"), thr=120, maxside=300), "mob_cat.png")
save(process_region(P("1836788f7a74c6583ed7fba8fd532073.jpg"), thr=100, maxside=340), "mob_samurai.png")
save(process_region(P("c51f194078d50789e95c26af9002c1f2.jpg"), thr=110, maxside=320), "mob_monkey.png")
save(process_region(P("d466e60c1586b89f6358dc4cee97be11.jpg"), thr=110, maxside=300), "mob_bear.png")
save(process_region(P("8dbc0f7c795014f3d083d63490a08d04.jpg"), thr=120, maxside=340), "mob_dragon.png")
save(process_region(P("817331bf3fc6da3e997853989a0c1f97.jpg"), thr=110, maxside=360), "mob_face.png")
# 红蓝双翼兽：上下切半，各自出一只猎犬
img = Image.open(P("640cf675c57567c2ed073b505211e635.jpg"))
w, h = img.size
save(process_region(P("640cf675c57567c2ed073b505211e635.jpg"), box=(0, 0, w, int(h * 0.5)),
                    thr=52, maxside=300), "mob_hound1.png")
save(process_region(P("640cf675c57567c2ed073b505211e635.jpg"), box=(0, int(h * 0.5), w, h),
                    thr=52, maxside=300), "mob_hound2.png")
# 地窖三怪（黑底房间用白色主体，孔洞为黑）
DK = (255, 255, 255, 255)
DH = (0, 0, 0, 255)
save(process_region(P("0028ac93930d576da90a5001a0a3acfc.jpg"), thr=110, maxside=340, fg=DK, hole=DH), "mob_skeleton_w.png")
save(process_region(P("317eb22315c60a5afa0523c5e6fcc826.jpg"), thr=110, maxside=340, fg=DK, hole=DH), "mob_serpent_w.png")
save(process_region(P("813b62350f4da7bb7d5a01e5aa445bff.jpg"), thr=110, maxside=300, fg=DK, hole=DH), "mob_croc_w.png")

# ---- 路人 ----
save(process_region(P("7676f76f3120fae436019860b893495f.jpg"), thr=110, maxside=340), "npc_horse.png")


def cut_crowd(path, prefix="npc", n=10):
    g = load_gray(path)
    W0, H0 = g.size
    small = g.point(lambda p: 255 if p >= 128 else 0).resize((300, 300), Image.NEAREST)
    px = small.load()
    seen = [[False] * 300 for _ in range(300)]
    boxes = []
    for yy in range(300):
        for xx in range(300):
            if px[xx, yy] == 0 and not seen[yy][xx]:
                stack = [(xx, yy)]
                seen[yy][xx] = True
                x0 = x1 = xx
                y0 = y1 = yy
                area = 0
                while stack:
                    cx, cy = stack.pop()
                    area += 1
                    x0 = min(x0, cx); x1 = max(x1, cx)
                    y0 = min(y0, cy); y1 = max(y1, cy)
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < 300 and 0 <= ny < 300 and not seen[ny][nx] and px[nx, ny] == 0:
                            seen[ny][nx] = True
                            stack.append((nx, ny))
                bw, bh = x1 - x0, y1 - y0
                if area > 60 and bh > 35:  # 过滤碎块
                    boxes.append((area, x0, y0, x1, y1))
    boxes.sort(reverse=True)
    sx, sy = W0 / 300, H0 / 300
    made = 0
    pad = 6
    for i, (area, x0, y0, x1, y1) in enumerate(boxes[:n]):
        box = (max(0, int(x0 * sx) - pad), max(0, int(y0 * sy) - pad),
               min(W0, int((x1 + 1) * sx) + pad), min(H0, int((y1 + 1) * sy) + pad))
        r = process_region(path, box=box, thr=128, maxside=300)
        if r and r.size[0] > 30 and r.size[1] > 60:
            save(r, f"{prefix}_{i}.png")
            made += 1
    print(f"crowd cut: {made} figures")


cut_crowd(P("21ff7370640b6aaa5b5537edec40d861.jpg"))

# 联络表：快速人工检查
names = sorted(f for f in os.listdir(OUT) if f.endswith(".png"))
cols = 6
cell = 200
rows = (len(names) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell, rows * cell), (235, 233, 226))
d = ImageDraw.Draw(sheet)
for i, n in enumerate(names):
    im = Image.open(os.path.join(OUT, n)).convert("RGBA")
    im.thumbnail((cell - 24, cell - 40), Image.NEAREST)
    cx, cy = (i % cols) * cell, (i // cols) * cell
    sheet.paste(im, (cx + (cell - im.size[0]) // 2, cy + (cell - 20 - im.size[1]) // 2), im)
    d.text((cx + 6, cy + cell - 18), n.replace(".png", ""), fill=(20, 20, 20))
sheet.save(os.path.join(HERE, "contact_sheet.png"))
print("sheet ->", os.path.join(HERE, "contact_sheet.png"))
