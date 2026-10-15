#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CC-ZH linter -- jian ming zhong shou kong xie zuo gui fan de ji xie chu shai.

零依赖, Python 3.9+.
档位: --level 100(严谨档) | 80(标准档, 默认) | 60(80% 档)

只查能机械判定的规则: C10 黑名单与句式、B5 句长、B7 的链、B8 虚化动词、
段首 emoji、配额超标。零违规不等于好文章, 判断在人。

豁免:
- 代码块(``` 围栏)不查
- 「❌」「反例」「改写前」「不批准」开头的行不查(示例本身是坏文本)
- 表格行不查
- <!-- cczh:off --> 到 <!-- cczh:on --> 之间不查
"""

import argparse
import json
import re
import sys

CJK_RE = re.compile(r"[\u4e00-\u9fa5]")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[.\-'+%][A-Za-z0-9]+)*")
SENT_SPLIT = re.compile(r"(?<=[\u3002\uff01\uff1f!?])")
NON_WS = re.compile(r"\s+")
PREFIX = re.compile(r"^(?:>|[-*+]|\d+\.)\s*")
MARK = re.compile(r"^<!--\s*cczh:(off|on)\s*-->$")

# B7: 连续三层定语的「的」链
FRAG_SPLIT = re.compile(r"[,\uff0c\u3001;\uff1a:\uff1b]")
DE_CHAIN = re.compile(
    r"[\u4e00-\u9fa5A-Za-z0-9]{1,12}\u7684"
    r"[\u4e00-\u9fa5A-Za-z0-9]{1,10}\u7684"
    r"[\u4e00-\u9fa5A-Za-z0-9]{1,10}\u7684"
)

# B8: 虚化动词与被动
A1_PAT = re.compile(r"(进行|作出|加以|予以|实施|开展)[\u4e00-\u9fa5]{2}")
BEI_SUO = re.compile(r"被[\u4e00-\u9fa5]{0,6}所")
DEI = re.compile(r"得以[\u4e00-\u9fa5]{1,6}")

C10_WORDS = {
    "值得注意的是": ("套话", "删, 直接说"),
    "值得一提的是": ("套话", "删, 直接说"),
    "众所周知": ("套话", "删"),
    "在当今时代": ("套话", "删"),
    "总体而言": ("套话", "删"),
    "与此同时": ("连接词", "同时"),
    "因此可见": ("连接词", "删, 直接给结论"),
    "由此可见": ("连接词", "删, 直接给结论"),
    "综上所述": ("连接词", "结论放开头, 不放结尾"),
    "总而言之": ("连接词", "结论放开头, 不放结尾"),
    "总的来说": ("连接词", "结论放开头"),
    "不难发现": ("连接词", "删, 直接给证据"),
    "毫无疑问": ("套话", "删, 判断须带证据"),
    "不可否认": ("套话", "删, 判断须带证据"),
    "毋庸置疑": ("套话", "删"),
    "不容置疑": ("套话", "删"),
    "日益": ("套话", "更"),
    "愈发": ("套话", "更"),
    "愈加": ("套话", "更"),
    "存在着": ("套话", "有"),
    "赋能": ("黑话", "帮 / 增强 / 让能做到 X"),
    "抓手": ("黑话", "方法 / 切入点"),
    "沉淀": ("黑话", "积累 / 保存"),
    "颗粒度": ("黑话", "粒度 / 粗细"),
    "底层逻辑": ("黑话", "原理"),
    "顶层设计": ("黑话", "总体规划"),
    "拉齐": ("黑话", "统一"),
    "心智": ("黑话", "印象"),
    "势能": ("黑话", "潜力"),
    "打法": ("黑话", "策略"),
    "组合拳": ("黑话", "一组措施"),
    "护城河": ("黑话", "竞争优势"),
    "降维打击": ("黑话", "碾压 / 说具体做了什么"),
    "飞轮": ("黑话", "正循环"),
    "全链路": ("黑话", "全流程"),
    "深度绑定": ("黑话", "紧密合作"),
    "复盘": ("黑话", "总结"),
    "生态位": ("黑话", "定位"),
    "赋能式": ("空形容词", "说具体做了什么"),
    "对齐": ("黑话", "统一(非技术语境)"),
    "深度的": ("空形容词", "删 / 说具体多深"),
    "全面的": ("空形容词", "删 / 列全了什么"),
    "极致的": ("空形容词", "删 / 给数字"),
    "颠覆性": ("空形容词", "删 / 说具体变了什么"),
    "革命性": ("空形容词", "删 / 说具体变了什么"),
    "有效地": ("空形容词", "删(动词已含)"),
    "成功地": ("空形容词", "删(动词已含)"),
    "顺利地": ("空形容词", "删(动词已含)"),
    "快速地": ("空形容词", "删 / 给数字"),
    "深刻地": ("空形容词", "删"),
    "深入地": ("空形容词", "删 / 详细"),
    "充分地": ("空形容词", "删"),
    "可以说": ("空形容词", "删"),
    "基本上": ("模糊词", "直接写不确定度"),
    "某种程度上": ("模糊词", "直接写不确定度"),
    "一定程度上": ("模糊词", "直接写不确定度"),
    "相对而言": ("模糊词", "删"),
    "某种意义上": ("模糊词", "直接写不确定度"),
}
CLOSE_LOOP = re.compile(r"闭环(?!控制)")

C10_PATS = [
    (re.compile(r"随着[\u4e00-\u9fa5]{0,12}的不断发展"), ("套话", "删")),
    (re.compile(r"不仅仅?[^\u3002\uff0c,;\uff1b!?\uff01\uff1f]{0,20}更是"), ("三段式", "拆成独立判断")),
    (re.compile(r"既[^\u3002\uff0c,]{1,20}又[^\u3002\uff0c,]{1,20}还"), ("三段式", "拆句")),
]

VERY = re.compile(r"(非常|极其|十分|相当(?!于))")
YIZHI = "之一"
FURTHER = "进一步"
PAIBAI = re.compile(r"不仅[^\u3002\uff0c,]{0,30}而且")
EXEMPT = {"\u274c", "\u2705"}  # ❌ ✅ 示例标记, 不算排版污染


def is_emoji(ch):
    o = ord(ch)
    hot = o >= 0x1F000 or 0x2190 <= o <= 0x2BFF or 0xFE00 <= o <= 0xFE0F
    return hot and ch not in EXEMPT


def visual_len(s):
    """B5 数法: 汉字逐字数, 连续英文/数字串各算 1 个字, 标点不计。"""
    n = 0
    i = 0
    while i < len(s):
        if CJK_RE.match(s[i]):
            n += 1
            i += 1
        else:
            m = WORD_RE.match(s, i)
            if m:
                n += 1
                i = m.end()
            else:
                i += 1
    return n


def analyze(lines, level, hard_max, soft_max):
    out = []

    def add(ln, rule, sev, msg):
        out.append({"line": ln, "rule": rule, "severity": sev, "message": msg})

    off = fence = False
    very_n = yizhi_n = further_n = paibai_n = 0
    total = 0

    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if fence:
            if s.startswith("```"):
                fence = False
            continue
        if s.startswith("```"):
            fence = True
            continue
        m = MARK.match(s)
        if m:
            off = m.group(1) == "off"
            continue
        if off:
            continue
        if s.startswith("|"):
            continue
        content = PREFIX.sub("", s).strip()
        if content.startswith(("❌", "反例", "改写前", "不批准")):
            continue

        text = re.sub(r"`[^`\n]*`", "", content)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"[*_#]+", "", text)

        if content and is_emoji(content[0]):
            add(i, "C10", "hard", "排版污染: 段首 emoji")
        if "\u2014\u2014" in content:
            add(i, "C10", "soft", "破折号做解释, 改冒号或拆句")

        for w, (cat, rep) in C10_WORDS.items():
            if w in text:
                add(i, "C10", "hard", f"{cat}「{w}」, 替代: {rep}")
        if CLOSE_LOOP.search(text):
            add(i, "C10", "hard", "黑话「闭环」, 替代: 完整流程(闭环控制除外)")
        for pat, (cat, rep) in C10_PATS:
            mm = pat.search(text)
            if mm:
                add(i, "C10", "hard", f"{cat}「{mm.group(0)}」, {rep}")
        if "首先" in text and "其次" in text:
            add(i, "C10", "soft", "首先/其次连接词, 考虑用列表")

        if level >= 80:
            for m1 in A1_PAT.finditer(text):
                add(i, "B8", "hard", f"虚化动词「{m1.group(0)}」, 直接用动词")
            if BEI_SUO.search(text):
                add(i, "B8", "hard", "「被…所…」, 改主动句")
            if DEI.search(text):
                add(i, "B8", "hard", "「得以…」, 直接写动词")

        for sent in [x for x in SENT_SPLIT.split(text) if x.strip()]:
            n = visual_len(sent)
            if n > hard_max:
                add(i, "B5", "hard", f"句长 {n} 字(B5 数法), 超硬上限 {hard_max}")
            elif level == 100 and n > soft_max:
                add(i, "B5", "soft", f"句长 {n} 字, 严谨档建议不超 {soft_max}")

        if level >= 80:
            for frag in FRAG_SPLIT.split(text):
                if DE_CHAIN.search(frag):
                    add(i, "B7", "hard", "连续 3 层「的」定语, 拆句")
                    break
            if text.count("被") > 1:
                add(i, "B8", "soft", f"一段 {text.count('被')} 个「被」, 上限 1")

        very_n += len(VERY.findall(text))
        yizhi_n += text.count(YIZHI)
        further_n += text.count(FURTHER)
        paibai_n += len(PAIBAI.findall(text))
        total += visual_len(NON_WS.sub("", text))

    if level == 80:
        v_allow = max(2, (total // 500) * 2)
        if very_n > v_allow:
            add(0, "C10", "quota", f"「非常/极其/十分/相当」{very_n} 个, 配额 {v_allow}")
        if yizhi_n > 2:
            add(0, "C10", "quota", f"「之一」{yizhi_n} 个, 配额 2")
        if further_n > 1:
            add(0, "C10", "quota", f"「进一步」{further_n} 个, 配额 1")
        if paibai_n > 1:
            add(0, "C10", "quota", f"排比「不仅…而且…」{paibai_n} 处, 配额 1")
    elif level == 100:
        if very_n:
            add(0, "C10", "hard", f"严谨档零修辞: 程度副词 {very_n} 个")
        if further_n:
            add(0, "C10", "hard", f"严谨档零修辞: 「进一步」{further_n} 个")
        if paibai_n:
            add(0, "C10", "hard", f"严谨档零修辞: 排比 {paibai_n} 处")
        if yizhi_n > 2:
            add(0, "C10", "soft", f"「之一」{yizhi_n} 个, 配额 2")

    return out


def main():
    ap = argparse.ArgumentParser(description="CC-ZH linter: 简明中文机械初筛")
    ap.add_argument("files", nargs="*", help="要检查的文件; 缺省读 stdin")
    ap.add_argument("--level", type=int, default=80, choices=(100, 80, 60),
                    help="100=严谨档 80=标准档(默认) 60=80%%档")
    ap.add_argument("--max-len", type=int, default=40, help="句长硬上限(默认 40)")
    ap.add_argument("--soft-len", type=int, default=30, help="严谨档软上限(默认 30)")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    results = []
    if args.files:
        for path in args.files:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            for r in analyze(lines, args.level, args.max_len, args.soft_len):
                results.append({"file": path, **r})
    else:
        lines = sys.stdin.readlines()
        for r in analyze(lines, args.level, args.max_len, args.soft_len):
            results.append({"file": "<stdin>", **r})

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{r['file']}:{r['line']}: [{r['rule']}][{r['severity']}] {r['message']}")
        hard = sum(1 for r in results if r["severity"] == "hard")
        rest = len(results) - hard
        lv = {100: "严谨档", 80: "标准档", 60: "80% 档"}[args.level]
        print(f"-- 硬违规 {hard} 处, 提示/配额 {rest} 处({lv})")
    sys.exit(1 if any(r["severity"] == "hard" for r in results) else 0)


if __name__ == "__main__":
    main()
