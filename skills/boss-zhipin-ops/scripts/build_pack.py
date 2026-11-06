# 生成面试简历评估包：评估页（打分、SWOT、面试问题）+ 原始简历
# 用法：python build_pack.py <数据文件.py> [姓名 ...]
# 依赖：pip install pymupdf
# 输出目录：环境变量 PACK_OUT（默认 ./packs）；字体目录：环境变量 PACK_FONTS（默认 C:\Windows\Fonts，需含 simhei.ttf）。
# 格式与用法见 ../references/interview-pack.md，样板数据见 cands_example.py。
# 数据文件定义 C = [dict(...), ...]；RUBRIC 不写就用下面这 5 项；
# 另可给每人加：src_pdf（附件 PDF 路径）或 src_imgs（在线简历截图路径列表）。
import html, importlib.util, io, os, sys
import pymupdf as fitz

ROOT = os.environ.get("PACK_OUT", "./packs")
FONTS = os.environ.get("PACK_FONTS", r"C:\Windows\Fonts")
RUBRIC = [("岗位匹配", 25), ("技术/科研深度", 30), ("学习与思维信号", 20), ("学历口径（本科 985/QS100）", 15), ("风险与稳定性", 10)]
e = html.escape

CSS = """
@font-face { font-family: hei; src: url(simhei.ttf); }
* { font-family: hei; }
body { font-size: 9.6pt; color: #1d2433; line-height: 1.45; }
h1 { font-size: 19pt; margin: 0; }
.sub { color: #555555; margin: 2px 0 6px 0; }
.big { font-size: 26pt; font-weight: bold; text-align: right; }
.conf { font-size: 12pt; font-weight: bold; text-align: right; }
table { border-collapse: collapse; width: 100%; margin: 4px 0; }
td, th { border: 1px solid #c9ced8; padding: 3px 5px; vertical-align: top; text-align: left; }
th { background-color: #eef1f6; font-weight: bold; }
td.nb { border: none; padding: 0; }
h2 { font-size: 11.5pt; margin: 9px 0 3px 0; color: #1d2433; }
ul { margin: 1px 0 1px 14px; padding: 0; }
li { margin: 0; }
.flag { background-color: #fff4e5; border: 1px solid #f0b357; padding: 4px 6px; margin: 6px 0; }
.qt { font-weight: bold; margin: 6px 0 0 0; }
.qh { color: #4a5568; font-size: 8.8pt; margin: 1px 0 0 12px; }
.note { color: #666666; font-size: 8pt; margin-top: 8px; }
"""


def body(c, rubric, total, date):
    lst = lambda xs: "<ul>" + "".join(f"<li>{e(x)}</li>" for x in xs) + "</ul>"
    rows = "".join(f"<tr><th width='40%'>{e(n)}</th><td>{s} / {m}</td></tr>" for (n, m), s in zip(rubric, c["scores"]))
    qs = "".join(f"<p class='qt'>Q{i}. {e(q)}</p><p class='qh'>听什么：{e(h)}</p>" for i, (q, h) in enumerate(c["Q"], 1))
    src = "BOSS 附件简历" if c.get("src_pdf") else "BOSS 在线简历截图（未核实）"
    return f"""
<table><tr><td class='nb'><h1>{e(c['name'])}</h1><p class='sub'>{c['age']} 岁 · {e(c['job'])}</p></td>
<td class='nb'><p class='big'>{total} 分</p><p class='conf'>置信度 {c['conf']}%</p></td></tr></table>
<table>
<tr><th width='16%'>面试时间</th><td>北京 {e(c['bj'])} ｜ 你本地 {e(c['la'])} ｜ {e(c['platform'])}</td></tr>
<tr><th>教育</th><td>{e(c['edu'])}</td></tr>
<tr><th>新口径核对</th><td>{e(c['rule'])}</td></tr>
<tr><th>一句话结论</th><td><b>{e(c['verdict'])}</b></td></tr>
<tr><th>置信度说明</th><td>{e(c['conf_why'])}</td></tr>
</table>
<h2>分项打分（满分 100）</h2><table>{rows}<tr><th>合计</th><td><b>{total}</b></td></tr></table>
<div class='flag'><b>要核实的点：</b>{lst(c['flags'])}</div>
<h2>SWOT</h2>
<table><tr><td width='50%'><b>S 优势</b>{lst(c['S'])}</td><td><b>W 劣势</b>{lst(c['W'])}</td></tr>
<tr><td><b>O 机会（对我们）</b>{lst(c['O'])}</td><td><b>T 风险</b>{lst(c['T'])}</td></tr></table>
<h2>面试问题（针对他简历上的具体经历）</h2>{qs}
<p class='note'>置信度 = 我对这个分数反映他真实水平有多大把握，取决于简历内容有多少能被核实、前后是否自洽。评估由 Claude 根据{src}撰写（{date}），后面几页是原始简历。</p>
"""


def build(c, rubric, date):
    total = sum(c["scores"])
    story = fitz.Story(html=body(c, rubric, total, date), user_css=CSS, archive=fitz.Archive(FONTS))
    buf = io.BytesIO()
    w = fitz.DocumentWriter(buf)
    med = fitz.paper_rect("a4")
    more = 1
    while more:
        dev = w.begin_page(med)
        more, _ = story.place(med + (36, 36, -36, -36))
        story.draw(dev)
        w.end_page()
    w.close()
    doc = fitz.open("pdf", buf.getvalue())
    n_eval = doc.page_count
    if c.get("src_pdf"):
        doc.insert_pdf(fitz.open(c["src_pdf"]))
    for img in c.get("src_imgs", []):
        pix = fitz.Pixmap(img)
        page = doc.new_page(width=pix.width * 0.6, height=pix.height * 0.6)
        page.insert_image(page.rect, filename=img)
    os.makedirs(ROOT, exist_ok=True)
    dst = os.path.join(ROOT, f"{c['name']}_{total}分.pdf")
    doc.save(dst, garbage=3, deflate=True)
    return c["name"], total, c["conf"], n_eval, doc.page_count, dst


if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location("cands", sys.argv[1])
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    only = set(sys.argv[2:])
    for c in m.C:
        if only and c["name"] not in only:
            continue
        rubric = getattr(m, "RUBRIC", RUBRIC)
        assert len(c["scores"]) == len(rubric), c["name"]
        print(*build(c, rubric, getattr(m, "DATE", "")))
