# -*- coding: utf-8 -*-
import streamlit as st
import os
import json
import sqlite3
from datetime import datetime
import importlib.metadata

# PDF 生成相关库 (ReportLab 工业级排版引擎)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

# 引入 Google Gemini AI SDK
import google.generativeai as genai

# ==========================================
# 0. 运行时第三方依赖包版本探测器 (新增调试核心)
# ==========================================
def get_library_versions():
    """
    动态检测当前运行环境中加载的第三方包真实版本，防范云端缓存导致的版本滞后
    """
    packages = ["streamlit", "google-generativeai", "reportlab", "protobuf", "pypdf"]
    versions = {}
    for pkg in packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except Exception:
            # 兼容：如果 importlib 无法捕获，使用模块内置魔术属性兜底
            if pkg == "protobuf":
                try:
                    import google.protobuf
                    versions[pkg] = google.protobuf.__version__
                except Exception:
                    versions[pkg] = "未检出"
            elif pkg == "google-generativeai":
                try:
                    import google.generativeai as genai_module
                    versions[pkg] = genai_module.__version__
                except Exception:
                    versions[pkg] = "未检出"
            else:
                versions[pkg] = "未检出"
    return versions

# ==========================================
# 1. 初始化中文字体与本地数据库
# ==========================================
try:
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
except Exception as e:
    pass

DB_FILE = "market_reports.db"

def init_db():
    """初始化本地 SQLite 数据库，用于持久化 PDF 报告"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            country TEXT NOT NULL,
            created_at TEXT NOT NULL,
            pdf_data BLOB NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# 初始化数据库
init_db()

# ==========================================
# 2. ReportLab 自动页码与高保真页眉页脚 (NumberedCanvas)
# ==========================================
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        if self._pageNumber == 1:
            # 封面页绘制左侧深蓝高端修饰条
            self.saveState()
            self.setFillColor(colors.HexColor('#1B365D'))
            self.rect(0, 0, 15, 841.89, fill=True, stroke=False)
            self.restoreState()
            return

        self.saveState()
        self.setFont("STSong-Light", 8.5)
        self.setFillColor(colors.HexColor('#64748B'))

        # 页眉分割线与系统标题
        self.drawString(54, 785, "亚马逊跨国市场智能研究报告中心")
        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.5)
        self.line(54, 775, 541.27, 775)

        # 页脚页码与行业保密声明
        page_text = f"第 {self._pageNumber} 页 / 共 {page_count} 页"
        self.drawRightString(541.27, 40, page_text)
        self.drawString(54, 40, "系统自动生成报告 | 跨境电商 AI 智能决策中心")
        self.line(54, 52, 541.27, 52)
        
        self.restoreState()

# ==========================================
# 3. 核心功能：PDF 出版级报告编译引擎
# ==========================================
def compile_pdf_report(product, country, data):
    """动态解析 AI 结构化 JSON 并通过 ReportLab 渲染为高保真 PDF 字节流"""
    os.makedirs("/tmp", exist_ok=True)
    filename = f"/tmp/{product}_{country}_report.pdf"
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    story = []
    
    # 样式表精细定义
    cover_title_style = ParagraphStyle('CoverTitle', fontName='STSong-Light', fontSize=22, leading=28, alignment=1, textColor=colors.white)
    cover_subtitle_style = ParagraphStyle('CoverSubtitle', fontName='STSong-Light', fontSize=12, leading=18, alignment=1, textColor=colors.HexColor('#475569'), spaceBefore=25, spaceAfter=140)
    cover_meta_style = ParagraphStyle('CoverMeta', fontName='STSong-Light', fontSize=10, leading=16, alignment=1, textColor=colors.HexColor('#64748B'))
    h1_style = ParagraphStyle('CN_H1', fontName='STSong-Light', fontSize=15, leading=20, textColor=colors.HexColor('#1B365D'), spaceBefore=20, spaceAfter=10, keepWithNext=True)
    h2_style = ParagraphStyle('CN_H2', fontName='STSong-Light', fontSize=11, leading=16, textColor=colors.HexColor('#0F172A'), spaceBefore=12, spaceAfter=6, keepWithNext=True)
    body_style = ParagraphStyle('CN_Body', fontName='STSong-Light', fontSize=9.5, leading=15, textColor=colors.HexColor('#334155'), spaceBefore=4, spaceAfter=10)
    cell_header_style = ParagraphStyle('CellHeader', fontName='STSong-Light', fontSize=8.5, leading=11, textColor=colors.white, alignment=1)
    cell_body_style = ParagraphStyle('CellBody', fontName='STSong-Light', fontSize=8, leading=11, textColor=colors.HexColor('#1E293B'))
    cell_body_center_style = ParagraphStyle('CellBodyCenter', fontName='STSong-Light', fontSize=8, leading=11, alignment=1, textColor=colors.HexColor('#1E293B'))

    # --- 封面页 ---
    story.append(Spacer(1, 40))
    title_p = Paragraph(f"<b>亚马逊【{product}】行业<br/>{country}市场品牌科学分析报告</b>", cover_title_style)
    banner_table = Table([[title_p]], colWidths=[487.27])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1B365D')),
        ('TOPPADDING', (0,0), (-1,-1), 40),
        ('BOTTOMPADDING', (0,0), (-1,-1), 40),
        ('LEFTPADDING', (0,0), (-1,-1), 20),
        ('RIGHTPADDING', (0,0), (-1,-1), 20),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(banner_table)
    
    subtitle_p = Paragraph("基于BSR、评论动量与自然SoV的跨国市场多维比较与智能筛选", cover_subtitle_style)
    story.append(subtitle_p)

    story.append(Paragraph(f"<b>研究对象：</b> 亚马逊【{country}】商城 {product} 类目", cover_meta_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>生成时间：</b> {datetime.now().strftime('%Y年%m月%d日')}", cover_meta_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>数据算法依据：</b> BSR排位模型、评论动量模型、Organic Share of Voice (SoV)", cover_meta_style))
    story.append(PageBreak())

    # --- 第一部分：方法论 ---
    story.append(Paragraph("第一部分：数据分析方法与逻辑依据", h1_style))
    story.append(Paragraph(data.get("methodology", "暂无分析方法论描述。"), body_style))
    story.append(PageBreak())

    # --- 第二部分：Top 10 品牌表格 ---
    story.append(Paragraph(f"第二部分：【{country}】市场 Top 10 品牌深度剖析", h1_style))
    
    # 动态填入 Top 10 表格数据
    table_content = [
        [
            Paragraph("<b>排名</b>", cell_header_style),
            Paragraph("<b>品牌名称</b>", cell_header_style),
            Paragraph("<b>核心产品线</b>", cell_header_style),
            Paragraph("<b>目标客群定位</b>", cell_header_style),
            Paragraph("<b>核心竞争力及上榜理由</b>", cell_header_style)
        ]
    ]
    
    for brand in data.get("top_brands", []):
        table_content.append([
            Paragraph(str(brand.get("rank", "")), cell_body_center_style),
            Paragraph(f"<b>{brand.get('brand_name', '')}</b>", cell_body_style),
            Paragraph(brand.get("products", ""), cell_body_style),
            Paragraph(brand.get("target_audience", ""), cell_body_style),
            Paragraph(brand.get("reasons", ""), cell_body_style)
        ])
    
    t_brands = Table(table_content, colWidths=[25, 65, 95, 95, 207.27], repeatRows=1)
    t_brands.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1B365D')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAFC'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(t_brands)
    story.append(PageBreak())

    # --- 第三部分：跨国市场差异对比 ---
    story.append(Paragraph("第三部分：美、德/跨国多维度差异对比", h1_style))
    
    comp_content = [
        [
            Paragraph("<b>对比维度</b>", cell_header_style),
            Paragraph("<b>美国站点 (Amazon US) 偏好</b>", cell_header_style),
            Paragraph(f"<b>目标站点 ({country}) 偏好</b>", cell_header_style)
        ]
    ]
    
    for diff in data.get("market_differences", []):
        comp_content.append([
            Paragraph(f"<b>{diff.get('dimension', '')}</b>", cell_body_style),
            Paragraph(diff.get("us_preference", ""), cell_body_style),
            Paragraph(diff.get("target_preference", ""), cell_body_style)
        ])
        
    t_comp = Table(comp_content, colWidths=[80, 203, 204.27], repeatRows=1)
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1B365D')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAFC'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 15))

    # --- 第四部分：实战启示 ---
    story.append(Paragraph("第四部分：对跨境供应链与卖家的实战启示", h1_style))
    for i, insight in enumerate(data.get("actionable_insights", [])):
        story.append(Paragraph(f"<b>{i+1}. {insight.get('title', '')}</b>", h2_style))
        story.append(Paragraph(insight.get("detail", ""), body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    
    with open(filename, "rb") as f:
        pdf_bytes = f.read()
    
    try:
        os.remove(filename)
    except:
        pass
        
    return pdf_bytes

# ==========================================
# 5. 2.0+ 现代大脑：Gemini 市场结构化扫描器
# ==========================================
def call_gemini_analysis(product, country, model_name, api_key):
    """
    【2.0+时代专用版】直连 Google 官方标准 'google_search' 实现在线接地。
    要求 google-generativeai>=0.8.3。抛弃所有历史包袱。
    """
    if not api_key:
        raise ValueError("未配置有效的 GEMINI_API_KEY，请在侧边栏或 Secrets 中进行配置。")
        
    genai.configure(api_key=api_key)

    # 1. 2.0+ 世代模型统一使用最新标准工具接口，格式必须为 list of dict，防客户端拦截报错
    tools_config = [{"google_search": {}}]

    prompt = f"""
    请你首先使用 google_search 工具，在互联网上实时检索亚马逊【{country}】站点关于【{product}】类目的最新 BSR（Best Sellers）榜单、2026最新品牌数据。
    
    重点关注：
    - 该国市场该类目前10名最活跃、销量最高、或评论累计最多的真实品牌。
    - 针对这些品牌的真实核心产品线、目标人群进行整合。
    - 检索该国对于该产品特殊的环保合规政策、消费者对材质/设计本土化的真实偏好。
    
    数据检索完毕后，严格按照以下 JSON 模式（Schema）输出，禁止包含任何 markdown 标记（如 ```json），只输出纯 JSON 字符串：
    {{
        "methodology": "请写一段约150字到200字的科学筛选依据，阐述你如何通过实时谷歌搜索检索到的 BSR 排位、评论权重和自然搜索占有率（SoV）三者动态加权，排除大促噪点进行真实实力评定。",
        "top_brands": [
            {{
                "rank": 1,
                "brand_name": "检索到的真实品牌名",
                "products": "该品牌的真实主打产品线（不超过20字）",
                "target_audience": "该品牌的真实核心目标买家群体（不超过20字）",
                "reasons": "结合检索到的最新数据，分析其2026年上榜的硬核理由（不超过80字）"
            }}
            // ... 输出 Top 1 到 Top 10 的品牌
        ],
        "market_differences": [
            {{
                "dimension": "尺寸与空间适配倾向",
                "us_preference": "美国消费者的真实偏好细节及原因（基于检索数据）",
                "target_preference": "该国家市场消费者的真实偏好细节及原因"
            }},
            {{
                "dimension": "审美风格与配色细节",
                "us_preference": "美国家庭对于该产品外观、颜色的偏好（基于检索数据）",
                "target_preference": "该国家市场对该产品外观、颜色、设计的本土偏好"
            }},
            {{
                "dimension": "认证与环保合规准入",
                "us_preference": "美国主流的阻燃或基础化学无毒认证要求（如加州CA117）",
                "target_preference": "该国极其严格的生态准入门槛（如德国的OEKO-TEX, 欧盟REACH等）以及消费者对劣质化学味道的抗拒习惯"
            }}
        ],
        "actionable_insights": [
            {{
                "title": "研发创新建议（Differentiated R&D）",
                "detail": "基于上述对比，针对此产品，中国供应链在材质、环保或多功能设计上面向该国买家痛点如何进行差异化开发。"
            }},
            {{
                "title": "货盘与高压缩率包装优化",
                "detail": "结合海运运费与尾程仓储，如何进行高弹性、高压缩比包装开发从而节省 30%-50% 的物流仓储成本，并且指导不同国家尺寸配比备货。"
            }}
        ]
    }}
    """
    
    # 2. 直接实例化 2.x/2.5 模型并调用
    model = genai.GenerativeModel(
        model_name=model_name,
        tools=tools_config
    )
    response = model.generate_content(prompt)
    clean_text = response.text.strip()
            
    # 解析并验证返回内容是否为合格 JSON
    if clean_text.startswith("```"):
        clean_text = clean_text.split("```")[1]
        if clean_text.startswith("json"):
            clean_text = clean_text[4:]
    
    return json.loads(clean_text)

# ==========================================
# 6. 动态获取可用模型 (自动过滤老旧 1.x 代模型)
# ==========================================
def get_available_models(api_key):
    """
    根据当前的 API Key，动态调用 Google list_models 接口获取真实的可用模型。
    自动过滤掉 1.0、1.5 等老旧历史模型，只呈现 2.0+ / 2.5 / 3.0+ 等现代高智能模型。
    """
    # 2.0+ 时代默认精选高能模型
    fallback_models = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash"
    ]
    if not api_key:
        return fallback_models
    try:
        genai.configure(api_key=api_key)
        raw_models = genai.list_models()
        valid_models = []
        for m in raw_models:
            if 'generateContent' in m.supported_generation_methods:
                model_id = m.name.replace("models/", "")
                # 排除 1.0, 1.5 系列，保留 2.0 及更高代际
                if "gemini" in model_id.lower() and not any(v in model_id for v in ["1.0", "1.5"]):
                    valid_models.append(model_id)
        
        if valid_models:
            valid_models.sort()
            # 优先推荐 2.5 系列
            primary_recommends = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]
            for rec in reversed(primary_recommends):
                if rec in valid_models:
                    valid_models.remove(rec)
                    valid_models.insert(0, rec)
            return valid_models
    except Exception as e:
        pass
    return fallback_models

# ==========================================
# 7. Streamlit GUI 交互控制台
# ==========================================
st.set_page_config(page_title="亚马逊多国市场品牌智能分析系统", layout="wide")

st.title("🛡️ 2026 亚马逊跨国市场 brand 智能分析系统 (Gemini 2.x/2.5+ 重构版)")
st.write("输入任意品类与目的国商城，一键启动 AI 级多维度 BSR 评论动量模型评估，并直接编译为**出版级 PDF 报告**。")

# --- 侧边栏：API 凭证、动态模型感知与环境诊断 ---
with st.sidebar:
    st.header("🔑 API 凭证与模型状态")
    
    default_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    
    api_key_input = st.text_input(
        "请输入您的 Google AI Studio API Key：",
        value=default_key,
        type="password",
        help="建议配置在 Streamlit Secrets 中。"
    )
    
    active_key = api_key_input.strip() if api_key_input else ""
    
    if active_key:
        st.success("🟢 API 密钥已就绪")
        
        with st.spinner("🔄 正在动态扫描您账户权限内的 Gemini 2.x+ 模型列表..."):
            available_models = get_available_models(active_key)
            
        st.caption("✨ **已动态读取以下可用模型：**")
        st.code("\n".join(available_models[:12]) + ("\n..." if len(available_models) > 12 else ""))
    else:
        st.error("🔴 未检测到有效的 API 密钥，请在上方输入或部署 Secrets。")
        available_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]

    # ------------------ 新增：动态包版本调试面板 ------------------
    st.divider()
    with st.expander("⚙️ 运行时第三方库版本诊断"):
        st.caption("以下为云端服务器当前实际加载的依赖版本，可用于快速排除 Protobuf 校验冲突。")
        runtime_versions = get_library_versions()
        for pkg_name, pkg_ver in runtime_versions.items():
            # 特殊标注出 google-generativeai，如果低于 0.8.3 将发出黄色警告提示
            if pkg_name == "google-generativeai":
                if pkg_ver != "未检出" and pkg_ver < "0.8.3":
                    st.warning(f"⚠️ **{pkg_name}**: `{pkg_ver}` (建议 >=0.8.3)")
                    continue
            st.write(f"🔹 **{pkg_name}**: `{pkg_ver}`")
    # -------------------------------------------------------------

st.divider()

col1, col2 = st.columns([1, 2])

with col1:
    st.header("🔍 新建市场分析")
    
    with st.form("analysis_form"):
        product_input = st.text_input("产品中文名称：", value="狗床", help="例如：狗床、猫爬架等")
        country_select = st.selectbox(
            "选择亚马逊目的国商城：",
            ["德国 (Amazon DE)", "美国 (Amazon US)", "日本 (Amazon JP)", "英国 (Amazon UK)", "法国 (Amazon FR)", "意大利 (Amazon IT)"]
        )
        
        model_select = st.selectbox(
            "选择已授权的 Gemini 2.x/2.5+ 驱动模型：",
            options=available_models,
            help="此处的列表是由您的 API Key 权限实时动态拉取的最新一代模型。"
        )
        
        submit_btn = st.form_submit_button("📊 运行智能分析 & 生成PDF")
        
    if submit_btn:
        if not active_key:
            st.error("❌ 无法分析：侧边栏未检测到 API 密钥，请配置！")
        elif not product_input:
            st.error("❌ 无法分析：请输入产品中文名称！")
        else:
            with st.spinner(f"🚀 正在使用模型 【{model_select}】 抓取多节点BSR，扫描评论动量并运行 SoV AI 分析中...请耐心等待"):
                try:
                    report_data = call_gemini_analysis(product_input, country_select, model_name=model_select, api_key=active_key)
                    pdf_bytes = compile_pdf_report(product_input, country_select, report_data)
                    
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO reports (product_name, country, created_at, pdf_data) VALUES (?, ?, ?, ?)",
                        (product_input, country_select, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pdf_bytes)
                    )
                    conn.commit()
                    conn.close()
                    
                    st.success(f"🎉 报告生成并归档成功！品类：{product_input} | 商城：{country_select}")
                    
                    st.download_button(
                        label=f"⬇️ 立即下载报告 PDF",
                        data=pdf_bytes,
                        file_name=f"Amazon_{product_input}_{country_select}_Report_2026.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    error_msg = str(e)
                    st.error(f"分析失败！\n\n**错误信息：** {error_msg}")

with col2:
    st.header("🗂️ 历史分析报告归档（随时下载）")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, product_name, country, created_at FROM reports ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        st.info("暂无历史分析记录。请在左侧输入内容并点击“运行智能分析”。")
    else:
        for row in rows:
            rep_id, prod, country, t_stamp = row
            col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
            with col_b1:
                st.write(f"📁 **品类：** {prod} ({country})")
            with col_b2:
                st.caption(f"⏱️ {t_stamp}")
            with col_b3:
                def get_bytes(r_id):
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("SELECT pdf_data FROM reports WHERE id=?", (r_id,))
                    res = cursor.fetchone()[0]
                    conn.close()
                    return res
                
                st.download_button(
                    label="📥 下载 PDF",
                    data=get_bytes(rep_id),
                    file_name=f"Amazon_{prod}_{country}_Report_2026.pdf",
                    mime="application/pdf",
                    key=f"dl_{rep_id}"
                )
            st.divider()
