#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""出游攻略验收清单自动检查（只读，不改任何文件，不上网）。

用法：python3 出游攻略检查.py <样稿 html 路径> [--技能目录 目录] [--截图目录 目录] [--词表 文件] [--推文 文件] [--报告 文件]
有「不通过」时退出码为 1，全部通过或只剩「需人看」时为 0。

隐私词表：在本程序同目录放一个「隐私词表.txt」（或用 --词表 指定），一行一个词，
写你家人的称呼、你的籍贯、小区名、常用药名等。这个文件只留在本机，不要提交。
没有词表时，隐私词这几项显示「需人看」，程序照常运行。
"""
import argparse, hashlib, html as H, os, re, struct, sys, time

开始 = time.time()
本目录 = os.path.dirname(os.path.abspath(__file__))
默认技能目录 = os.path.dirname(本目录)
默认词表 = os.path.join(本目录, '隐私词表.txt')

色板 = {'#f7f5fb', '#ffffff', '#1f1f1f', '#6b5ce7', '#e6b84d', '#e8e2f8', '#ddd5f2',
        '#6a6385', '#fff6dd', '#f3f0fc', '#fbf3dc'}
命名色 = ('white black red green blue pink orange yellow purple violet gray grey silver lime olive teal '
          'navy maroon aqua fuchsia brown gold tan beige coral salmon crimson indigo khaki ivory '
          'lavender magenta cyan transparent currentcolor').split()
起点词 = ['从家', '总里程', '全程', '合计']
禁用词 = ['待' + '核实', '待查实', '可能是', '你给的', '查不到', '原因是', '改动记录', '到家', '回家', '在家']

def 读词表(p):
    """一行一个词，# 开头的行和空行跳过；文件不存在返回 None。"""
    try:
        with open(p, encoding='utf-8') as f:
            return [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
    except OSError: return None
繁体字 = set('們這個來時從會說對過還發後點車開門問樣種現為與將進電話裡裏體們價錢買賣東氣讓'
             '經濟動區場館間廣號長歡寫圖風雲陽鐘頭臉飯麵燒雞魚湯總覽無認識請應該當禮學檢驗單據'
             '條處邊際實質')

結果 = []  # (编号, 状态, 证据)
def 记(编号, 状态, 证据):
    結果.append((编号, 状态, 证据))
def 判(编号, 条件, 好, 坏):
    记(编号, '通过' if 条件 else '不通过', 好 if 条件 else 坏)
def 人看(编号, 谁, 说明):
    记(编号, '需人看', f'{说明}，请{谁}看。')

def 读(p):
    try:
        with open(p, encoding='utf-8') as f: return f.read()
    except OSError: return None

def 行号(文本, 词, 最多=5):
    号 = [str(i) for i, l in enumerate(文本.splitlines(), 1) if 词 in l]
    return '、'.join(号[:最多]) + ('…' if len(号) > 最多 else '')

def 宽度(png):
    try:
        with open(png, 'rb') as f: 头 = f.read(24)
        if 头[:8] != b'\x89PNG\r\n\x1a\n': return None
        return struct.unpack('>I', 头[16:20])[0]
    except OSError: return None

def 纯文本(片段):
    return H.unescape(re.sub(r'<[^>]+>', '', 片段))

def 加权字数(s):
    链 = re.findall(r'https?://\S+', s)
    s = re.sub(r'https?://\S+', '', s)
    return sum(2 if ord(c) >= 0x2E80 else 1 for c in s) + 23 * len(链)

def 第九节(t):
    m = re.search(r'^## 9\..*?(?=^## 10\.)', t, re.S | re.M)
    return m.group(0) if m else None

def main():
    ap = argparse.ArgumentParser(description='出游攻略验收清单自动检查', add_help=False,
        usage='python3 出游攻略检查.py <样稿 html 路径> [--技能目录 目录] [--截图目录 目录] [--词表 文件] [--推文 文件] [--报告 文件]')
    ap._positionals.title = '必填参数'; ap._optionals.title = '可选参数'
    ap.add_argument('-h', '--帮助', action='help', help='显示这段说明')
    ap.add_argument('html', help='样稿 html 路径')
    ap.add_argument('--技能目录', default=默认技能目录, help='SKILL.md 所在目录')
    ap.add_argument('--截图目录', default=None, help='手机截图所在目录，默认是样稿同目录')
    ap.add_argument('--词表', default=默认词表, help='隐私词表路径，一行一个词，默认是程序同目录的 隐私词表.txt')
    ap.add_argument('--推文', default=None, help='推文定稿 md 路径（可选，不给就跳过 T 项）')
    ap.add_argument('--报告', default=None, help='报告输出路径（可选，不给就只打印不写文件）')
    a = ap.parse_args()

    src = 读(a.html)
    if src is None:
        print(f'读不到样稿：{a.html}'); sys.exit(2)
    改版目录 = os.path.dirname(os.path.abspath(a.html))
    版本 = os.path.splitext(os.path.basename(a.html))[0]
    隐私词 = 读词表(a.词表)
    def 词表缺(编号): 人看(编号, '你自己', f'没找到隐私词表（{os.path.basename(a.词表)}），隐私词这一项跳过；照 隐私词表.示例.txt 建一份就能自动查')
    无图 = re.sub(r'base64,[A-Za-z0-9+/=]+', 'base64,…', src)
    样式 = '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', 无图, re.S | re.I))
    正文 = re.sub(r'<style.*?</style>', '', 无图, flags=re.S | re.I)
    body = 正文.split('<body', 1)[-1]
    文字 = 纯文本(body)
    文字行 = 纯文本(无图)  # 保留行号用

    def 计(词, 文=文字): return 文.count(词)
    def 带行(词): return f'「{词}」{计(词)} 处（第 {行号(无图, 词)} 行）'

    # ---------- H ----------
    外链 = []
    for 名, 式 in [('link 标签', r'<link\b'), ('@import', r'@import'), ('@font-face', r'@font-face'),
                  ('url()', r'url\('), ('外链图片', r'<img[^>]+src\s*=\s*["\']?(?!["\']|data:)')]:
        n = len(re.findall(式, 无图, re.I))
        if n: 外链.append(f'{名} {n} 处')
    判('H1', not 外链, '没有 link、@import、@font-face、url()，图片都是内嵌，单文件能离线打开。',
       '有外部资源：' + '，'.join(外链) + '。')
    图目录 = a.截图目录 or 改版目录
    try: 所有图 = sorted(f for f in os.listdir(图目录) if f.lower().endswith('.png'))
    except OSError: 所有图 = []
    宽 = {}
    for w in (375, 640):
        候选 = [f for f in 所有图 if str(w) in f]
        宽[w] = 宽度(os.path.join(图目录, 候选[0])) if 候选 else None
    if 宽[375] == 750 and 宽[640] == 1280:
        判('H2', True, '375 和 640 两张截图都在，宽 750 和 1280。', '')
    elif 宽[375] == 750:
        人看('H2', '你自己', '375 那张截图在、宽 750；没找到 640 那张，宽屏请自己开浏览器看一眼')
    else:
        判('H2', False, '', f'没找到宽 750 的 375 截图（375 那张宽 {宽[375]}，640 那张宽 {宽[640]}）。')

    # ---------- A ----------
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S)
    h1t = 纯文本(h1.group(1)) if h1 else ''
    判('A1', bool(re.search(r'\d{1,2}:\d{2}', h1t)) and '去' in h1t,
       f'大标题是「{h1t}」，有出发时刻也有去哪。', f'大标题缺时刻或地点：「{h1t or "没有 h1"}」。')
    站 = re.findall(r'<li[^>]*>.*?</li>', (re.search(r'<ol class="route">(.*?)</ol>', body, re.S) or re.match('', '')).group(1) or '', re.S) if 'class="route"' in body else []
    店卡 = re.findall(r'<section class="card shop">(.*?)</section>', body, re.S)
    缺图标站 = sum(1 for s in 站 if 'class="sico"' not in s)
    缺图标卡 = sum(1 for c in 店卡 if not re.search(r'<h3><span class="ico"', c))
    判('A2', 站 and not 缺图标站 and not 缺图标卡, f'时间轴 {len(站)} 站、店卡 {len(店卡)} 张都有小图标。',
       f'时间轴 {len(站)} 站里 {缺图标站} 站没图标，店卡里 {缺图标卡} 张没图标。')
    节 = re.findall(r'<section[^>]*>(.*?)</section>', body, re.S)
    首块 = 纯文本(节[0]) if 节 else ''
    判('A3', '天气' in 首块[:40], '大标题下第一块就是天气卡。', '大标题下第一块不是天气卡。')
    问题 = []; 豁免 = []
    for c in 店卡:
        名 = 纯文本(re.search(r'<h3>(.*?)</h3>', c, re.S).group(1)).strip()
        if '公园' in 名: 豁免.append(名); continue
        li = re.findall(r'<li>(.*?)</li>', (re.search(r'<ol class="top3">(.*?)</ol>', c, re.S) or re.match('', '')).group(1) or '', re.S) if 'top3' in c else []
        if '大家最推荐' not in c: 问题.append(f'{名}没有「大家最推荐」')
        elif len(li) != 3: 问题.append(f'{名}推荐 {len(li)} 项，不是 3 项')
        elif any('class="who' not in x for x in li): 问题.append(f'{名}有推荐项没带标签')
    判('A4', not 问题, f'{len(店卡) - len(豁免)} 张餐饮店卡都有「大家最推荐」三项，每项带标签；'
       f'{"、".join(豁免)}是公园，不算餐饮店卡，豁免。', '；'.join(问题) + '。')
    出门 = re.search(r'出门前看一眼', body)
    bye = re.search(r'<p class="bye">(.*?)</p>', body, re.S)
    判('A5', bool(出门 and bye and 纯文本(bye.group(1)).strip()),
       f'有「出门前看一眼」清单，收尾一句是「{纯文本(bye.group(1)).strip() if bye else ""}」。',
       '缺「出门前看一眼」清单或收尾一句。')
    缺 = [x for x in ['【大人 1】', '【大人 2】', '【孩子】'] if x not in 文字]
    判('A6', not 缺 and all(f'who t{i}' in body for i in (1, 2, 3)),
       f'【大人 1】{计("【大人 1】")} 处、【大人 2】{计("【大人 2】")} 处、【孩子】{计("【孩子】")} 处，三人各用一个标签样式。',
       f'缺填写位：{"、".join(缺) or "标签样式不全"}。')

    # ---------- B ----------
    缺时 = sum(1 for s in 站 if '<time' not in s)
    缺距 = sum(1 for s in 站[:-1] if not re.search(r'class="dist">[^<]*km[^<]*分', s))
    判('B1', 站 and not 缺时 and not 缺距, f'时间轴 {len(站)} 站都有时间，站间都写了公里和车程。',
       f'{缺时} 站没时间，{缺距} 段没写距离车程。')
    caps = re.findall(r'<figcaption[^>]*>(.*?)</figcaption>', body, re.S)
    imgs = re.findall(r'<img\b[^>]*>', body)
    坏署名 = [纯文本(c)[:20] for c in caps if not re.search(r'示意图：.*（非本[店园]）.*/', 纯文本(c))]
    娄 = next((c for c in caps if 'Loujiang' in c), '')
    娄好 = '《Loujiang River, Kunshan》' in 娄 and 'creativecommons.org/licenses/by/3.0' in 娄 and '（已裁剪）' in 娄
    判('B2', len(caps) == len(imgs) and not 坏署名 and 娄好,
       f'{len(imgs)} 张图都有「示意图：…（非本店/非本园）」加作者和协议；娄江那张有作品标题、CC BY 3.0 协议链接和（已裁剪）。',
       f'图 {len(imgs)} 张、署名 {len(caps)} 条；格式不对的：{"、".join(坏署名) or "无"}；娄江署名{"齐全" if 娄好 else "不全"}。')
    判('B3', '万一有变' in 文字, f'有「万一有变」（第 {行号(无图, "万一有变")} 行）。', '没有「万一有变」。')
    判('B4', '出门前打个电话' in 文字, f'有「出门前打个电话」（第 {行号(无图, "出门前打个电话")} 行）。', '没有「出门前打个电话」。')
    链 = re.findall(r'href="https?://', body)
    判('B5', len(链) > 0, f'正文共有 {len(链)} 个来源链接。', '没有来源链接。')

    # ---------- P ----------
    if 隐私词 is None: 词表缺('P1')
    else:
        命中 = {w: len(re.findall(r'(?<![A-Za-z])' + re.escape(w) + r'(?![A-Za-z])', 文字)) for w in 隐私词}
        判('P1', not any(命中.values()), f'隐私词表里的 {len(隐私词)} 个词在页面上都是 0 处（词表外的人名请人顺带过目）。',
           '有隐私词：' + '，'.join(f'{k} {v} 处（第 {行号(无图, k)} 行）' for k, v in 命中.items() if v) + '。')
    起 = {w: 计(w) for w in 起点词}
    判('P2', '【出发地】' in 文字 and not any(起.values()), f'起点写【出发地】（{计("【出发地】")} 处），从家、总里程、全程、合计都是 0。',
       '；'.join(带行(w) for w, n in 起.items() if n) or '没有【出发地】' + '。')
    判('P3', '随身药品：【自行填写】' in 文字, f'有「随身药品：【自行填写】」（第 {行号(无图, "随身药品")} 行），药名不写在页面上（由 P1 的隐私词表查）。',
       '随身药品占位缺失。')

    # ---------- C ----------
    非卡底 = re.sub(r'<p class="foot">.*?</p>', '', body, flags=re.S)
    标注 = re.findall(r'[（(]\s*\d{1,2}/\d{1,2}\s*查\s*[）)]', 纯文本(非卡底))
    判('C1', not 标注, '正文行末没有「（10/18 查）」这类标注。', f'正文有 {len(标注)} 处行末查证标注。')
    长句 = re.findall(r'查不到[^。]*原因是[^。]*。?', 文字)
    判('C2', not 长句 and 计('查不到') == 0, '「查不到」「原因是」都是 0 处。',
       f'有长句「{长句[0] if 长句 else ""}」，查不到 {计("查不到")} 处（第 {行号(无图, "查不到")} 行）。')
    缺底 = [纯文本(re.search(r'<h3>(.*?)</h3>', c, re.S).group(1)).strip() for c in 店卡
            if not re.search(r'<p class="foot">[^<]*\d{1,2}/\d{1,2}', c)]
    判('C3', not 缺底, f'{len(店卡)} 张卡底部都有带日期的来源小字。', f'缺卡底日期小字：{"、".join(缺底)}。')
    禁 = {w: 计(w) for w in 禁用词}
    判('C4', not any(禁.values()), '「待查实」这类说法、可能是、你给的、查不到、原因是、改动记录、到家、回家、在家都是 0 处。',
       '；'.join(带行(w) for w, n in 禁.items() if n) + '。')

    # ---------- V ----------
    色 = set(c.lower() for c in re.findall(r'#[0-9a-fA-F]{3,8}\b', 样式 + 正文))
    色 = {('#' + ''.join(x * 2 for x in c[1:])) if len(c) == 4 else c for c in 色}
    外色 = sorted(色 - 色板)
    函数色 = re.findall(r'\b(?:rgba?|hsla?)\s*\(', 样式 + 正文, re.I)
    名色 = sorted(set(re.findall(r'(?<![\w-])(' + '|'.join(命名色) + r')(?![\w-])', 样式, re.I)))
    名色 = [x for x in 名色]
    判('V1', not 外色 and not 函数色 and not 名色, f'只用了色板里的 {len(色)} 种颜色，色板外 0 种，rgb/rgba/hsl 0 处，命名色 0 处。',
       f'色板外颜色 {len(外色)} 种（{"、".join(外色)}），rgb/hsl {len(函数色)} 处，命名色 {"、".join(名色) or "0 处"}。')
    判('V2', not 外色 and not 函数色 and not 名色, '颜色全在色板里，所以没有橙色、粉色、绿色。', '有色板外颜色，见 V1。')
    脚 = len(re.findall(r'<script', 无图, re.I)); js = len(re.findall(r'javascript:', 无图, re.I))
    on = len(re.findall(r'<[^>]+\s on[a-z]+\s*=', 无图.replace('\n', ' '), re.I)) + len(re.findall(r'<[^>]+\son[a-z]+\s*=', 无图, re.I))
    判('V3', not (脚 or js or on), 'script 0 个，javascript: 0 处，on* 属性 0 个。', f'script {脚} 个，javascript: {js} 处，on* 属性 {on} 个。')
    非内嵌 = [i for i in imgs if 'src="data:image' not in i]
    缺alt = [i for i in imgs if not re.search(r'alt="[^"]+"', i)]
    判('V4', not 外链 and not 非内嵌 and not 缺alt, f'{len(imgs)} 张图都是 base64 内嵌，每张都有非空 alt，没有外链字体或 CSS。',
       f'不是内嵌的图 {len(非内嵌)} 张，缺 alt 的 {len(缺alt)} 张，外部资源：{"，".join(外链) or "无"}。')
    人看('V5', '你自己', f'截图里有没有切字、横向溢出、版面好不好看，程序判断不了（截图宽 {宽[375]} 和 {宽[640]}）')

    # ---------- S ----------
    sd = a.技能目录
    sk, rd = (读(os.path.join(sd, f)) or '' for f in ('SKILL.md', 'README.md'))
    n1 = 第九节(sk)
    分版 = [w for w in ('家用版', '公开版') if n1 and w in n1]
    判('S2', n1 is not None and '唯一' in n1 and not 分版,
       f'SKILL.md 第 9 节（{len((n1 or "").splitlines())} 行）写明唯一固定版式。',
       f'SKILL.md 第 9 节{"找不到" if n1 is None else "没写唯一版式"}，或还分{"、".join(分版)}。')
    s3 = '每次交付物是一份单文件 HTML' in sk and 'v4 合并版式' in sk and re.search(r'截图[^。\n]{0,60}只用来', sk)
    判('S3', bool(s3), 'SKILL.md 写了「每次交付物是一份单文件 HTML，用 v4 合并版式」，截图只用来验收。',
       'SKILL.md 缺「每次交付物是一份单文件 HTML」「v4 合并版式」或「截图只用来」。')
    先填 = re.search(r'^## 用之前先填.*?(?=^## )', sk, re.S | re.M)
    要项 = ['几个人', '称呼', '口味', '月龄', '随身药品', '出发地']
    缺项 = [w for w in 要项 if not 先填 or w not in 先填.group(0)]
    判('S4', bool(先填) and not 缺项, 'SKILL.md 有「用之前先填」，人数、称呼、口味、月龄、随身药品、出发地都在。',
       f'「用之前先填」缺：{"、".join(缺项) or "整节"}。')
    判('S5', all('不进公开仓库' in x for x in (sk, rd)), 'SKILL.md、README.md 都写了「不进公开仓库」。', '有文件没写「不进公开仓库」。')
    旧说法 = ['.md 加 .html', 'md 加 html', 'md 和 html 各一份', '.md 和 .html', '和同名 `.html`', '各一份', '改动记在文末', '记在文末', '文末']
    s6 = [f'{名} 第 {行号(x, w)} 行「{w}」' for 名, x in (('SKILL.md', sk), ('README.md', rd))
          for w in 旧说法 if w in x]
    判('S6', not s6, '两份文件里「.md 加 .html 各一份」「改动记在文末」这类旧说法都是 0 处。（整体有没有别的矛盾，可再通读一遍。）',
       '还有和第 9.5 节冲突的旧说法：' + '；'.join(s6) + '。')
    if 隐私词 is None: 词表缺('S7')
    else:
        s7 = [f'{名}「{w}」第 {行号(x, w)} 行' for 名, x in (('SKILL.md', sk), ('README.md', rd))
              for w in 隐私词 if w in x]
        判('S7', not s7, f'SKILL.md、README.md 里隐私词表的 {len(隐私词)} 个词都是 0 处。', '有私人信息：' + '；'.join(s7) + '。')

    # ---------- T（可选：给了 --推文 才查）----------
    tw = 读(a.推文) if a.推文 else None
    if tw is None:
        人看('T1', '你自己', '没给 --推文 或读不到推文文件，推文几项跳过')
    else:
        块 = re.search(r'```[^\n]*\n(.*?)```', tw, re.S)
        推 = 块.group(1).strip() if 块 else ''
        判('T1', bool(推), '推文文件里找到了代码块正文。', '推文文件里没找到 ``` 包起来的正文。')
        敏 = [w for w in ['公司', '老板', '同事', '上班', '政治', '政府', '旧号'] if w in 推]
        人看('T2', '你自己', f'政治、工作和旧号要看语境；关键词初筛命中 {len(敏)} 个（{"、".join(敏) or "无"}）')
        隐 = [w for w in ['学校', '幼儿园', '小区', '定位', '照片'] if w in 推]
        人看('T3', '你自己', f'孩子露不露脸要看配图；正文关键词初筛命中 {len(隐)} 个（{"、".join(隐) or "无"}）')
        判('T4', '链接占位' in 推 and '公开后补链接' in 推, '正文有「【链接占位：公开后补链接】」。', '正文缺「链接占位」或「公开后补链接」。')
        w = 加权字数(推)
        判('T5', 推 and w <= 280, f'正文加权 {w} 个字符，不超过 280。', f'正文加权 {w} 个字符，超过 280（或没找到正文）。')

    # ---------- F ----------
    查文件 = {'样稿正文': 文字, 'SKILL.md': sk, 'README.md': rd}
    if tw: 查文件['推文'] = tw
    繁 = {k: sorted(set(c for c in v if c in 繁体字)) for k, v in 查文件.items()}
    繁 = {k: v for k, v in 繁.items() if v}
    判('F5', not 繁, f'{len(查文件)} 份文件里没有常见繁体字。（英文只该出现在店名、协议名和网址里，可抽看。）',
       '有繁体字：' + '；'.join(f'{k}：{"".join(v)}' for k, v in 繁.items()) + '。')

    # ---------- 输出 ----------
    计数 = {s: sum(1 for r in 結果 if r[1] == s) for s in ('通过', '不通过', '需人看')}
    耗时 = time.time() - 开始
    总结 = (f'{版本} 共 {len(結果)} 条：通过 {计数["通过"]} 条，不通过 {计数["不通过"]} 条，需人看 {计数["需人看"]} 条；'
          + ('有不通过的，先改再交。' if 计数['不通过'] else '机器能查的都过了，剩下的请人看。') + f'用时 {耗时:.2f} 秒。')
    for 编号, 状态, 证据 in 結果:
        print(f'{编号}　{状态}　{证据}')
    print(总结)
    if a.报告:
        行 = [f'# {版本} 程序检查结果', '', f'检查对象：{os.path.basename(a.html)}',
              f'检查时间：{time.strftime("%Y-%m-%d %H:%M")}', '',
              '说明：A4 里公园不算餐饮店卡，按此豁免。「需人看」写明了该由谁看。', '',
              '| 编号 | 结论 | 证据 |', '|---|---|---|']
        行 += [f'| {a_} | {b} | {c.replace("|", "／")} |' for a_, b, c in 結果]
        行 += ['', '## 总结', '', 总结, '']
        with open(a.报告, 'w', encoding='utf-8') as f: f.write('\n'.join(行))
        print(f'报告已写到：{a.报告}')
    sys.exit(1 if 计数['不通过'] else 0)

if __name__ == '__main__':
    main()
