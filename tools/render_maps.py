#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地形蓝图生成器：从 index.html 的 LEVELS 数据渲染每关的俯视参考图。
用法：python3 tools/render_maps.py
输出：maps/ 下每关一张 PNG + 总览拼图
说明：图中网格与坐标 = LEVELS 数组里的原始坐标（构建时整体 ×1.9 生效），
     改地形时直接对照图上的坐标改 LEVELS 即可。
"""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'maps')
os.makedirs(OUT, exist_ok=True)

FONT_CANDIDATES = ['/System/Library/Fonts/STHeiti Light.ttc',
                   '/System/Library/Fonts/Hiragino Sans GB.ttc',
                   '/System/Library/Fonts/Supplemental/Songti.ttc']
FONT_PATH = next(p for p in FONT_CANDIDATES if os.path.exists(p))

def F(size):
    return ImageFont.truetype(FONT_PATH, size)

# ---------- 1. 从 index.html 提取 LEVELS 数据 ----------
GAME_FILE = os.path.join(OUT, '_game.js')

def extract_levels():
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    game = re.search(r'<script>([\s\S]*)</script>', html).group(1)
    open(GAME_FILE, 'w', encoding='utf-8').write(game)

    wfile = os.path.join(OUT, '_extract.js')
    wrapper = """ObjC.import("Foundation");
function readFile(p){ return ObjC.unwrap($.NSString.stringWithContentsOfFileEncodingError(p, $.NSUTF8StringEncoding, null)); }
var __CAP = { listeners: [], workers: [] };
var universal = new Proxy(function(){}, {
  get: function(t,p){ if (p === Symbol.toPrimitive) return function(){ return 0; }; return universal; },
  apply: function(){ return universal; },
  set: function(){ return true; },
  construct: function(){ return universal; }
});
var document = {
  getElementById: function(){ return { width: 960, height: 640, getContext: function(){ return universal; }, addEventListener: function(){} }; },
  createElement: function(){ return { width:0, height:0, getContext: function(){ return universal; } }; }
};
function addEventListener(type, f){ __CAP.listeners.push({type:type, f:f}); }
var localStorage = { getItem:function(){ return null; }, setItem:function(){} };
var location = { search: "" };
var performance = { now: function(){ return 0; } };
function requestAnimationFrame(){ return 0; }
function setTimeout(f, t){ return 0; }
function URLSearchParams(s){ this.s = s || ""; }
URLSearchParams.prototype.has = function(){ return false; };
URLSearchParams.prototype.get = function(){ return null; };
function Worker(url){ this.postMessage = function(){}; }
var URL = { createObjectURL: function(){ return ""; } };
var Blob = function(){};
var console = { warn: function(){}, log: function(){} };
var window = {};
function Image(){ this.width = 0; this.height = 0; }
(function(){
  var stubs = "";
  var game = readFile("%GAME%");
  try {
    eval(stubs + "\\n" + game + "\\n;__CAP.OUT = JSON.stringify({SC: SC, ROOM: ROOM, LEVELS: LEVELS});");
    return __CAP.OUT;
  } catch (e) { return "ERR:" + e.message; }
})()"""
    wrapper = wrapper.replace('%GAME%', GAME_FILE)
    open(wfile, 'w', encoding='utf-8').write(wrapper)
    r = subprocess.run(['osascript', '-l', 'JavaScript', wfile], capture_output=True, text=True, timeout=60)
    if not r.stdout.strip():
        print('JXA STDERR:', r.stderr[:400]); sys.exit(1)
    out = r.stdout.strip()
    os.remove(wfile)
    if out.startswith('ERR'):
        raise RuntimeError(out)
    return json.loads(out)

def room_xy(x, y, ox, oy):
    return (ox + (x - 40), oy + (y - 72))

SC_HINT = '网格/坐标 = LEVELS 原始坐标（构建时 ×1.9 生效）· 每格 100'
GNAME = {'mob_cat':'纹章猫','mob_samurai':'武士','mob_monkey':'猴子','mob_bear':'熊',
         'mob_skeleton':'骷髅','mob_serpent':'蛇怪','mob_croc':'巨鳄BOSS','mob_dragon':'三头龙',
         'mob_hound1':'双翼兽','mob_hound2':'双翼兽','mob_face':'四脸石像','npc_6':'光束雕像','npc_2':'光环雕像'}
TNAME = {'scan':'驻足环视','slow':'慢转远视','dart':'乱窜','charge':'咆哮冲锋','ghost':'穿墙感知',
         'lance':'吐信突刺','phase':'穿墙白影','triple':'三首环顾','sniff':'循迹追踪','beam':'旋转光束',
         'aura':'全视光环','boss':'永不遗忘','':'普通巡逻','fixed':'固定扫视'}
FNAME = {'table':'桌','shelf':'架','sofa':'沙发','safe':'保险柜','crate':'箱','bench':'长椅','coffin':'棺'}
TVAL = {'coin':'金币','gem':'宝石','vase':'花瓶','crown':'王冠','pic':'名画'}

def render_level(L, idx, total):
    dark = L.get('dark', False)
    W, H = 1000, 850
    ox, oy = 70, 118
    img = Image.new('RGB', (W, H), '#f4f2ec')
    g = ImageDraw.Draw(img)
    f = {s: F(s) for s in (12, 13, 15, 17, 20, 26, 30)}

    g.text((30, 16), f'{L["name"]}', font=f[30], fill='#000')
    sub = '黑暗关（迷雾加浓）' if dark else '普通光照'
    g.text((W-30-8*len(sub), 24), sub, font=f[15], fill='#555')
    g.text((30, 56), SC_HINT, font=f[12], fill='#777')

    gy = 20
    for i, gd in enumerate(L['guards']):
        nm = GNAME.get(gd['img'], gd['img'])
        tr = TNAME.get(gd.get('trait',''), '固定扫视') if gd.get('fixed') else TNAME.get(gd.get('trait',''), '普通巡逻')
        g.text((W-360, gy), f'G{i+1} {nm} · {tr} · 视野半径{int(gd["R"]*1.35)}', font=f[13], fill='#333')
        gy += 22
    for j, n in enumerate(L.get('npcs', [])):
        g.text((W-360, gy), f'路人（看到你会喊人）', font=f[13], fill='#888')
        gy += 22

    rx, ry = room_xy(40, 72, ox, oy)
    g.rectangle([rx, ry, rx+880, ry+528], fill='#fbfaf5', outline='#000', width=3)
    for gx in range(140, 921, 100):
        a = room_xy(gx, 72, ox, oy)
        g.line([a, room_xy(gx, 600, ox, oy)], fill='#d8d5c8', width=1)
        g.text((a[0]-14, ry-24), str(gx), font=f[12], fill='#999')
    for gy2 in range(172, 601, 100):
        a = room_xy(40, gy2, ox, oy)
        g.line([room_xy(40, gy2, ox, oy), room_xy(920, gy2, ox, oy)], fill='#d8d5c8', width=1)
        g.text((rx-46, a[1]-7), str(gy2), font=f[12], fill='#999')

    def X(x): return ox + (x - 40)
    def Y(y): return oy + (y - 72)

    for s in L.get('shadows', []):
        x0, y0, w, h = X(s[0]), Y(s[1]), s[2], s[3]
        g.rectangle([x0, y0, x0+w, y0+h], outline='#000', width=2)
        for i in range(-int(h), int(w), 14):
            g.line([x0+max(0,i), y0+min(h, i+h), x0+min(w, i+h), y0+max(0, i)], fill='#000', width=1)
        g.text((x0+6, y0+4), '暗影·藏身', font=f[13], fill='#fff')

    for gx, gy, gr in L.get('glows', []):
        c = (X(gx), Y(gy))
        g.ellipse([c[0]-gr, c[1]-gr*0.75, c[0]+gr, c[1]+gr*0.75], outline='#000', width=2)
        g.text((c[0]-34, c[1]-gr*0.75-16), '亮处·暴露', font=f[13], fill='#000')

    for fx, fy, fw, fh, kind in L.get('furniture', []):
        a = (X(fx), Y(fy))
        g.rectangle([a[0], a[1], a[0]+fw, a[1]+fh], fill='#555', outline='#000', width=2)
        g.text((a[0]+5, a[1]+4), FNAME.get(kind, kind), font=f[13], fill='#fff')

    for n in L.get('npcs', []):
        b = n['box']
        a = (X(b[0]), Y(b[1]))
        g.rectangle([a[0], a[1], a[0]+b[2], a[1]+b[3]], outline='#999', width=1)
        for i in range(0, int(b[2]), 18):
            g.line([a[0]+i, a[1], a[0]+i, a[1]+b[3]], fill='#ddd', width=1)
        g.text((a[0]+4, a[1]+3), '路人活动区', font=f[12], fill='#777')
        c = (X(n['x']), Y(n['y']))
        g.ellipse([c[0]-7, c[1]-7, c[0]+7, c[1]+7], fill='#999')
        g.text((c[0]+9, c[1]-7), '路人', font=f[12], fill='#777')

    for lp in L.get('lamps', []):
        c = (X(lp['x']), Y(lp['y']))
        g.ellipse([c[0]-260, c[1]-195, c[0]+260, c[1]+195], outline='#aaa', width=1)
        g.text((c[0]-28, c[1]-215), '台灯·照亮', font=f[12], fill='#888')

    for gd in L.get('gadgets', []):
        c = (X(gd['x']), Y(gd['y']))
        g.rectangle([c[0]-10, c[1]-10, c[0]+10, c[1]+10], fill='#000')
        g.text((c[0]+13, c[1]-9), '唱机·声东击西', font=f[13], fill='#000')

    TS = {'coin':'金币¥30','gem':'宝石¥50','vase':'花瓶¥40','crown':'王冠¥100','pic':'名画¥80'}
    for t in L['treasures']:
        c = (X(t['x']), Y(t['y']))
        g.polygon([(c[0], c[1]-9), (c[0]+9, c[1]), (c[0], c[1]+9), (c[0]-9, c[1])], fill='#000')
        g.text((c[0]+11, c[1]-8), TS.get(t['type'],'?'), font=f[13], fill='#000')

    if L.get('keyAt'):
        c = (X(L['keyAt']['x']), Y(L['keyAt']['y']))
        g.ellipse([c[0]-9, c[1]-9, c[0]+3, c[1]+3], outline='#000', width=3)
        g.line([c[0]+3, c[1]-3, c[0]+14, c[1]+8], fill='#000', width=3)
        g.text((c[0]+16, c[1]+2), '万能钥匙', font=f[13], fill='#000')

    for gt in L.get('gates', []):
        a = (X(gt['x']), Y(gt['y']))
        g.rectangle([a[0], a[1], a[0]+gt['w'], a[1]+gt['h']], fill='#000')
        g.text((a[0]+gt['w']/2-52, a[1]+gt['h']+6), '栅门(需万能钥匙)', font=f[13], fill='#000')

    for i, gd in enumerate(L['guards']):
        R = gd['R'] * 1.35
        ccol = '#000'
        if gd.get('fixed'):
            c = (X(gd['fixed']['x']), Y(gd['fixed']['y']))
        elif gd.get('roam'):
            c = (X(480), Y(380))
            ccol = '#777'
        else:
            pts = [ (X(px), Y(py)) for px, py in gd['path'] ]
            if len(pts) > 2:
                g.line(pts + [pts[0]], fill=ccol, width=2)
            else:
                g.line(pts, fill=ccol, width=2)
            for j, p in enumerate(pts):
                g.ellipse([p[0]-5, p[1]-5, p[0]+5, p[1]+5], fill='#000')
                g.text((p[0]+6, p[1]-18), str((j % len(gd['path']))+1), font=f[13], fill='#000')
            c = pts[0]
        r = R
        for k in range(0, 360, 8):
            a0 = k * 3.14159 / 180
            a1 = (k + 4) * 3.14159 / 180
            g.arc([c[0]-r, c[1]-r*0.75, c[0]+r, c[1]+r*0.75], a0*57.3, a1*57.3, fill=ccol, width=2)
        g.rectangle([c[0]-12, c[1]-12, c[0]+12, c[1]+12], fill='#000')
        g.text((c[0]+16, c[1]-22), f'G{i+1}', font=f[15], fill='#000')

    sp = (X(L['start']['x']), Y(L['start']['y']))
    g.polygon([(sp[0], sp[1]-13), (sp[0]+11, sp[1]+9), (sp[0]-11, sp[1]+9)], fill='#000')
    g.text((sp[0]+14, sp[1]+2), '出生点', font=f[15], fill='#000')
    e = L['exit']
    ea = (X(e['x']+e['w']/2), Y(584))
    g.rectangle([ea[0]-40, ea[1]-14, ea[0]+40, ea[1]+8], fill='#000')
    g.text((ea[0]-16, ea[1]+12), 'EXIT 出口', font=f[15], fill='#000')

    ly = H - 96
    g.rectangle([20, ly-14, W-20, H-16], outline='#000', width=1)
    g.text((30, ly-8), '墙体(碰撞+挡视线)', font=f[13], fill='#000')
    g.rectangle([30+150, ly-8, 30+172, ly+6], fill='#555'); g.text((30+178, ly-8), '家具(碰撞)', font=f[13], fill='#000')
    g.rectangle([30+270, ly-7, 30+292, ly+5], outline='#000', width=2); g.text((30+298, ly-8), '暗影·藏身', font=f[13], fill='#000')
    g.ellipse([30+390, ly-8, 30+412, ly+6], outline='#000', width=2); g.text((30+418, ly-8), '亮处·暴露', font=f[13], fill='#000')
    g.arc([30+500, ly-9, 30+520, ly+7], 0, 360, fill='#000', width=2); g.text((30+526, ly-8), '守卫视野(虚线圈)', font=f[13], fill='#000')
    g.text((30+680, ly-8), '虚线框=路人区 数字=巡逻点', font=f[13], fill='#000')
    g.text((30, ly+22), '◆宝物   ▲出生点   ■出口   ■栅门(需万能钥匙)   ○台灯(照亮)   ■唱机(声东击西)   ★守卫编号', font=f[13], fill='#000')

    return img

try:
    data = extract_levels()
except Exception as e:
    print('提取失败:', e); sys.exit(1)

SC = data['SC']
print('SC =', SC, '| 关卡数 =', len(data['LEVELS']))

imgs = []
for i, L in enumerate(data['LEVELS']):
    safe = re.sub(r'[ ·]', '', L['name']).replace('·','')
    fn = os.path.join(OUT, f'L{i+1}-{safe}.png')
    img = render_level(L, i, len(data['LEVELS']))
    img.save(fn)
    imgs.append((fn, img))
    print('生成', fn)

# 总览拼图
total_h = sum(im.height for _, im in imgs)
sheet = Image.new('RGB', (imgs[0][1].width, total_h), '#ffffff')
y = 0
for _, im in imgs:
    sheet.paste(im, (0, y)); y += im.height
sheet.save(os.path.join(OUT, '全部地图总览.png'))
print('生成 总览拼图')
