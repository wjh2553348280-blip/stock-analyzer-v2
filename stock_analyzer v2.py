import streamlit as st
import requests
from datetime import datetime, timedelta
import json
import re
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===== 核心配置 =====
FINNHUB_KEY = "d7qvc0pr01qtpsm0hhggd7qvc0pr01qtpsm0hhh0"
DEEPSEEK_KEY = "sk-c7476186e5ee4b408281db4d620489be"

# ===== 页面样式：华尔街专业投研风格 =====
st.set_page_config(page_title="证券量化研报终端", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    /* 全局背景：浅灰白 */
    .main { background-color: #f7f9fc; color: #1a202c; }

    /* 顶部标题与文本 */
    h1, h2, h3 { color: #1e3a8a; font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }

    /* 指标卡片：白底深色字 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* 报告卡片：专业排版 */
    .report-card {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        line-height: 1.8;
        font-size: 1.1rem;
        color: #2d3748;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }

    /* 按钮：海军蓝 */
    .stButton>button {
        background-color: #1e3a8a;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.6rem 2rem;
        border: none;
    }
    .stButton>button:hover { background-color: #172554; border: none; }
    </style>
    """, unsafe_allow_html=True)

# ===== 财务指标中文映射表 =====
METRIC_LABEL_MAP = {
    "peNormalizedAnnual": "市盈率 (PE)",
    "epsNormalizedAnnual": "每股收益 (EPS)",
    "roeTTM": "净资产收益率 (ROE)",
    "grossMarginTTM": "销售毛利率",
    "netProfitMarginTTM": "销售净利率",
    "52WeekHigh": "52周最高价",
    "52WeekLow": "52周最低价",
    "totalDebt/totalEquityAnnual": "资产负债率",
    "dividendYieldIndicatedAnnual": "年度股息率"
}


# ===== 数据抓取引擎 =====
def fetch_market_data(ticker):
    """抓取核心行情与基本面数据"""
    p = requests.get(f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={FINNHUB_KEY}",
                     verify=False).json()
    q = requests.get(f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}", verify=False).json()
    m = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={FINNHUB_KEY}",
                     verify=False).json()

    today = datetime.now().strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    n = requests.get(
        f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={month_ago}&to={today}&token={FINNHUB_KEY}",
        verify=False).json()

    return p, q, m.get("metric", {}), n[:5]


def generate_professional_report(ticker, data):
    """生成专家级投资研报"""
    prompt = f"""
    角色：证券投研部首席分析师
    任务：针对 {ticker} 提供深度投资评级研报。

    分析数据：{json.dumps(data, ensure_ascii=False)}

    撰写规范：
    1. 严禁出现“AI”、“模型”或“助理”字眼。
    2. 使用严谨的金融术语，如：资产负债表质量、内生增长动能、估值锚点、流动性溢价。
    3. 报告结构：
       - 【商业模式分析】：深挖行业竞争格局与核心护城河。
       - 【财务数据透视】：剖析盈利能力、现金流状态及当前估值合理性。
       - 【风险与机会评估】：分析近期资讯对市场预期的边际影响。
       - 【投资策略指引】：给出清晰的买入/持有/卖出逻辑。
    4. 评分规范：报告最后一行必须写“最终评分：X.X”（评分范围0-10）。
    """

    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.25},
        verify=False
    )
    return resp.json()["choices"][0]["message"]["content"]


# ===== 界面交互流程 =====
st.title("🏛️ 证券分析量化终端")
st.markdown("**使命：赋能专业分析，洞察数据背后的投资逻辑。**")
st.divider()

# 输入区域
with st.container():
    c1, c2 = st.columns([4, 1])
    with c1:
        ticker = st.text_input("请输入美股股票代码", placeholder="例如: NVDA",
                               label_visibility="collapsed").upper().strip()
    with c2:
        btn_start = st.button("开始深度研报分析", use_container_width=True)

if btn_start and ticker:
    # 状态加载动画（圈圈转动）
    with st.status("正在初始化分析引擎...", expanded=True) as status:
        try:
            status.write("正在连接全球行情中心...")
            profile, quote, metrics, news = fetch_market_data(ticker)

            if not profile.get("name"):
                st.error("无法识别的证券代码，请核对后输入。")
                st.stop()

            status.write("正在构建财务因子模型...")
            time.sleep(0.5)

            status.write("分析师正在生成投资建议报告...")
            # 整理传递给引擎的数据
            context = {
                "公司名称": profile.get("name"),
                "当前股价": quote.get("c"),
                "今日涨跌": f"{quote.get('dp')}%",
                "核心财务指标": {k: metrics.get(k, "N/A") for k in METRIC_LABEL_MAP.keys()},
                "近期关联资讯": [n.get("headline") for n in news]
            }

            # 生成报告
            full_content = generate_professional_report(ticker, context)

            # 完成后关闭状态框
            status.update(label="研报生成完毕", state="complete", expanded=False)

            # --- 全部结果一次性展示 ---
            st.divider()

            # 1. 顶部核心指标
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("当前成交价", f"${quote.get('c')}")
            m2.metric("日内涨跌幅", f"{quote.get('dp')}%", delta=f"{quote.get('dp')}%")
            m3.metric("动态市盈率", f"{metrics.get('peNormalizedAnnual', 'N/A'):.2f}")
            m4.metric("总市值", f"${profile.get('marketCapitalization', 0) / 1000:.2f}B")

            # 2. 醒目的评分牌（居中设计）
            score_match = re.search(r"最终评分：\s*(\d+(\.\d+)?)", full_content)
            score = float(score_match.group(1)) if score_match else 5.0

            # 定义评分视觉反馈
            if score >= 7.5:
                s_color, s_label = "#10b981", "超配 / 买入"
            elif score >= 5.0:
                s_color, s_label = "#f59e0b", "中性 / 持有"
            else:
                s_color, s_label = "#ef4444", "减配 / 卖出"

            st.markdown(f"""
                <div style="background-color: #f8fafc; border: 2px solid {s_color}; padding: 30px; border-radius: 15px; text-align: center; margin: 30px 0;">
                    <div style="color: #64748b; text-transform: uppercase; letter-spacing: 2px; font-weight: bold;">量化评估分值</div>
                    <div style="color: {s_color}; font-size: 4rem; font-weight: 800; margin: 10px 0;">{score}</div>
                    <div style="background-color: {s_color}; color: white; display: inline-block; padding: 5px 20px; border-radius: 20px; font-weight: bold; font-size: 1.2rem;">{s_label}</div>
                </div>
            """, unsafe_allow_html=True)

            # 3. 研报正文展示
            # 去除结尾的评分行
            clean_text = re.sub(r"最终评分：.*", "", full_content).strip()
            st.markdown('<div class="report-card">', unsafe_allow_html=True)
            st.markdown(f"### {profile.get('name')}（{ticker}）投资价值分析报告")
            st.markdown(clean_text)
            st.markdown('</div>', unsafe_allow_html=True)

            # 4. 辅助数据展示
            st.write("")
            with st.expander("点击查看完整财务因子清单与关联资讯"):
                col_left, col_right = st.columns(2)
                with col_left:
                    st.subheader("底层财务指标")
                    for k, label in METRIC_LABEL_MAP.items():
                        val = metrics.get(k, "N/A")
                        st.write(f"**{label}**: {val}")
                with col_right:
                    st.subheader("最新关联动态")
                    for n in news:
                        st.caption(f"· {n.get('headline')}")

        except Exception as e:
            st.error(f"分析引擎发生技术故障: {str(e)}")

elif btn_start and not ticker:
    st.warning("操作中止：请先输入有效的股票代码。")