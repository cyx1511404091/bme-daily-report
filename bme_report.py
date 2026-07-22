# -*- coding: utf-8 -*-
"""
生物医学工程 (BME) 每日前沿研究推送
通过PubMed/arXiv API获取最新论文
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

TOPICS = {
    "生物材料": '("biomaterials"[MeSH Terms] OR "biomaterial"[Title/Abstract] OR "bioactive material"[Title/Abstract]) AND ("2025"[Date - Publication] : "3000"[Date - Publication])',
    "医学影像与AI": '("medical imaging"[Title/Abstract] OR "deep learning radiology"[Title/Abstract] OR "AI diagnosis"[Title/Abstract]) AND ("2025"[Date - Publication] : "3000"[Date - Publication])',
    "组织工程与再生医学": '("tissue engineering"[MeSH Terms] OR "regenerative medicine"[Title/Abstract] OR "organoid"[Title/Abstract] OR "3D bioprinting"[Title/Abstract]) AND ("2025"[Date - Publication] : "3000"[Date - Publication])',
    "神经工程与脑机接口": '("neural engineering"[Title/Abstract] OR "brain-computer interface"[Title/Abstract] OR "neuroprosthetic"[Title/Abstract]) AND ("2025"[Date - Publication] : "3000"[Date - Publication])',
    "纳米医学与药物递送": '("nanomedicine"[MeSH Terms] OR "drug delivery nanoparticle"[Title/Abstract] OR "theranostic"[Title/Abstract] OR "lipid nanoparticle"[Title/Abstract]) AND ("2025"[Date - Publication] : "3000"[Date - Publication])',
    "生物传感器与可穿戴": '("biosensor"[MeSH Terms] OR "wearable sensor"[Title/Abstract] OR "point-of-care"[Title/Abstract] OR "lab-on-a-chip"[Title/Abstract]) AND ("2025"[Date - Publication] : "3000"[Date - Publication])',
    "基因编辑与合成生物学": '("CRISPR"[Title/Abstract] OR "gene therapy"[MeSH Terms] OR "synthetic biology"[Title/Abstract] OR "base editing"[Title/Abstract]) AND ("2025"[Date - Publication] : "3000"[Date - Publication])',
    "AI+药物发现": '("AI drug discovery"[Title/Abstract] OR "machine learning drug design"[Title/Abstract] OR "AlphaFold"[Title/Abstract] OR "computational drug repurposing"[Title/Abstract]) AND ("2025"[Date - Publication] : "3000"[Date - Publication])',
}

TOP_JOURNALS = [
    "Nature Biomedical Engineering", "Nature Biotechnology", "Nature Medicine",
    "Science Translational Medicine", "Cell", "Nature", "Science",
    "Advanced Materials", "ACS Nano", "Biomaterials",
    "IEEE Transactions on Biomedical Engineering", "Medical Image Analysis",
    "Lab on a Chip", "Nature Communications", "PNAS",
]

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bme_papers_cache.json")


def fetch_pubmed(query, max_results=5):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    search_url = base_url + "/esearch.fcgi?db=pubmed&term=" + urllib.parse.quote(query) + "&retmax=" + str(max_results) + "&sort=date&retmode=json"
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": "BME-Daily/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            id_list = json.loads(resp.read()).get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print("  PubMed search error: " + str(e))
        return []
    if not id_list:
        return []
    time.sleep(0.5)
    fetch_url = base_url + "/efetch.fcgi?db=pubmed&id=" + ",".join(id_list) + "&retmode=xml"
    try:
        req = urllib.request.Request(fetch_url, headers={"User-Agent": "BME-Daily/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
    except Exception as e:
        print("  PubMed fetch error: " + str(e))
        return []

    papers = []
    for article in root.findall(".//PubmedArticle"):
        title_el = article.find(".//ArticleTitle")
        title = title_el.text if title_el is not None and title_el.text else "N/A"
        journal_el = article.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None and journal_el.text else "N/A"
        year_el = article.find(".//PubDate/Year")
        month_el = article.find(".//PubDate/Month")
        date_str = ""
        if year_el is not None:
            date_str = year_el.text or ""
            if month_el is not None and month_el.text:
                date_str = year_el.text + " " + month_el.text
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else ""
        authors = []
        for author in article.findall(".//Author"):
            last = author.find("LastName")
            fore = author.find("ForeName")
            if last is not None:
                n = last.text or ""
                if fore is not None and fore.text:
                    n = fore.text + " " + n
                authors.append(n)
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        abstract_el = article.find(".//AbstractText")
        abstract = ""
        if abstract_el is not None and abstract_el.text:
            abstract = abstract_el.text[:300] + "..."
        papers.append({
            "title": title, "journal": journal, "date": date_str,
            "authors": author_str, "abstract": abstract,
            "url": "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/", "pmid": pmid,
        })
    return papers


def fetch_arxiv(query, max_results=3):
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": query, "start": 0, "max_results": max_results,
        "sortBy": "submittedDate", "sortOrder": "descending",
    })
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BME-Daily/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
    except Exception as e:
        print("  arXiv error: " + str(e))
        return []

    ns = {"a": "http://www.w3.org/2005/Atom"}
    papers = []
    for entry in root.findall("a:entry", ns):
        title_el = entry.find("a:title", ns)
        title = title_el.text.strip() if title_el is not None else "N/A"
        summary_el = entry.find("a:summary", ns)
        summary = summary_el.text.strip()[:250] + "..." if summary_el is not None and summary_el.text else ""
        published_el = entry.find("a:published", ns)
        d = published_el.text[:10] if published_el is not None else ""
        id_el = entry.find("a:id", ns)
        aid = id_el.text.split("/")[-1] if id_el is not None else ""
        authors = []
        for a in entry.findall("a:author", ns):
            n = a.find("a:name", ns)
            if n is not None: authors.append(n.text)
        papers.append({
            "title": title, "journal": "arXiv", "date": d,
            "authors": ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
            "abstract": summary, "url": "https://arxiv.org/abs/" + aid, "pmid": aid,
        })
    return papers


def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"pmids": [], "dates": {}}


def save_cache(cache):
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    cache["dates"] = {k: v for k, v in cache["dates"].items() if k >= cutoff}
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
        print("[Email] " + str(e))
        return False


def generate_html(all_papers):
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    total = sum(len(v) for v in all_papers.values())

    colors = {
        "生物材料": "#27ae60", "医学影像与AI": "#2980b9",
        "组织工程与再生医学": "#8e44ad", "神经工程与脑机接口": "#e74c3c",
        "纳米医学与药物递送": "#f39c12", "生物传感器与可穿戴": "#1abc9c",
        "基因编辑与合成生物学": "#e67e22", "AI+药物发现": "#3498db",
    }

    sections = ""
    for topic, papers in all_papers.items():
        if not papers:
            continue
        c = colors.get(topic, "#333")
        sections += '<h3 style="color:' + c + ';margin-top:20px;border-left:4px solid ' + c + ';padding-left:10px;">' + topic + ' (' + str(len(papers)) + '篇)</h3>'
        for p in papers:
            tag = ""
            for tj in TOP_JOURNALS:
                if tj.lower() in p["journal"].lower():
                    tag = ' <span style="background:#ff6b6b;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;">顶刊</span>'
                    break
            sections += '<div style="margin:12px 0;padding:12px;background:#f8f9fa;border-radius:8px;"><div style="font-weight:bold;font-size:14px;margin-bottom:4px;"><a href="' + p["url"] + '" style="color:#2c3e50;text-decoration:none;" target="_blank">' + p["title"] + '</a>' + tag + '</div><div style="color:#888;font-size:12px;margin:4px 0;">' + p["journal"] + ' | ' + p["date"] + ' | ' + p["authors"] + '</div><div style="color:#555;font-size:13px;line-height:1.5;margin-top:4px;">' + p.get("abstract", "") + '</div></div>'

    tags_html = "".join(
        '<span style="background:' + colors.get(t, "#999") + ';color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;">' + t + ': ' + str(len(p)) + '篇</span>'
        for t, p in all_papers.items() if p
    )

    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei',sans-serif;max-width:720px;margin:0 auto;padding:20px;color:#333;background:#f0f2f5;">
<div style="background:#fff;border-radius:12px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.06);">
<h1 style="color:#1a1a1a;border-bottom:3px solid #2c3e50;padding-bottom:10px;margin:0 0 8px;">生物医学工程前沿日报</h1>
<p style="color:#999;margin:0 0 20px;">""" + today_str + """ | 共 """ + str(total) + """ 篇 | 8个子领域</p>
<div style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 20px;">""" + tags_html + """</div>
""" + sections + """
<div style="background:#eaf2f8;padding:12px;border-left:4px solid #2980b9;margin:20px 0;border-radius:4px;"><strong>数据来源</strong><br>PubMed (NCBI) · arXiv | 2025年至今 | 自动去重</div>
<div style="background:#fff3cd;padding:12px;border-left:4px solid #ffc107;margin:10px 0;border-radius:4px;"><strong>免责声明</strong><br>自动化生成，仅用于学术信息追踪。</div>
</div>
<p style="text-align:center;color:#bbb;font-size:12px;margin-top:16px;">BME每日前沿 v1.0 | 每天自动推送</p>
</body></html>"""


def main():
    print("===== BME每日前沿研究 =====")
    cache = load_cache()
    all_papers = {}

    for topic, query in TOPICS.items():
        print("[" + topic + "]")
        papers = fetch_pubmed(query, 4)
        new_papers = [p for p in papers if p["pmid"] not in cache["pmids"]]
        print("  PubMed: " + str(len(new_papers)) + " 篇新论文")
        all_papers[topic] = new_papers
        for p in new_papers:
            cache["pmids"].append(p["pmid"])
        time.sleep(1)

    # arXiv补充
    print("[arXiv] 生物医学工程预印本...")
    arxiv_papers = fetch_arxiv("biomedical engineering OR tissue engineering OR medical imaging", 3)
    new_arxiv = [p for p in arxiv_papers if p["pmid"] not in cache["pmids"]]
    all_papers["arXiv预印本"] = new_arxiv
    for p in new_arxiv:
        cache["pmids"].append(p["pmid"])

    total = sum(len(v) for v in all_papers.values())
    print("总计: " + str(total) + " 篇新论文")

    if total > 0:
        html = generate_html(all_papers)
        subject = "生物医学工程前沿日报 - " + datetime.now().strftime("%Y-%m-%d")
        ok = send_email(subject, html)
        print("邮件发送: " + ("成功" if ok else "失败"))
    else:
        print("无新论文，跳过发送")

    save_cache(cache)
    print("完成")


if __name__ == "__main__":
    main()
