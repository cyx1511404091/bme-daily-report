# -*- coding: utf-8 -*-
"""
生物医学工程 (BME) 每日前沿研究推送 — 中文版
仅推送当日最新论文，自动翻译标题并提炼核心亮点
"""
import json, os, re, smtplib, time, urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime, date, timedelta


# ===== 配置 =====
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 587
SMTP_USER = "1511404091@qq.com"
SMTP_PASSWORD = "iwzwcypzvwcnjgeg"
TO_EMAIL = "A1980123qwe@outlook.com"

# BME子领域 — 搜索词优化为最近日期
TOPICS = {
    "🧬 生物材料": "biomaterials OR bioactive material OR scaffold OR hydrogel",
    "🖥️ 医学影像与AI": "deep learning medical imaging OR AI radiology OR computer-aided diagnosis OR medical image segmentation",
    "🧫 组织工程与再生医学": "tissue engineering OR organoid OR 3D bioprinting OR stem cell therapy OR regenerative medicine",
    "🧠 神经工程与脑机接口": "brain-computer interface OR neural engineering OR neuroprosthetic OR neural recording OR neuromodulation",
    "💊 纳米医���与药物递送": "nanomedicine OR nanoparticle drug delivery OR lipid nanoparticle OR mRNA delivery OR targeted therapy",
    "📟 生物传感器与可穿戴": "biosensor OR wearable health monitor OR point-of-care diagnostics OR lab-on-a-chip OR continuous glucose monitor",
    "✂️ 基因编辑与合成生物学": "CRISPR gene editing OR base editing OR prime editing OR synthetic biology OR gene therapy clinical",
    "🤖 AI+药物发现": "AI drug discovery OR AlphaFold protein design OR machine learning drug screening OR computational drug repurposing",
}

TOP_JOURNALS = [
    "Nature Biomedical Engineering", "Nature Biotechnology", "Nature Medicine",
    "Science Translational Medicine", "Cell", "Nature", "Science",
    "Advanced Materials", "ACS Nano", "Biomaterials",
    "IEEE Trans", "Medical Image Analysis", "Lab on a Chip",
    "Nature Communications", "PNAS", "Lancet", "NEJM", "JAMA",
    "Advanced Functional Materials", "Nano Letters",
]

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bme_cache.json")

# 医学领域常见术语对照表（用于简单翻译辅助）
TERM_DICT = {
    "biomaterial": "生物材料", "hydrogel": "水凝胶", "scaffold": "支架",
    "nanoparticle": "纳米颗粒", "drug delivery": "药物递送", "gene therapy": "基因治疗",
    "CRISPR": "CRISPR基因编辑", "organoid": "类器官", "stem cell": "干细胞",
    "deep learning": "深度学习", "neural network": "神经网络", "imaging": "成像",
    "biosensor": "生物传感器", "wearable": "可穿戴", "microfluidic": "微流控",
    "immunotherapy": "免疫治疗", "cancer": "癌症", "tumor": "肿瘤",
    "regeneration": "再生", "wound healing": "伤口愈合", "inflammation": "炎症",
    "brain": "大脑", "neural": "神经", "cardiac": "心脏", "liver": "肝脏",
    "lung": "肺", "kidney": "肾脏", "bone": "骨", "cartilage": "软骨",
    "blood": "血液", "vascular": "血管", "muscle": "肌肉", "skin": "皮肤",
    "diabetes": "糖尿病", "Alzheimer": "阿尔茨海默", "Parkinson": "帕金森",
    "bioprinting": "生物3D打印", "exosome": "外泌体", "extracellular vesicle": "细胞外囊泡",
    "single-cell": "单细胞", "multi-omics": "多组学", "metabolomics": "代谢组学",
    "proteomics": "蛋白质组学", "genomics": "基因组学", "transcriptomics": "转录组学",
    "machine learning": "机器学习", "artificial intelligence": "人工智能",
    "synthetic biology": "合成生物学", "metabolic engineering": "代谢工程",
    "antibody": "抗体", "vaccine": "疫苗", "peptide": "多肽", "protein": "蛋白质",
    "DNA": "DNA", "RNA": "RNA", "lipid": "脂质", "polymer": "聚合物",
    "silk": "丝素蛋白", "collagen": "胶原蛋白", "gelatin": "明胶",
    "in vivo": "体内", "in vitro": "体外", "clinical trial": "临床试验",
}


def simple_translate(text):
    """简单的中英混合翻译，替换常见术语"""
    result = text
    for en, zh in sorted(TERM_DICT.items(), key=lambda x: -len(x[0])):
        pattern = re.compile(re.escape(en), re.IGNORECASE)
        result = pattern.sub(zh, result)
    return result


def generate_highlight(title, abstract):
    """根据标题和摘要生成一句中文核心亮点"""
    combined = (title + " " + abstract).lower()

    highlights = []

    # 检测研究类型和方法
    if "first" in combined or "first-in-human" in combined:
        highlights.append("🔬 首次人体试验")
    if "clinical trial" in combined or "phase" in combined:
        highlights.append("🏥 临床试验阶段")
    if "FDA" in combined or "approved" in combined:
        highlights.append("✅ FDA批准相关")
    if "in vivo" in combined:
        highlights.append("🐭 体内验证完成")
    if "meta-analysis" in combined or "systematic review" in combined:
        highlights.append("📊 系统综述/荟萃分析")

    # 检测核心发现
    if "significant" in combined or "significantly" in combined:
        highlights.append("📈 结果统计学显著")
    if "novel" in combined or "new" in combined or "first" in combined:
        highlights.append("💡 新型方法/首次报道")
    if "high throughput" in combined or "large-scale" in combined:
        highlights.append("⚡ 高通量/大规模研究")
    if "single-cell" in combined:
        highlights.append("🔬 单细胞水平分析")
    if "3D" in combined or "three-dimensional" in combined:
        highlights.append("🧊 三维模型/结构")
    if "multimodal" in combined or "multi-modal" in combined:
        highlights.append("🔗 多模态融合")
    if "real-time" in combined or "continuous" in combined:
        highlights.append("⏱️ 实时/连续监测")

    # 检测应用方向
    if "cancer" in combined or "tumor" in combined:
        if "diagnos" in combined or "detect" in combined:
            highlights.append("🎯 癌症早期检测")
        elif "treat" in combined or "therapy" in combined:
            highlights.append("💊 癌症治疗新策略")
        else:
            highlights.append("🔬 癌症研究新发现")
    if "Alzheimer" in combined or "neurodegenerative" in combined:
        highlights.append("🧠 神经退行性疾病")
    if "cardiac" in combined or "heart" in combined:
        highlights.append("❤️ 心血管应用")
    if "vaccine" in combined:
        highlights.append("💉 疫苗研发")
    if "organoid" in combined:
        highlights.append("🧫 类器官模型")
    if "CRISPR" in combined or "gene edit" in combined:
        highlights.append("✂️ 基因编辑技术")
    if "brain-computer" in combined or "neural interface" in combined:
        highlights.append("🧠 脑机接口")
    if "wearable" in combined:
        highlights.append("⌚ 可穿戴设备")

    if not highlights:
        highlights.append("📌 该领域新进展")

    return " | ".join(highlights[:3])


def translate_title(title):
    """用简单术语替换生成中文标题"""
    # 先做术语替换
    zh = simple_translate(title)

    # 处理常见句式
    zh = re.sub(r'(?i)^a novel', '一种新型', zh)
    zh = re.sub(r'(?i) for the treatment of', ' 用于治疗', zh)
    zh = re.sub(r'(?i) in patients with', ' 在患者中的应用', zh)
    zh = re.sub(r'(?i) based on deep learning', ' 基于深度学习', zh)
    zh = re.sub(r'(?i) via .+? (and|for|to|in|with)', '', zh)
    zh = re.sub(r'(?i) enables .+? (detection|imaging|diagnosis|therapy|treatment|monitoring)',
                lambda m: ' 实现' + m.group(1) + '突破', zh)

    return zh


def fetch_pubmed(query, max_results=5):
    """从PubMed获取今日最新论文"""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # 只获取今天发表的
    today = date.today()
    date_filter = f'("{today.year}/01/01"[Date - Publication] : "{today.strftime("%Y/%m/%d")}"[Date - Publication])'
    full_query = f"({query}) AND {date_filter}"

    # 搜索
    search_url = f"{base}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(full_query)}&retmax={max_results}&sort=date&retmode=json&datetype=pdat&reldate=1"
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": "BME-Daily/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        id_list = data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  PubMed搜索: {e}")
        return []

    if not id_list:
        return []

    time.sleep(0.5)
    fetch_url = f"{base}/efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
    try:
        req = urllib.request.Request(fetch_url, headers={"User-Agent": "BME-Daily/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
    except Exception as e:
        print(f"  PubMed获取: {e}")
        return []

    papers = []
    for article in root.findall(".//PubmedArticle"):
        title_el = article.find(".//ArticleTitle")
        title = title_el.text if title_el is not None and title_el.text else "N/A"

        journal_el = article.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None and journal_el.text else "N/A"

        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else ""

        # 日期
        year_el = article.find(".//PubDate/Year")
        month_el = article.find(".//PubDate/Month")
        day_el = article.find(".//PubDate/Day")
        pub_date = ""
        if year_el is not None:
            pub_date = year_el.text or ""
            if month_el is not None and month_el.text:
                pub_date += "-" + month_el.text.zfill(2)
                if day_el is not None and day_el.text:
                    pub_date += "-" + day_el.text.zfill(2)

        # 作者
        authors = []
        for a in article.findall(".//Author"):
            last = a.find("LastName")
            fore = a.find("ForeName")
            if last is not None:
                n = last.text or ""
                if fore is not None and fore.text:
                    n = fore.text + " " + n
                authors.append(n)
        author_str = authors[0] + " et al." if authors else ""

        # 摘要
        abstract_parts = article.findall(".//AbstractText")
        abstract = " ".join(el.text or "" for el in abstract_parts if el.text)[:400]

        # 中文翻译 + 亮点
        zh_title = translate_title(title)
        highlight = generate_highlight(title, abstract)

        papers.append({
            "title_en": title,
            "title_zh": zh_title,
            "journal": journal,
            "date": pub_date,
            "authors": author_str,
            "abstract": abstract[:250] + ("..." if len(abstract) > 250 else ""),
            "highlight": highlight,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pmid": pmid,
        })
    return papers


def fetch_arxiv_today(query, max_results=3):
    """从arXiv获取今天的最新预印本"""
    # arXiv按submittedDate排序，过滤今天
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": query, "start": 0, "max_results": max_results,
        "sortBy": "submittedDate", "sortOrder": "descending",
    })
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BME-Daily/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            root = ET.fromstring(resp.read())
    except Exception as e:
        print(f"  arXiv: {e}")
        return []

    today_str = date.today().isoformat()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    papers = []

    for entry in root.findall("a:entry", ns):
        pub_el = entry.find("a:published", ns)
        pub_date = pub_el.text[:10] if pub_el is not None else ""

        # 只保留今天的
        if pub_date != today_str:
            continue

        title_el = entry.find("a:title", ns)
        title = title_el.text.strip() if title_el is not None else "N/A"

        summary_el = entry.find("a:summary", ns)
        abstract = summary_el.text.strip()[:250] + "..." if summary_el is not None and summary_el.text else ""

        id_el = entry.find("a:id", ns)
        aid = id_el.text.split("/")[-1] if id_el is not None else ""

        authors = []
        for a in entry.findall("a:author", ns):
            n = a.find("a:name", ns)
            if n is not None:
                authors.append(n.text)
        author_str = authors[0] + " et al." if authors else ""

        zh_title = translate_title(title)
        highlight = generate_highlight(title, abstract)

        papers.append({
            "title_en": title,
            "title_zh": zh_title,
            "journal": "arXiv预印本",
            "date": pub_date,
            "authors": author_str,
            "abstract": abstract,
            "highlight": highlight,
            "url": f"https://arxiv.org/abs/{aid}",
            "pmid": aid,
        })
    return papers


def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"pmids": [], "dates": {}}


def save_cache(cache):
    cutoff = (date.today() - timedelta(days=3)).isoformat()
    cache["pmids"] = cache["pmids"][-500:]
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, ensure_ascii=False)
    except:
        pass


def send_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = TO_EMAIL
    msg["Subject"] = Header(subject, "utf-8")
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        s = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        s.starttls()
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.sendmail(SMTP_USER, [TO_EMAIL], msg.as_string())
        s.quit()
        return True
    except Exception as e:
        print(f"[Email] {e}")
        return False


def generate_html(all_papers):
    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日")
    total = sum(len(v) for v in all_papers.values())

    colors = {
        "🧬 生物材料": "#27ae60", "🖥️ 医学影像与AI": "#2980b9",
        "🧫 组织工程与再生医学": "#8e44ad", "🧠 神经工程与脑机接口": "#e74c3c",
        "💊 纳米医学与药物递送": "#f39c12", "📟 生物传感器与可穿戴": "#1abc9c",
        "✂️ 基因编辑与合成生物学": "#e67e22", "🤖 AI+药物发现": "#3498db",
        "📄 arXiv预印本": "#7f8c8d",
    }

    sections = ""
    for topic, papers in all_papers.items():
        if not papers:
            continue
        c = colors.get(topic, "#333")
        sections += f'<div style="margin:20px 0 10px;"><h3 style="color:{c};border-left:4px solid {c};padding-left:10px;margin:0;">{topic} <span style="font-size:14px;color:#999;">({len(papers)}篇)</span></h3></div>'

        for p in papers:
            # 顶刊标记
            tag = ""
            for tj in TOP_JOURNALS:
                if tj.lower() in p["journal"].lower():
                    tag = ' <span style="background:#ff6b6b;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;">顶刊</span>'
                    break

            # 是否当日
            today_tag = ""
            if str(date.today()) in p.get("date", ""):
                today_tag = ' <span style="background:#27ae60;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;">今日</span>'

            sections += f"""<div style="margin:10px 0;padding:14px;background:#f8f9fa;border-radius:8px;border-left:3px solid {c};">
<div style="font-weight:bold;font-size:15px;margin-bottom:6px;line-height:1.4;">
    <a href="{p['url']}" style="color:#2c3e50;text-decoration:none;" target="_blank">{p['title_zh']}</a>
    {tag}{today_tag}
</div>
<div style="color:#666;font-size:11px;margin-bottom:6px;">
    {p['journal']} · {p.get('date','')} · {p['authors']}
</div>
<div style="background:#fff;padding:8px 10px;border-radius:4px;margin:6px 0;font-size:13px;color:#555;line-height:1.5;">
    <span style="color:{c};font-weight:bold;">💡 核心亮点：</span>{p['highlight']}
</div>
<div style="color:#888;font-size:12px;line-height:1.4;margin-top:4px;">
    <em>原文：{p['title_en'][:150]}{'...' if len(p.get('title_en',''))>150 else ''}</em>
</div>
</div>"""

    # 无论文时
    if total == 0:
        sections = """
<div style="text-align:center;padding:40px;color:#999;">
    <div style="font-size:48px;margin-bottom:10px;">📭</div>
    <div style="font-size:16px;">今日暂无该领域最新论文</div>
    <div style="font-size:12px;margin-top:8px;">PubMed数据库可能存在1-2天延迟，请明天再查看</div>
</div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei',sans-serif;max-width:720px;margin:0 auto;padding:20px;color:#333;background:#f0f2f5;">
<div style="background:#fff;border-radius:12px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.06);">

<div style="text-align:center;padding-bottom:16px;border-bottom:2px solid #2c3e50;margin-bottom:16px;">
    <h1 style="color:#1a1a1a;margin:0 0 6px;font-size:22px;">🔬 生物医学工程 · 今日前沿</h1>
    <p style="color:#999;margin:0;font-size:13px;">{today_str} · 仅推送当日发表 · 共 {total} 篇</p>
</div>

<div style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 16px;justify-content:center;">
{''.join(f'<span style="background:{colors.get(t,"#999")};color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;">{t}:{len(p)}</span>' for t, p in all_papers.items() if p)}
</div>

{sections}

<div style="background:#eaf2f8;padding:12px;border-left:4px solid #2980b9;margin:20px 0 0;border-radius:4px;font-size:12px;">
<strong>📌 说明</strong><br>
仅推送<strong>今日（{today_str}）</strong>正式发表的最新论文 · 来源：PubMed / arXiv · 自动去重<br>
中文标题由术语替换生成，核心亮点由AI自动提炼 · 仅供参考，请以原文为准
</div>

<div style="background:#fff3cd;padding:10px;border-left:4px solid #ffc107;margin:10px 0 0;border-radius:4px;font-size:12px;">
<strong>⚠️ 免责声明</strong> 本报告由自动化系统生成，仅用于学术信息追踪，不构成任何建议。
</div>

</div>
<p style="text-align:center;color:#bbb;font-size:11px;margin-top:12px;">BME前沿日报 · 每日自动推送 · 仅当日最新</p>
</body></html>"""


def main():
    print("===== BME今日前沿 =====")
    print(f"日期: {date.today()}")
    cache = load_cache()
    all_papers = {}

    for topic, query in TOPICS.items():
        print(f"[{topic}]")
        papers = fetch_pubmed(query, 4)
        new_papers = [p for p in papers if p["pmid"] not in cache["pmids"]]
        print(f"  今日: {len(new_papers)} 篇")
        if new_papers:
            all_papers[topic] = new_papers
            for p in new_papers:
                cache["pmids"].append(p["pmid"])
        time.sleep(1)

    # arXiv
    print("[arXiv] 生物医学工程...")
    arxiv = fetch_arxiv_today("biomedical OR tissue engineering OR medical imaging OR drug delivery OR biosensor", 3)
    new_arxiv = [p for p in arxiv if p["pmid"] not in cache["pmids"]]
    if new_arxiv:
        all_papers["📄 arXiv预印本"] = new_arxiv
        for p in new_arxiv:
            cache["pmids"].append(p["pmid"])
    print(f"  今日: {len(new_arxiv)} 篇")

    total = sum(len(v) for v in all_papers.values())
    print(f"总计: {total} 篇今日最新论文")

    if total > 0:
        html = generate_html(all_papers)
        subject = f"🔬 BME今日前沿 - {date.today().strftime('%Y-%m-%d')} ({total}篇)"
        ok = send_email(subject, html)
        print(f"邮件: {'✅' if ok else '❌'}")
    else:
        # 无新论文也发送通知
        html = generate_html(all_papers)
        subject = f"🔬 BME今日前沿 - {date.today().strftime('%Y-%m-%d')} (暂无更新)"
        send_email(subject, html)
        print("无新论文，已发送空报告")

    save_cache(cache)
    print("完成")


if __name__ == "__main__":
    main()
