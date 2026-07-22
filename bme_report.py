# -*- coding: utf-8 -*-
"""
生物医学工程 (BME) 每日前沿研究推送 — 中文精华版
- 仅推送当日最新论文
- 自动匹配中科院期刊分区
- 每篇论文含中文总结要点
- 按分区优先级排列，精简冗余
"""
import json, os, re, smtplib, time, urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime, date, timedelta


# ============================================================
#  配置
# ============================================================
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 587
SMTP_USER = "1511404091@qq.com"
SMTP_PASSWORD = "iwzwcypzvwcnjgeg"
TO_EMAIL = "A1980123qwe@outlook.com"

# 中科院期刊分区数据库（基于2025年升级版，大类分区）
# 格式: "期刊名关键词(小写)": (分区, "大类学科", "简称")
CAS_ZONE = {
    # ===== 医学/生物医学 一区 =====
    "nature biomedical engineering":    ("1区", "医学", "Nat Biomed Eng"),
    "nature biotechnology":             ("1区", "生物学", "Nat Biotechnol"),
    "nature medicine":                  ("1区", "医学", "Nat Med"),
    "science translational medicine":   ("1区", "医学", "Sci Transl Med"),
    "cell":                             ("1区", "生物学", "Cell"),
    "nature":                           ("1区", "综合性期刊", "Nature"),
    "science":                          ("1区", "综合性期刊", "Science"),
    "lancet":                           ("1区", "医学", "Lancet"),
    "new england journal of medicine":  ("1区", "医学", "NEJM"),
    "nejm":                             ("1区", "医学", "NEJM"),
    "jama":                             ("1区", "医学", "JAMA"),
    "nature materials":                 ("1区", "材料科学", "Nat Mater"),
    "nature nanotechnology":            ("1区", "材料科学", "Nat Nanotechnol"),
    "nature methods":                   ("1区", "生物学", "Nat Methods"),
    "nature genetics":                  ("1区", "生物学", "Nat Genet"),
    "cancer cell":                      ("1区", "医学", "Cancer Cell"),
    "immunity":                         ("1区", "医学", "Immunity"),
    "cell stem cell":                   ("1区", "医学", "Cell Stem Cell"),
    "neuron":                           ("1区", "医学", "Neuron"),
    "cell metabolism":                  ("1区", "医学", "Cell Metab"),
    "nature neuroscience":              ("1区", "医学", "Nat Neurosci"),
    "nature immunology":                ("1区", "医学", "Nat Immunol"),
    "nature cancer":                    ("1区", "医学", "Nat Cancer"),

    # ===== 材料/工程 一区 =====
    "advanced materials":               ("1区", "材料科学", "Adv Mater"),
    "advanced functional materials":     ("1区", "材料科学", "Adv Funct Mater"),
    "acs nano":                         ("1区", "材料科学", "ACS Nano"),
    "nano letters":                     ("1区", "材料科学", "Nano Lett"),
    "nano today":                       ("1区", "材料科学", "Nano Today"),
    "nano energy":                      ("1区", "材料科学", "Nano Energy"),
    "science advances":                 ("1区", "综合性期刊", "Sci Adv"),
    "matter":                           ("1区", "材料科学", "Matter"),
    "materials today":                  ("1区", "材料科学", "Mater Today"),
    "acs central science":              ("1区", "化学", "ACS Cent Sci"),
    "angewandte chemie":                ("1区", "化学", "Angew Chem"),
    "journal of the american chemical society": ("1区", "化学", "JACS"),

    # ===== 生物材料/组织工程 一区 =====
    "biomaterials":                     ("1区", "医学", "Biomaterials"),
    "acta biomaterialia":               ("1区", "医学", "Acta Biomater"),
    "bioactive materials":              ("1区", "医学", "Bioact Mater"),
    "theranostics":                     ("1区", "医学", "Theranostics"),

    # ===== 综合一区 =====
    "nature communications":            ("1区", "综合性期刊", "Nat Commun"),
    "pnas":                             ("1区", "综合性期刊", "PNAS"),
    "proceedings of the national academy": ("1区", "综合性期刊", "PNAS"),
    "science bulletin":                 ("1区", "综合性期刊", "Sci Bull"),
    "national science review":          ("1区", "综合性期刊", "Natl Sci Rev"),
    "research":                         ("1区", "综合性期刊", "Research"),
    "science china":                    ("1区", "综合性期刊", "Sci China"),

    # ===== 传感器/诊断 一区 =====
    "biosensors and bioelectronics":    ("1区", "工程技术", "Biosens Bioelectron"),
    "acs sensors":                      ("1区", "化学", "ACS Sens"),
    "lab on a chip":                    ("1区", "工程技术", "Lab Chip"),
    "analytical chemistry":             ("1区", "化学", "Anal Chem"),
    "sensors and actuators b":          ("1区", "工程技术", "Sens Actuators B"),

    # ===== 医学影像 一区 =====
    "medical image analysis":           ("1区", "医学", "Med Image Anal"),
    "radiology":                        ("1区", "医学", "Radiology"),
    "ieee transactions on medical imaging": ("1区", "计算机科学", "IEEE TMI"),
    "ieee transactions on pattern analysis": ("1区", "计算机科学", "IEEE TPAMI"),
    "ieee transactions on image processing": ("1区", "计算机科学", "IEEE TIP"),

    # ===== 药物发现/计算 一区 =====
    "nature reviews drug discovery":    ("1区", "医学", "Nat Rev Drug Discov"),
    "drug resistance updates":          ("1区", "医学", "Drug Resist Update"),
    "advanced drug delivery reviews":   ("1区", "医学", "Adv Drug Deliv Rev"),
    "trends in pharmacological sciences": ("1区", "医学", "Trends Pharmacol Sci"),
    "pharmacology and therapeutics":    ("1区", "医学", "Pharmacol Ther"),
    "journal of controlled release":    ("1区", "医学", "J Control Release"),
    "molecular therapy":                ("1区", "医学", "Mol Ther"),
    "nucleic acids research":           ("1区", "生物学", "Nucleic Acids Res"),

    # ===== 神经工程 一区 =====
    "nature biomedical engineering":    ("1区", "医学", "Nat Biomed Eng"),
    "brain":                            ("1区", "医学", "Brain"),
    "brain stimulation":                ("1区", "医学", "Brain Stimul"),
    "ieee transactions on neural systems": ("1区", "医学", "IEEE TNSRE"),
    "journal of neural engineering":    ("1区", "医学", "J Neural Eng"),

    # ===== 二区期刊 =====
    "acs applied materials":            ("2区", "材料科学", "ACS Appl Mater"),
    "chemical engineering journal":     ("2区", "化学", "Chem Eng J"),
    "small":                            ("2区", "材料科学", "Small"),
    "nanoscale":                        ("2区", "材料科学", "Nanoscale"),
    "journal of materials chemistry b": ("2区", "材料科学", "J Mater Chem B"),
    "biomaterials science":             ("2区", "医学", "Biomater Sci"),
    "acs biomaterials":                 ("2区", "材料科学", "ACS Biomater"),
    "tissue engineering":               ("2区", "医学", "Tissue Eng"),
    "frontiers in bioengineering":      ("2区", "医学", "Front Bioeng"),
    "biomedical optics express":        ("2区", "医学", "Biomed Opt Express"),
    "neuroimage":                       ("2区", "医学", "NeuroImage"),
    "ieee transactions on biomedical engineering": ("2区", "医学", "IEEE TBME"),
    "journal of biomedical optics":     ("2区", "医学", "J Biomed Opt"),
    "physics in medicine and biology":  ("2区", "医学", "Phys Med Biol"),
    "journal of biomechanics":          ("2区", "医学", "J Biomech"),
    "biotechnology and bioengineering": ("2区", "生物学", "Biotechnol Bioeng"),
    "journal of biomedical materials":  ("2区", "医学", "J Biomed Mater"),
    "macromolecular bioscience":        ("2区", "材料科学", "Macromol Biosci"),
    "colloids and surfaces b":          ("2区", "化学", "Colloids Surf B"),
    "international journal of nanomedicine": ("2区", "医学", "Int J Nanomed"),
    "nanomedicine":                     ("2区", "医学", "Nanomedicine"),
    "european journal of pharmaceutics":("2区", "医学", "Eur J Pharm"),
    "molecular pharmaceutics":          ("2区", "医学", "Mol Pharm"),
    "pharmaceutical research":          ("2区", "医学", "Pharm Res"),
    "drug delivery and translational":  ("2区", "医学", "Drug Deliv Transl"),
    "sensors":                          ("2区", "工程技术", "Sensors"),
    "ieee sensors journal":             ("2区", "工程技术", "IEEE Sens J"),
    "biomedical signal processing":     ("2区", "计算机科学", "Biomed Signal Process"),
    "computers in biology and medicine":("2区", "计算机科学", "Comput Biol Med"),
    "computer methods and programs":    ("2区", "计算机科学", "Comput Meth Prog Bio"),
    "artificial intelligence in medicine": ("2区", "计算机科学", "Artif Intell Med"),
    "journal of biomedical informatics":("2区", "医学", "J Biomed Inform"),
    "briefings in bioinformatics":      ("2区", "生物学", "Brief Bioinform"),
    "bioinformatics":                   ("2区", "生物学", "Bioinformatics"),
    "plos computational biology":       ("2区", "生物学", "PLoS Comput Biol"),
    "bmc bioinformatics":               ("2区", "生物学", "BMC Bioinformatics"),
    "frontiers in neuroscience":        ("2区", "医学", "Front Neurosci"),
    "frontiers in cellular neuroscience": ("2区", "医学", "Front Cell Neurosci"),
    "journal of neuroengineering":      ("2区", "医学", "J Neuroeng Rehabil"),
    "ieee reviews in biomedical engineering": ("2区", "医学", "IEEE Rev Biomed Eng"),
    "annual review of biomedical engineering": ("2区", "医学", "Annu Rev Biomed Eng"),
    "cancer research":                  ("2区", "医学", "Cancer Res"),
    "clinical cancer research":         ("2区", "医学", "Clin Cancer Res"),
    "advanced healthcare materials":    ("2区", "材料科学", "Adv Healthc Mater"),
    "advanced science":                 ("2区", "综合性期刊", "Adv Sci"),
    "elife":                            ("2区", "生物学", "eLife"),
    "cell reports":                     ("2区", "生物学", "Cell Rep"),
    "cell reports medicine":            ("2区", "医学", "Cell Rep Med"),
    "iscience":                         ("2区", "综合性期刊", "iScience"),
    "communications biology":           ("2区", "生物学", "Commun Biol"),
    "communications medicine":          ("2区", "医学", "Commun Med"),
    "communications materials":         ("2区", "材料科学", "Commun Mater"),
    "scientific reports":               ("2区", "综合性期刊", "Sci Rep"),
    "science signaling":                ("2区", "生物学", "Sci Signal"),
    "journal of nanobiotechnology":     ("2区", "生物学", "J Nanobiotechnol"),
    "nanotoxicology":                   ("2区", "医学", "Nanotoxicology"),
    "wiley interdisciplinary reviews nanomedicine": ("2区", "医学", "WIREs Nanomed"),
    "drug discovery today":             ("2区", "医学", "Drug Discov Today"),
    "expert opinion on drug delivery":  ("2区", "医学", "Expert Opin Drug Deliv"),
    "bioconjugate chemistry":           ("2区", "化学", "Bioconjug Chem"),
    "organic letters":                  ("2区", "化学", "Org Lett"),
    "journal of medicinal chemistry":   ("2区", "医学", "J Med Chem"),
    "european journal of medicinal chemistry": ("2区", "医学", "Eur J Med Chem"),
    "stem cells":                       ("2区", "医学", "Stem Cells"),
    "stem cell reports":                ("2区", "医学", "Stem Cell Rep"),
    "stem cells translational medicine":("2区", "医学", "Stem Cells Transl Med"),
    "cancer letters":                   ("2区", "医学", "Cancer Lett"),
    "journal of nanobiotechnology":     ("2区", "生物学", "J Nanobiotechnol"),
    "molecular cancer":                 ("2区", "医学", "Mol Cancer"),

    # ===== 三区/四区快速识别 =====
    "journal of biomedical materials research": ("3区", "医学", "J Biomed Mater Res"),
    "artificial organs":                ("3区", "医学", "Artif Organs"),
    "biomedical engineering online":    ("3区", "医学", "Biomed Eng Online"),
    "medical engineering and physics":  ("3区", "医学", "Med Eng Phys"),
    "journal of biomaterials applications": ("3区", "医学", "J Biomater Appl"),
    "materials science and engineering c": ("3区", "材料科学", "Mater Sci Eng C"),
    "biomedical microdevices":          ("3区", "医学", "Biomed Microdevices"),
    "journal of tissue engineering":    ("3区", "医学", "J Tissue Eng"),
    "regenerative medicine":            ("3区", "医学", "Regen Med"),
    "regen engineering":                ("3区", "医学", "Regen Eng"),
    "plos one":                         ("3区", "综合性期刊", "PLoS ONE"),
    "peerj":                            ("3区", "综合性期刊", "PeerJ"),
    "bmc biomedical engineering":       ("3区", "医学", "BMC Biomed Eng"),
    "applied sciences":                 ("4区", "工程技术", "Appl Sci"),
    "micromachines":                    ("3区", "工程技术", "Micromachines"),
    "bioengineering":                   ("3区", "医学", "Bioengineering"),
    "biomedicines":                     ("3区", "医学", "Biomedicines"),
    "pharmaceutics":                    ("3区", "医学", "Pharmaceutics"),
    "nanomaterials":                    ("3区", "材料科学", "Nanomaterials"),
    "polymers":                         ("3区", "化学", "Polymers"),
    "gels":                             ("3区", "化学", "Gels"),
}


def get_cas_zone(journal_name):
    """查询期刊的中科院分区 — 精确匹配优先，模糊匹配兜底"""
    jl = journal_name.lower().strip()
    # 精确匹配
    if jl in CAS_ZONE:
        return CAS_ZONE[jl]
    # 模糊匹配：优先长关键词（更精确）
    best = None
    best_len = 0
    for key, (zone, field, abbr) in CAS_ZONE.items():
        if key in jl:
            if len(key) > best_len:
                best_len = len(key)
                best = (zone, field, abbr)
        elif jl in key and len(jl) > best_len:
            best_len = len(jl)
            best = (zone, field, abbr)
    return best if best else (None, None, None)


# BME子领域搜索词
TOPICS = {
    "🧬 生物材料": "biomaterials OR bioactive material OR scaffold OR hydrogel OR biomimetic material",
    "🖥️ 医学影像与AI": "deep learning medical imaging OR AI radiology OR computer-aided diagnosis OR medical image segmentation",
    "🧫 组织工程与再生医学": "tissue engineering OR organoid OR 3D bioprinting OR stem cell therapy OR regenerative medicine",
    "🧠 神经工程与脑机接口": "brain-computer interface OR neural engineering OR neuroprosthetic OR neural recording OR neuromodulation",
    "💊 纳米医学与药物递送": "nanomedicine OR nanoparticle drug delivery OR lipid nanoparticle OR mRNA delivery OR targeted therapy",
    "📟 生物传感器与可穿戴": "biosensor OR wearable health monitor OR point-of-care diagnostics OR lab-on-a-chip OR continuous glucose monitor",
    "✂️ 基因编辑与合成生物学": "CRISPR gene editing OR base editing OR prime editing OR synthetic biology OR gene therapy clinical",
    "🤖 AI+药物发现": "AI drug discovery OR AlphaFold protein design OR machine learning drug screening OR computational drug repurposing",
}

# 术语翻译字典（长词优先匹配）
TERM_DICT = {
    "extracellular vesicle": "细胞外囊泡", "artificial intelligence": "人工智能",
    "machine learning": "机器学习", "deep learning": "深度学习",
    "synthetic biology": "合成生物学", "metabolic engineering": "代谢工程",
    "drug delivery": "药物递送", "gene therapy": "基因治疗",
    "clinical trial": "临床试验", "stem cell": "干细胞",
    "wound healing": "伤口愈合", "single-cell": "单细胞",
    "multi-omics": "多组学", "neural network": "神经网络",
    "point-of-care": "即时检测", "real-time": "实时",
    "high-throughput": "高通量", "large-scale": "大规模",
    "brain-computer": "脑机", "lipid nanoparticle": "脂质纳米颗粒",
    "targeted therapy": "靶向治疗", "cancer immunotherapy": "肿瘤免疫治疗",
    "personalized medicine": "个性化医疗", "precision medicine": "精准医学",
    "magnetic resonance": "磁共振", "computed tomography": "CT",
    "positron emission": "PET", "optical coherence": "光学相干",
    "surface plasmon": "表面等离子体", "lateral flow": "侧流层析",
    "electrochemical sensor": "电化学传感器", "field-effect transistor": "场效应晶体管",
    "biosensor": "生物传感器", "wearable": "可穿戴",
    "microfluidic": "微流控", "lab-on-a-chip": "芯片实验室",
    "organ-on-a-chip": "器官芯片", "3D bioprinting": "3D生物打印",
    "hydrogel": "水凝胶", "scaffold": "支架",
    "biomaterial": "生物材料", "bioactive": "生物活性",
    "biocompatible": "生物相容性", "biodegradable": "可降解",
    "nanoparticle": "纳米颗粒", "nanofiber": "纳米纤维",
    "nanotube": "纳米管", "quantum dot": "量子点",
    "graphene": "石墨烯", "MXene": "MXene",
    "CRISPR": "CRISPR基因编辑", "base editing": "碱基编辑",
    "prime editing": "先导编辑", "Cas9": "Cas9",
    "organoid": "类器官", "spheroid": "球状体",
    "exosome": "外泌体", "extracellular matrix": "细胞外基质",
    "immunotherapy": "免疫治疗", "CAR-T": "CAR-T",
    "antibody": "抗体", "vaccine": "疫苗",
    "peptide": "多肽", "protein": "蛋白质",
    "DNA": "DNA", "RNA": "RNA", "mRNA": "mRNA",
    "lipid": "脂质", "polymer": "聚合物",
    "silk": "丝素蛋白", "collagen": "胶原蛋白", "gelatin": "明胶",
    "chitosan": "壳聚糖", "alginate": "海藻酸盐",
    "hyaluronic acid": "透明质酸", "polyethylene glycol": "聚乙二醇",
    "polylactic acid": "聚乳酸", "polycaprolactone": "聚己内酯",
    "in vivo": "体内", "in vitro": "体外", "in situ": "原位",
    "diagnosis": "诊断", "prognosis": "预后",
    "therapeutic": "治疗", "therapeutics": "治疗学",
    "regeneration": "再生", "remodeling": "重塑",
    "inflammation": "炎症", "fibrosis": "纤维化",
    "apoptosis": "凋亡", "autophagy": "自噬",
    "metastasis": "转移", "angiogenesis": "血管生成",
    "cancer": "癌症", "tumor": "肿瘤", "tumour": "肿瘤",
    "diabetes": "糖尿病", "Alzheimer": "阿尔茨海默", "Parkinson": "帕金森",
    "cardiac": "心脏", "cardiovascular": "心血管",
    "liver": "肝脏", "kidney": "肾脏", "lung": "肺部",
    "bone": "骨骼", "cartilage": "软骨", "muscle": "肌肉",
    "skin": "皮肤", "blood": "血液", "vascular": "血管",
    "brain": "大脑", "neural": "神经", "cerebral": "脑",
    "spinal cord": "脊髓", "peripheral nerve": "周围神经",
    "metabolomics": "代谢组学", "proteomics": "蛋白质组学",
    "genomics": "基因组学", "transcriptomics": "转录组学",
    "epigenetic": "表观遗传", "epigenetics": "表观遗传学",
    "microbiome": "微生物组", "microbiota": "微生物群",
    "algorithm": "算法", "segmentation": "分割",
    "classification": "分类", "prediction": "预测",
    "monitoring": "监测", "detection": "检测",
    "sensitivity": "灵敏度", "specificity": "特异性",
    "photothermal": "光热", "photodynamic": "光动力",
    "sonodynamic": "声动力", "chemodynamic": "化学动力",
    "immunogenic cell death": "免疫原性细胞死亡",
    "tumor microenvironment": "肿瘤微环境",
    "blood-brain barrier": "血脑屏障",
    "reactive oxygen species": "活性氧", "ROS": "活性氧",
    "metal-organic framework": "金属有机框架",
    "covalent organic framework": "共价有机框架",
    "black phosphorus": "黑磷", "transition metal": "过渡金属",
    "calcium phosphate": "磷酸钙", "bioactive glass": "生物活性玻璃",
    "shape memory": "形状记忆", "self-healing": "自修复",
    "stimuli-responsive": "刺激响应", "pH-responsive": "pH响应",
    "enzyme-responsive": "酶响应", "redox-responsive": "氧化还原响应",
    "thermoresponsive": "温敏", "photo-responsive": "光响应",
    "magnetic-responsive": "磁响应", "ultrasound": "超声",
    "photoacoustic": "光声", "fluorescence": "荧光",
    "chemiluminescence": "化学发光", "bioluminescence": "生物发光",
    "raman": "拉曼", "SERS": "表面增强拉曼",
    "electrospinning": "静电纺丝", "microsphere": "微球",
    "microneedle": "微针", "transdermal": "透皮",
    "injectable": "可注射", "implantable": "可植入",
    "minimally invasive": "微创", "noninvasive": "无创",
    "machine-learning": "机器学习", "deep-learning": "深度学习",
    "convolutional neural": "卷积神经", "transformer": "Transformer",
    "graph neural": "图神经", "generative adversarial": "生成对抗",
    "reinforcement learning": "强化学习", "transfer learning": "迁移学习",
    "self-supervised": "自监督", "federated learning": "联邦学习",
    "explainable AI": "可解释AI", "foundation model": "基础模型",
    "large language": "大语言", "multimodal": "多模态",
    "radiomics": "影像组学", "pathomics": "病理组学",
}

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bme_cache.json")


# ============================================================
#  术语翻译
# ============================================================
def translate_text(text):
    """将英文术语替换为中文"""
    result = text
    for en, zh in sorted(TERM_DICT.items(), key=lambda x: -len(x[0])):
        pattern = re.compile(re.escape(en), re.IGNORECASE)
        result = pattern.sub(zh, result)
    return result


# ============================================================
#  论文总结生成
# ============================================================
def generate_summary(title, abstract, zone=""):
    """
    基于标题和摘要生成详细的中文总结。
    包含：研究背景 → 核心方法 → 关键发现 → 应用前景，输出一段150-300字的结构化总结。
    """
    combined = (title + " " + abstract).lower()
    parts = []

    # ========================
    #  1. 研究背景/动机
    # ========================
    bg = []
    if "cancer" in combined or "tumor" in combined or "tumour" in combined:
        if "breast" in combined:
            bg.append("针对乳腺癌临床诊疗中的瓶颈")
        elif "lung" in combined:
            bg.append("面向肺癌精准诊疗需求")
        elif "liver" in combined or "hepatocellular" in combined:
            bg.append("针对肝癌诊疗难题")
        elif "pancreatic" in combined:
            bg.append("胰腺癌预后极差，亟需新策略")
        elif "colorectal" in combined or "colon" in combined:
            bg.append("结直肠癌高发病率背景下")
        elif "glioblastoma" in combined or "glioma" in combined or "brain tumor" in combined:
            bg.append("脑胶质瘤治疗面临血脑屏障挑战")
        elif "prostate" in combined:
            bg.append("前列腺癌精准诊疗需求迫切")
        elif "melanoma" in combined or "skin cancer" in combined:
            bg.append("黑色素瘤免疫治疗耐药亟待解决")
        else:
            bg.append("当前肿瘤诊疗面临精准性不足的挑战")
    elif "Alzheimer" in combined or "dementia" in combined:
        bg.append("阿尔茨海默病早期诊断手段匮乏")
    elif "Parkinson" in combined:
        bg.append("帕金森病缺乏客观生物标志物")
    elif "diabetes" in combined or "glucose" in combined:
        bg.append("糖尿病管理需要更便捷的监测手段")
    elif "cardiovascular" in combined or "myocardial" in combined or "heart failure" in combined:
        bg.append("心血管疾病是全球首要死亡原因")
    elif "stroke" in combined or "ischemic" in combined:
        bg.append("缺血性脑卒中救治时间窗狭窄")
    elif "infection" in combined or "antibacterial" in combined or "antimicrobial" in combined:
        bg.append("耐药菌感染对全球公共卫生构成严重威胁")
    elif "covid" in combined or "sars" in combined or "pandemic" in combined:
        bg.append("疫情暴露出快速诊断技术的不足")
    elif "wound" in combined:
        bg.append("慢性伤口愈合是临床棘手问题")
    elif "bone" in combined or "osteopor" in combined or "fracture" in combined:
        bg.append("骨缺损修复仍是骨科重大挑战")
    elif "spinal" in combined:
        bg.append("脊髓损伤再生修复极为困难")
    elif "rare disease" in combined or "orphan" in combined:
        bg.append("罕见病治疗选择极为有限")
    elif "obesity" in combined or "metabolic" in combined:
        bg.append("代谢性疾病全球患病率持续攀升")
    elif "aging" in combined or "senescence" in combined or "age-related" in combined:
        bg.append("人口老龄化带来巨大医疗需求")
    if not bg:
        bg.append("该领域存在未满足的临床需求")

    # ========================
    #  2. 研究类型与核心方法
    # ========================
    method = []
    # 研究类型
    if "first-in-human" in combined or "first in human" in combined:
        method.append("首次人体临床试验")
    elif "clinical trial" in combined and ("phase iii" in combined or "phase 3" in combined):
        method.append("开展III期临床试验")
    elif "clinical trial" in combined and ("phase ii" in combined or "phase 2" in combined):
        method.append("开展II期临床试验")
    elif "clinical trial" in combined and ("phase i" in combined or "phase 1" in combined):
        method.append("开展I期临床试验")
    elif "clinical trial" in combined:
        method.append("开展临床试验")
    elif "meta-analysis" in combined or "systematic review" in combined:
        method.append("通过系统综述/荟萃分析方法")
    elif "review" in combined:
        method.append("系统回顾该领域最新进展")

    # AI/计算方法
    if "deep learning" in combined or "neural network" in combined:
        if "transformer" in combined or "attention" in combined:
            method.append("基于Transformer注意力机制构建模型")
        elif "convolution" in combined or "cnn" in combined:
            method.append("利用卷积神经网络提取特征")
        elif "graph neural" in combined or "gnn" in combined:
            method.append("通过图神经网络建模复杂关系")
        elif "generative" in combined or "gan" in combined:
            method.append("采用生成式AI方法")
        elif "foundation model" in combined or "large language" in combined or "llm" in combined:
            method.append("基于大语言模型/基础模型")
        elif "federated" in combined:
            method.append("采用联邦学习保护数据隐私")
        elif "self-supervised" in combined or "contrastive" in combined:
            method.append("利用自监督/对比学习减少标注需求")
        elif "transfer learning" in combined:
            method.append("通过迁移学习克服数据稀缺")
        elif "reinforcement" in combined:
            method.append("运用强化学习优化决策")
        elif "multimodal" in combined:
            method.append("融合多模态数据进行综合分析")
        else:
            method.append("采用深度学习算法实现智能分析")
    elif "machine learning" in combined:
        if "random forest" in combined or "xgboost" in combined or "gradient boosting" in combined:
            method.append("利用集成学习方法进行预测建模")
        elif "support vector" in combined or "svm" in combined:
            method.append("基于支持向量机分类建模")
        else:
            method.append("采用机器学习方法建立预测模型")
    elif "artificial intelligence" in combined or "AI" in combined:
        method.append("利用人工智能技术辅助分析")

    # 实验技术
    if "single-cell" in combined:
        if "sequencing" in combined or "rna-seq" in combined:
            method.append("通过单细胞测序技术解析细胞异质性")
        else:
            method.append("在单细胞水平进行精细分析")
    if "multi-omics" in combined:
        method.append("整合多组学数据进行系统分析")
    if "crispr" in combined:
        if "base edit" in combined:
            method.append("采用碱基编辑技术实现精准基因修正")
        elif "prime edit" in combined:
            method.append("采用先导编辑技术进行大片段基因替换")
        elif "screen" in combined:
            method.append("通过CRISPR全基因组筛选发现关键靶点")
        else:
            method.append("利用CRISPR基因编辑技术进行功能研究")
    if "organoid" in combined:
        if "patient-derived" in combined:
            method.append("构建患者来源类器官模型进行个性化药筛")
        else:
            method.append("构建三维类器官模型模拟体内微环境")
    if "3d bioprint" in combined:
        method.append("采用3D生物打印技术构建仿生组织")
    if "microfluidic" in combined or "lab-on-a-chip" in combined:
        method.append("基于微流控芯片平台实现高通量分析")
    if "organ-on-a-chip" in combined:
        method.append("利用器官芯片技术模拟人体生理环境")

    # 材料相关
    if "hydrogel" in combined:
        if "injectable" in combined:
            method.append("设计可注射水凝胶体系实现微创递送")
        elif "self-healing" in combined:
            method.append("开发自修复水凝胶材料")
        elif "stimuli-responsive" in combined or "responsive" in combined:
            method.append("构建刺激响应型智能水凝胶")
        elif "conductive" in combined:
            method.append("制备导电水凝胶用于电活性组织修复")
        elif "3d" in combined or "print" in combined:
            method.append("开发可3D打印水凝胶墨水")
        else:
            method.append("设计多功能水凝胶材料")
    elif "nanoparticle" in combined or "nanocarrier" in combined or "nanomedicine" in combined:
        if "lipid" in combined or "lnp" in combined:
            method.append("利用脂质纳米颗粒实现高效包载与递送")
        elif "polymeric" in combined:
            method.append("设计聚合物纳米载体实现可控释放")
        elif "mesoporous" in combined or "silica" in combined:
            method.append("基于介孔二氧化硅纳米颗粒构建递送系统")
        elif "metal" in combined or "gold" in combined or "silver" in combined:
            method.append("利用金属纳米颗粒的独特理化性质")
        elif "magnetic" in combined or "iron oxide" in combined:
            method.append("利用磁性纳米颗粒实现磁靶向与成像")
        elif "MOF" in combined or "metal-organic" in combined:
            method.append("基于金属有机框架构建多功能纳米平台")
        elif "exosome" in combined:
            method.append("利用外泌体作为天然纳米载体")
        else:
            method.append("设计智能纳米递送系统")
    if "scaffold" in combined:
        if "decellularized" in combined:
            method.append("利用脱细胞基质支架保持天然微结构")
        elif "electrospun" in combined or "nanofiber" in combined:
            method.append("通过静电纺丝技术制备纳米纤维支架")
        elif "3d-printed" in combined or "3d print" in combined:
            method.append("3D打印个性化支架匹配缺损形态")
        else:
            method.append("构建仿生支架材料引导组织再生")

    # 传感器/诊断
    if "biosensor" in combined:
        if "electrochemical" in combined:
            method.append("开发电化学生物传感器")
        elif "optical" in combined or "fluorescence" in combined:
            method.append("基于光学/荧光检测原理构建传感器")
        elif "wearable" in combined:
            method.append("设计可穿戴生物传感装置")
        elif "implantable" in combined:
            method.append("开发可植入式生物传感器")
        else:
            method.append("构建新型生物传感检测平台")

    if not method:
        method.append("通过系统的实验研究")

    # ========================
    #  3. 关键发现/成果
    # ========================
    findings = []
    if "novel" in combined or "first" in combined:
        findings.append("首次报道了该方法的可行性")
    if "significant" in combined and ("improve" in combined or "enhance" in combined or "superior" in combined):
        findings.append("实验结果显著优于现有临床金标准或同类方法")
    if "high sensitivity" in combined or "highly sensitive" in combined:
        findings.append("检测灵敏度达到极高水平")
    if "high specificity" in combined:
        findings.append("具有优异的检测特异性")
    if "accuracy" in combined or "accurate" in combined:
        if "high" in combined or "improved" in combined or "superior" in combined:
            findings.append("诊断准确率大幅提升")
        else:
            findings.append("验证了良好的准确性")
    if "real-time" in combined:
        findings.append("实现了实时动态监测")
    if "noninvasive" in combined or "non-invasive" in combined:
        findings.append("采用无创/微创方式，减少患者痛苦")
    if "portable" in combined or "wearable" in combined or "point-of-care" in combined:
        findings.append("实现了便携式即时检测，适用于基层医疗")
    if "biodegradable" in combined or "biocompatible" in combined:
        findings.append("材料具有良好的生物相容性和可降解性")
    if "long-term" in combined:
        if "stable" in combined or "stability" in combined:
            findings.append("经过长期验证表现出优异稳定性")
        elif "monitor" in combined or "track" in combined:
            findings.append("可长期连续追踪生理指标变化")
    if "low cost" in combined or "cost-effective" in combined:
        findings.append("成本低廉，有望大规模推广应用")
    if "personalized" in combined or "precision" in combined or "individualized" in combined:
        findings.append("为实现个性化/精准医疗提供新工具")
    if "safe" in combined or "safety" in combined or "no adverse" in combined:
        findings.append("安全性评估结果良好")
    if "synergistic" in combined or "combination" in combined:
        findings.append("联合治疗策略展现出协同增效作用")
    if "target" in combined and ("specific" in combined or "selective" in combined):
        findings.append("实现了对靶标的精准识别与高效作用")
    if "early" in combined and ("diagnos" in combined or "detect" in combined or "screen" in combined):
        findings.append("有望实现疾病的早期筛查与预警")
    if "in vivo" in combined:
        if "mouse" in combined or "mice" in combined or "animal" in combined:
            findings.append("动物体内实验验证了其有效性")
        elif "human" in combined or "patient" in combined:
            findings.append("已在人体/临床样本中验证效果")
        else:
            findings.append("体内实验证实了其生物学效应")
    if "therapeutic" in combined and "efficacy" in combined:
        findings.append("治疗有效性得到实验证实")
    if "overcome" in combined or "address" in combined:
        findings.append("成功克服了现有技术的关键瓶颈")

    # 补充：无匹配时默认
    if not findings:
        findings.append("研究结果验证了方案的可行性与有效性")

    # ========================
    #  4. 应用方向/意义
    # ========================
    apps = []
    if "cancer" in combined or "tumor" in combined or "tumour" in combined:
        if "diagnos" in combined or "detect" in combined or "screen" in combined or "biomarker" in combined:
            apps.append("为癌症早期筛查与精准诊断提供新手段")
        elif "immunotherapy" in combined or "immune" in combined:
            apps.append("为肿瘤免疫治疗开辟新方向")
        elif "drug" in combined or "delivery" in combined or "nanoparticle" in combined:
            apps.append("为肿瘤靶向药物递送提供新策略")
        elif "microenvironment" in combined or "tme" in combined:
            apps.append("为调控肿瘤微环境提供新思路")
        else:
            apps.append("为肿瘤临床治疗提供新的潜在方案")
    if "Alzheimer" in combined or "neurodegenerative" in combined:
        apps.append("为神经退行性疾病诊疗带来新希望")
    if "diabetes" in combined or "glucose" in combined:
        apps.append("为糖尿病精准管理提供技术支持")
    if "cardiac" in combined or "heart" in combined or "cardiovascular" in combined:
        apps.append("有望改善心血管疾病患者预后")
    if "wound" in combined:
        apps.append("为慢性伤口治疗提供新材料与新方案")
    if "bone" in combined or "osteogenic" in combined:
        apps.append("推动骨组织工程临床转化进程")
    if "brain" in combined or "neural" in combined:
        if "interface" in combined or "recording" in combined:
            apps.append("推动脑机接口技术的实用化发展")
        elif "stimulation" in combined:
            apps.append("为神经调控治疗提供新工具")
        else:
            apps.append("为神经系统疾病诊疗提供新路径")
    if "vaccine" in combined:
        apps.append("为疫苗开发提供关键递送技术支持")
    if "antibacterial" in combined or "antimicrobial" in combined or "infection" in combined:
        apps.append("为应对耐药菌感染提供新武器")
    if "drug" in combined and ("discover" in combined or "screen" in combined or "design" in combined):
        apps.append("可大幅加速新药研发进程并降低研发成本")
    if "gene" in combined and ("therapy" in combined or "edit" in combined or "delivery" in combined):
        apps.append("为基因治疗的临床转化提供关键技术支撑")
    if "regenerat" in combined:
        apps.append("推动再生医学向临床应用迈进")
    if "wearable" in combined or "mobile" in combined or "smartphone" in combined:
        apps.append("赋能个人健康管理与远程医疗")
    if "prognosis" in combined or "prognostic" in combined or "survival" in combined:
        apps.append("为疾病预后评估与风险分层提供新工具")

    if not apps:
        apps.append("为该领域的进一步发展提供了重要参考")

    # ========================
    #  5. 拼合为完整段落
    # ========================
    # 研究背景 + 方法
    sentence1 = bg[0] + "，" + "；".join(method[:2]) + "。"

    # 关键发现
    sentence2 = "结果表明，" + "，".join(findings[:3]) + "。"

    # 应用前景
    sentence3 = "该研究" + apps[0] + "。"

    result = sentence1 + " " + sentence2 + " " + sentence3

    # 分区标记
    if zone and "区" in zone:
        if "1" in zone:
            result += "【中科院1区期刊】"
        elif "2" in zone:
            result += "【中科院2区期刊】"

    return result


# ============================================================
#  PubMed 获取（当日优先 → 一周回退）
# ============================================================
def fetch_pubmed(query, max_results=5, days=1):
    """
    从PubMed获取论文。
    days=1: 仅当日；days=7: 近一周。
    返回 (papers, is_fallback): papers列表, is_fallback表示是否为回退数据。
    """
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    today = date.today()

    # 当日查询
    date_filter = f'("{today.year}/01/01"[Date - Publication] : "{today.strftime("%Y/%m/%d")}"[Date - Publication])'
    full_query = f"({query}) AND {date_filter}"

    search_url = f"{base}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(full_query)}&retmax={max_results}&sort=date&retmode=json&datetype=pdat&reldate=1"
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": "BME-Daily/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        id_list = data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  PubMed搜索失败: {e}")
        return [], True

    is_fallback = False
    if not id_list and days >= 7:
        # 回退：近7天
        week_ago = today - timedelta(days=7)
        date_filter = f'("{week_ago.year}/{week_ago.month:02d}/{week_ago.day:02d}"[Date - Publication] : "{today.strftime("%Y/%m/%d")}"[Date - Publication])'
        full_query = f"({query}) AND {date_filter}"
        search_url = f"{base}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(full_query)}&retmax={max_results}&sort=date&retmode=json"
        try:
            req = urllib.request.Request(search_url, headers={"User-Agent": "BME-Daily/2.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            id_list = data.get("esearchresult", {}).get("idlist", [])
            is_fallback = True
        except Exception as e:
            print(f"  PubMed一周回退失败: {e}")
            return [], True

    if not id_list:
        return [], True

    time.sleep(0.5)
    fetch_url = f"{base}/efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
    try:
        req = urllib.request.Request(fetch_url, headers={"User-Agent": "BME-Daily/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
    except Exception as e:
        print(f"  PubMed获取失败: {e}")
        return [], True

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
        author_str = (authors[0] + " et al.") if authors else ""

        # 摘要
        abstract_parts = article.findall(".//AbstractText")
        abstract = " ".join(el.text or "" for el in abstract_parts if el.text)

        # 中科院分区
        zone, field, abbr = get_cas_zone(journal)

        # 中文标题 + 总结
        zh_title = translate_text(title)
        summary = generate_summary(title, abstract, zone or "")

        papers.append({
            "title_en": title,
            "title_zh": zh_title,
            "journal": journal,
            "journal_abbr": abbr or journal[:30],
            "date": pub_date,
            "authors": author_str,
            "abstract": abstract[:350] + ("..." if len(abstract) > 350 else ""),
            "summary": summary,
            "zone": zone,
            "zone_field": field,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pmid": pmid,
            "is_fallback": is_fallback,
        })
    return papers, is_fallback


# ============================================================
#  arXiv 获取（当日优先 → 一周回退）
# ============================================================
def fetch_arxiv(query, max_results=3):
    """
    从arXiv获取预印本。先查当日，无结果则回退一周。
    返回 (papers, is_fallback)。
    """
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": query, "start": 0, "max_results": max_results * 3,
        "sortBy": "submittedDate", "sortOrder": "descending",
    })
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BME-Daily/2.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            root = ET.fromstring(resp.read())
    except Exception as e:
        print(f"  arXiv: {e}")
        return [], True

    today_str = date.today().isoformat()
    week_ago_str = (date.today() - timedelta(days=7)).isoformat()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    today_papers = []
    week_papers = []

    for entry in root.findall("a:entry", ns):
        pub_el = entry.find("a:published", ns)
        pub_date = pub_el.text[:10] if pub_el is not None else ""

        if pub_date == today_str:
            target = today_papers
        elif pub_date >= week_ago_str:
            target = week_papers
        else:
            continue

        title_el = entry.find("a:title", ns)
        title = title_el.text.strip() if title_el is not None else "N/A"

        summary_el = entry.find("a:summary", ns)
        abstract = (summary_el.text.strip()[:350] + "...") if summary_el is not None and summary_el.text else ""

        id_el = entry.find("a:id", ns)
        aid = id_el.text.split("/")[-1] if id_el is not None else ""

        authors = []
        for a in entry.findall("a:author", ns):
            n = a.find("a:name", ns)
            if n is not None:
                authors.append(n.text)
        author_str = (authors[0] + " et al.") if authors else ""

        zh_title = translate_text(title)
        summary_zh = generate_summary(title, abstract, "")

        target.append({
            "title_en": title,
            "title_zh": zh_title,
            "journal": "arXiv预印本",
            "journal_abbr": "arXiv",
            "date": pub_date,
            "authors": author_str,
            "abstract": abstract,
            "summary": summary_zh,
            "zone": "预印本",
            "zone_field": "",
            "url": f"https://arxiv.org/abs/{aid}",
            "pmid": aid,
            "is_fallback": False,
        })

    if today_papers:
        return today_papers[:max_results], False
    elif week_papers:
        for p in week_papers:
            p["is_fallback"] = True
        return week_papers[:max_results], True
    return [], True


# ============================================================
#  缓存
# ============================================================
def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"pmids": [], "dates": {}}


def save_cache(cache):
    cache["pmids"] = cache["pmids"][-500:]
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, ensure_ascii=False)
    except:
        pass


# ============================================================
#  邮件
# ============================================================
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


# ============================================================
#  HTML 报告生成
# ============================================================
def generate_html(all_papers, any_fallback=False):
    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日")
    total = sum(len(v) for v in all_papers.values())

    # 统计
    today_count = sum(1 for papers in all_papers.values() for p in papers if not p.get("is_fallback"))
    fb_count = sum(1 for papers in all_papers.values() for p in papers if p.get("is_fallback"))

    zone_colors = {
        "1区": "#e74c3c", "2区": "#e67e22", "3区": "#7f8c8d", "4区": "#bdc3c7",
        "预印本": "#3498db",
    }
    zone_badges = {
        "1区": "🏆 1区", "2区": "🥈 2区", "3区": "🥉 3区", "4区": "4区",
        "预印本": "📝 预印本",
    }
    topic_colors = {
        "🧬 生物材料": "#27ae60", "🖥️ 医学影像与AI": "#2980b9",
        "🧫 组织工程与再生医学": "#8e44ad", "🧠 神经工程与脑机接口": "#e74c3c",
        "💊 纳米医学与药物递送": "#f39c12", "📟 生物传感器与可穿戴": "#1abc9c",
        "✂️ 基因编辑与合成生物学": "#e67e22", "🤖 AI+药物发现": "#3498db",
        "📄 arXiv预印本": "#7f8c8d",
    }

    # 按分区排序：1区 > 2区 > 3区 > 4区 > 预印本
    def sort_key(topic_papers):
        zone_order = {"1区": 0, "2区": 1, "3区": 2, "4区": 3, "预印本": 4}
        # 取该topic下第一篇的分区作为排序依据（每个topic下再各自排序）
        return 99

    sections = ""
    for topic, papers in all_papers.items():
        if not papers:
            continue

        # 每个topic内按分区排序
        papers_sorted = sorted(papers, key=lambda p: {
            "1区": 0, "2区": 1, "3区": 2, "4区": 3, "预印本": 4, None: 5
        }.get(p.get("zone"), 5))

        c = topic_colors.get(topic, "#333")

        # 统计分区分布
        zone1 = sum(1 for p in papers_sorted if p.get("zone") == "1区")
        zone2 = sum(1 for p in papers_sorted if p.get("zone") == "2区")
        zone_count_str = ""
        if zone1 > 0:
            zone_count_str += f'<span style="background:#e74c3c;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;margin-left:4px;">1区×{zone1}</span>'
        if zone2 > 0:
            zone_count_str += f'<span style="background:#e67e22;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;margin-left:2px;">2区×{zone2}</span>'

        sections += f'<div style="margin:20px 0 10px;"><h3 style="color:{c};border-left:4px solid {c};padding-left:10px;margin:0;">{topic} <span style="font-size:14px;color:#999;">({len(papers_sorted)}篇)</span>{zone_count_str}</h3></div>'

        for p in papers_sorted:
            zone = p.get("zone")
            zone_color = zone_colors.get(zone, "#999") if zone else "#999"
            zone_badge = zone_badges.get(zone, "") if zone else ""

            # 分区标签
            zone_tag = ""
            if zone:
                zone_tag = f'<span style="display:inline-block;background:{zone_color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;margin-left:6px;">{zone_badge}</span>'

            # 回退标记（本周精选）
            fb_tag = ""
            if p.get("is_fallback"):
                fb_tag = ' <span style="display:inline-block;background:#6c5ce7;color:#fff;padding:2px 6px;border-radius:3px;font-size:10px;margin-left:4px;">🔄 本周</span>'

            # 期刊简称
            abbr_str = p.get("journal_abbr", p["journal"])[:35]

            sections += f"""
<div style="margin:10px 0;padding:14px;background:#f8f9fa;border-radius:8px;border-left:3px solid {zone_color if zone else c};">
<div style="display:flex;align-items:flex-start;justify-content:space-between;">
    <div style="flex:1;">
        <div style="font-weight:bold;font-size:15px;margin-bottom:4px;line-height:1.4;color:#2c3e50;">
            <a href="{p['url']}" style="color:#2c3e50;text-decoration:none;" target="_blank">{p['title_zh']}</a>
        </div>
        <div style="color:#888;font-size:11px;margin-bottom:8px;">
            <span style="color:#555;font-weight:600;">{abbr_str}</span>
            {zone_tag}{fb_tag}
            <span style="margin-left:6px;">{p.get('date','')}</span>
            <span style="margin-left:6px;">{p['authors']}</span>
        </div>
        <div style="background:#fff;padding:8px 10px;border-radius:4px;font-size:13px;color:#444;line-height:1.6;border:1px solid #eee;">
            <span style="color:{c};font-weight:bold;">📌 总结：</span>{p['summary']}
        </div>
        <div style="color:#aaa;font-size:11px;line-height:1.3;margin-top:6px;">
            <em>原标题：{p['title_en'][:180]}{'...' if len(p.get('title_en',''))>180 else ''}</em>
        </div>
    </div>
</div>
</div>"""

    # 无内容时
    if total == 0:
        sections = """
<div style="text-align:center;padding:40px;color:#999;">
    <div style="font-size:48px;margin-bottom:10px;">📭</div>
    <div style="font-size:16px;">今日暂无该领域最新论文</div>
    <div style="font-size:12px;margin-top:8px;">PubMed数据库可能存在1-2天延迟，请明天再查看</div>
</div>"""

    # 总体统计
    zone1_total = sum(1 for papers in all_papers.values() for p in papers if p.get("zone") == "1区")
    zone2_total = sum(1 for papers in all_papers.values() for p in papers if p.get("zone") == "2区")

    stats = ""
    if zone1_total > 0 or zone2_total > 0:
        stats = f'<div style="text-align:center;font-size:12px;color:#666;margin:8px 0;">🏆 1区 {zone1_total} 篇 | 🥈 2区 {zone2_total} 篇 | 总计 {total} 篇</div>'

    # 标题区 — 根据是否有回退动态调整
    period_desc = ""
    if any_fallback:
        if today_count > 0:
            period_desc = f"📅 当日 {today_count} 篇 + 🔄 本周精选 {fb_count} 篇"
        else:
            period_desc = f"🔄 今日暂无更新，展示本周精选 {fb_count} 篇"
    else:
        period_desc = f"📅 当日发表 {today_count} 篇"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei','PingFang SC',sans-serif;max-width:750px;margin:0 auto;padding:20px;color:#333;background:#f0f2f5;">
<div style="background:#fff;border-radius:12px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.06);">

<div style="text-align:center;padding-bottom:16px;border-bottom:2px solid #2c3e50;margin-bottom:10px;">
    <h1 style="color:#1a1a1a;margin:0 0 6px;font-size:22px;">🔬 生物医学工程 · 前沿日报</h1>
    <p style="color:#999;margin:0;font-size:13px;">{today_str} · {period_desc} · 含中科院分区 & 总结要点</p>
</div>

{stats}

<div style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 16px;justify-content:center;">
{''.join(f'<span style="background:{topic_colors.get(t,"#999")};color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;">{t}:{len(p)}</span>' for t, p in all_papers.items() if p)}
</div>

{sections}

<div style="background:#eaf2f8;padding:12px;border-left:4px solid #2980b9;margin:20px 0 0;border-radius:4px;font-size:12px;line-height:1.6;">
<strong>📌 说明</strong><br>
• 📅 <strong>当日发表</strong> 为今天正式出版的最新论文 · 来源 PubMed / arXiv<br>
• 🔄 <strong>本周精选</strong> 为当日无更新时自动回退近7天的高质量论文<br>
• <span style="color:#e74c3c;">🏆 1区</span> / <span style="color:#e67e22;">🥈 2区</span> 为中科院期刊分区（2025年升级版，大类）<br>
• 中文标题由术语替换生成，总结要点由规则引擎自动提炼 · 仅供参考，请以原文为准
</div>

<div style="background:#fff3cd;padding:10px;border-left:4px solid #ffc107;margin:10px 0 0;border-radius:4px;font-size:12px;">
<strong>⚠️ 免责声明</strong> 本报告由自动化系统生成，仅用于学术信息追踪，不构成任何建议。
</div>

</div>
<p style="text-align:center;color:#bbb;font-size:11px;margin-top:12px;">BME前沿日报 · 每日自动推送 · 仅当日最新</p>
</body></html>"""


# ============================================================
#  主流程
# ============================================================
def main():
    print("===== BME 前沿日报 =====")
    print(f"日期: {date.today()}")
    cache = load_cache()
    all_papers = {}
    any_fallback = False
    today_count = 0
    fallback_count = 0

    for topic, query in TOPICS.items():
        print(f"\n[{topic}]")
        papers, is_fallback = fetch_pubmed(query, 4, days=7)
        new_papers = [p for p in papers if p["pmid"] not in cache["pmids"]]
        if new_papers:
            all_papers[topic] = new_papers
            for p in new_papers:
                cache["pmids"].append(p["pmid"])
                zone_str = f" [{p.get('zone','')}]" if p.get("zone") else ""
                fb = " [回退]" if p.get("is_fallback") else ""
                print(f"  {p['journal_abbr'][:25]}{zone_str}{fb} → {p['title_zh'][:60]}...")
                if p.get("is_fallback"):
                    fallback_count += 1
                    any_fallback = True
                else:
                    today_count += 1
        else:
            print(f"  无新论文（近一周也无）")
        time.sleep(1)

    # arXiv
    print("\n[arXiv] 生物医学工程...")
    arxiv, arxiv_fb = fetch_arxiv("biomedical OR tissue engineering OR medical imaging OR drug delivery OR biosensor", 3)
    new_arxiv = [p for p in arxiv if p["pmid"] not in cache["pmids"]]
    if new_arxiv:
        all_papers["📄 arXiv预印本"] = new_arxiv
        for p in new_arxiv:
            cache["pmids"].append(p["pmid"])
            fb = " [回退]" if p.get("is_fallback") else ""
            print(f"  arXiv{fb} → {p['title_zh'][:60]}...")
            if p.get("is_fallback"):
                fallback_count += 1
                any_fallback = True
            else:
                today_count += 1
    if arxiv_fb:
        any_fallback = True
    print(f"  arXiv: {len(new_arxiv)} 篇")

    total = sum(len(v) for v in all_papers.values())
    zone1 = sum(1 for papers in all_papers.values() for p in papers if p.get("zone") == "1区")
    zone2 = sum(1 for papers in all_papers.values() for p in papers if p.get("zone") == "2区")
    print(f"\n总计: {total} 篇 (1区: {zone1}, 2区: {zone2}, 今日: {today_count}, 回退: {fallback_count})")

    html = generate_html(all_papers, any_fallback)
    period = "今日" if not any_fallback else "今日+本周精选"
    subject = f"🔬 BME前沿 - {date.today().strftime('%Y-%m-%d')} ({period}, 共{total}篇, 1区{zone1}篇)"
    ok = send_email(subject, html)
    print(f"邮件: {'✅' if ok else '❌'}")

    save_cache(cache)
    print("完成")


if __name__ == "__main__":
    main()
