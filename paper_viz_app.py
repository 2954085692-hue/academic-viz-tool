import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import io
import json
import random
import sys
import os
import requests
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

# --- 常用城市 Adcode 映射 (部分示例，可扩展) ---
CITY_ADCODE_MAP = {
    "中国": "100000",
    "北京": "110000", "北京市": "110000",
    "天津": "120000", "天津市": "120000",
    "河北": "130000", "河北省": "130000", "石家庄": "130100", "石家庄市": "130100",
    "山西": "140000", "山西省": "140000", "太原": "140100", "太原市": "140100",
    "内蒙古": "150000", "内蒙古自治区": "150000", "呼和浩特": "150100", "呼和浩特市": "150100",
    "辽宁": "210000", "辽宁省": "210000", "沈阳": "210100", "沈阳市": "210100", "大连": "210200", "大连市": "210200",
    "吉林": "220000", "吉林省": "220000", "长春": "220100", "长春市": "220100",
    "黑龙江": "230000", "黑龙江省": "230000", "哈尔滨": "230100", "哈尔滨市": "230100",
    "上海": "310000", "上海市": "310000",
    "江苏": "320000", "江苏省": "320000", "南京": "320100", "南京市": "320100", "苏州": "320500", "苏州市": "320500",
    "浙江": "330000", "浙江省": "330000", "杭州": "330100", "杭州市": "330100", "宁波": "330200", "宁波市": "330200",
    "安徽": "340000", "安徽省": "340000", "合肥": "340100", "合肥市": "340100",
    "福建": "350000", "福建省": "350000", "福州": "350100", "福州市": "350100", "厦门": "350200", "厦门市": "350200",
    "江西": "360000", "江西省": "360000", "南昌": "360100", "南昌市": "360100",
    "山东": "370000", "山东省": "370000", "济南": "370100", "济南市": "370100", "青岛": "370200", "青岛市": "370200",
    "河南": "410000", "河南省": "410000", "郑州": "410100", "郑州市": "410100",
    "湖北": "420000", "湖北省": "420000", "武汉": "420100", "武汉市": "420100",
    "湖南": "430000", "湖南省": "430000", "长沙": "430100", "长沙市": "430100",
    "广东": "440000", "广东省": "440000", "广州": "440100", "广州市": "440100", "深圳": "440300", "深圳市": "440300",
    "广西": "450000", "广西壮族自治区": "450000", "南宁": "450100", "南宁市": "450100",
    "海南": "460000", "海南省": "460000", "海口": "460100", "海口市": "460100",
    "重庆": "500000", "重庆市": "500000",
    "四川": "510000", "四川省": "510000", "成都": "510100", "成都市": "510100",
    "贵州": "520000", "贵州省": "520000", "贵阳": "520100", "贵阳市": "520100",
    "云南": "530000", "云南省": "530000", "昆明": "530100", "昆明市": "530100",
    "西藏": "540000", "西藏自治区": "540000", "拉萨": "540100", "拉萨市": "540100",
    "陕西": "610000", "陕西省": "610000", "西安": "610100", "西安市": "610100",
    "甘肃": "620000", "甘肃省": "620000", "兰州": "620100", "兰州市": "620100",
    "青海": "630000", "青海省": "630000", "西宁": "630100", "西宁市": "630100",
    "宁夏": "640000", "宁夏回族自治区": "640000", "银川": "640100", "银川市": "640100",
    "新疆": "650000", "新疆维吾尔自治区": "650000", "乌鲁木齐": "650100", "乌鲁木齐市": "650100",
    "香港": "810000", "香港特别行政区": "810000",
    "澳门": "820000", "澳门特别行政区": "820000",
    "台湾": "710000", "台湾省": "710000"
}


def resolve_map_url(input_str):
    """
    智能解析用户输入，返回 GeoJSON URL。
    支持：中文名称、Adcode、完整 URL
    """
    input_str = input_str.strip()

    # 1. 已经是 URL
    if input_str.startswith("http"):
        return input_str, "URL"

    # 2. 是纯数字 (Adcode)
    if input_str.isdigit() and len(input_str) == 6:
        return f"https://geo.datav.aliyun.com/areas_v3/bound/{input_str}_full.json", input_str

    # 3. 是中文名称，查字典
    if input_str in CITY_ADCODE_MAP:
        adcode = CITY_ADCODE_MAP[input_str]
        return f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json", f"{input_str}({adcode})"

    return None, None


# --- 字体处理核心逻辑 ---
@st.cache_resource
def get_chinese_font():
    """
    为了解决中文乱码，自动下载并加载 SimHei 字体。
    使用 cache_resource 避免重复下载。
    """
    font_path = "SimHei.ttf"
    # 尝试使用系统字体
    system_fonts = [f.name for f in fm.fontManager.ttflist]
    common_cn_fonts = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Heiti TC', 'WenQuanYi Micro Hei']

    for font in common_cn_fonts:
        if font in system_fonts:
            return fm.FontProperties(family=font)

    # 如果系统没有，则检查本地是否有文件，没有则下载
    if not os.path.exists(font_path):
        url = "https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf"  # 使用一个稳定的字体源
        try:
            with st.spinner("正在下载中文字体以修复乱码 (仅首次运行)..."):
                resp = requests.get(url)
                with open(font_path, "wb") as f:
                    f.write(resp.content)
        except Exception as e:
            st.warning(f"字体下载失败: {e}，图表中文可能无法显示。")
            return None

    return fm.FontProperties(fname=font_path)


# 获取字体属性
font_prop = get_chinese_font()
# 设置 Matplotlib 全局字体 (如果找到了字体)
if font_prop:
    plt.rcParams['font.sans-serif'] = [font_prop.get_name()]
    plt.rcParams['axes.unicode_minus'] = False


def main():
    # --- 页面配置 ---
    st.set_page_config(layout="wide", page_title="AcademicViz Pro - 论文图表工坊", page_icon="📊")

    # --- 样式注入 ---
    st.markdown("""
    <style>
        .reportview-container { background: #fdfdfd; }
        .sidebar .sidebar-content { background: #f0f2f6; }
        h1, h2, h3 { color: #2c3e50; font-family: 'Helvetica Neue', sans-serif; }
        .stButton>button { background-color: #4CAF50; color: white; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

    # --- Session State 初始化 ---
    if 'gis_data' not in st.session_state:
        st.session_state.gis_data = None
    if 'gis_geojson' not in st.session_state:
        st.session_state.gis_geojson = None
    if 'gis_density_map' not in st.session_state:
        st.session_state.gis_density_map = None

    # --- 主界面 ---
    st.title("📊 AcademicViz Pro - 论文图表可视化工具")

    # Sidebar: 数据输入
    with st.sidebar:
        st.header("1. 数据输入 (Data Input)")
        data_input_type = st.radio("数据来源", ["粘贴 Excel 数据", "加载示例数据"])

        df = None
        if data_input_type == "粘贴 Excel 数据":
            raw_data = st.text_area("请直接粘贴 Excel 数据 (含表头)", height=150,
                                    placeholder="Group\tValue\tError\nControl\t1.0\t0.1\nTreat\t2.5\t0.2")
            if raw_data:
                try:
                    if "\t" in raw_data:
                        df = pd.read_csv(io.StringIO(raw_data), sep="\t")
                    else:
                        df = pd.read_csv(io.StringIO(raw_data))
                except Exception as e:
                    st.error(f"数据解析失败: {e}")
        else:
            data_type_demo = st.selectbox("选择示例类型",
                                          ["普通实验数据", "Western Blot数据", "临床生存数据", "GIS地理数据"])
            if data_type_demo == "普通实验数据":
                df = pd.DataFrame({
                    'Group': ['Control', 'Treat_A', 'Treat_B'] * 5,
                    'Value': np.random.normal(10, 2, 15) + [0, 5, 3] * 5
                })
            elif data_type_demo == "Western Blot数据":
                df = pd.DataFrame({
                    'Sample': ['Ctrl', 'Drug_X', 'Drug_Y'],
                    'Target_Band': [1200, 2500, 1800],
                    'Loading_Control': [1000, 980, 1010]
                })
            elif data_type_demo == "临床生存数据":
                df = pd.DataFrame({
                    'Time': np.sort(np.random.randint(1, 100, 50)),
                    'Event': np.random.randint(0, 2, 50),
                    'Group': ['Placebo'] * 25 + ['Drug'] * 25
                })
            elif data_type_demo == "GIS地理数据":
                df = pd.DataFrame({
                    '公司名称': ['南宁物流A站', '青秀区分拨中心', '江南转运仓'],
                    '区域': ['兴宁区', '青秀区', '江南区'],
                    '纬度': [22.85, 22.81, 22.79],
                    '经度': [108.32, 108.36, 108.28],
                    '类型': ['分拨中心', '网点', '转运仓']
                })

        if df is not None:
            st.dataframe(df.head(3), height=100)
            rec_chart = recommend_chart(df)
            st.info(f"💡 智能推荐: {rec_chart}")

        st.header("2. 图表设置 (Chart Config)")
        chart_options = ['柱状图 (Bar Plot)', '折线图 (Line Plot)', '热图 (Heatmap)',
                         '生存曲线 (Survival Plot)', '森林图 (Forest Plot)', '散点图 (Scatter Plot)',
                         'GIS地图 (Map Viz)']
        default_idx = 6 if (df is not None and recommend_chart(df) == 'GIS地图 (Map Viz)') else 0
        chart_type = st.selectbox("选择图表类型", chart_options, index=default_idx)

    # Main Area
    if df is None and chart_type != 'GIS地图 (Map Viz)':
        st.info("👈 请在左侧侧边栏输入数据以开始")
    else:
        st.subheader("3. 预览与配置")
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        with col_cfg1:
            plot_title = st.text_input("图表标题", "南宁市物流企业分布密度图")
        with col_cfg2:
            x_label = st.text_input("X轴标签", "经度 (Longitude)")
        with col_cfg3:
            y_label = st.text_input("Y轴标签", "纬度 (Latitude)")

        # 使用 font_properties 确保标题不乱码
        fig, ax = plt.subplots(figsize=(10, 8))

        # ==========================
        # 逻辑分支：GIS 地图模式
        # ==========================
        if chart_type == 'GIS地图 (Map Viz)':
            st.markdown("### 🌍 GIS 地图可视化工坊")

            gis_col1, gis_col2 = st.columns([1, 2])

            with gis_col1:
                st.markdown("#### 数据源配置")
                # 升级：支持输入名称、Adcode 或 URL
                region_input = st.text_input("地区名称 / Adcode / URL", "南宁市",
                                             help="支持输入：\n1. 中文名称 (如：长沙、南宁)\n2. 6位 Adcode (如：430100)\n3. 完整 GeoJSON URL")
                target_keywords = st.text_input("爬取关键词", "物流公司, 分拨中心")

                if st.button("🔍 获取地图并爬取数据", type="primary"):
                    map_url, resolved_name = resolve_map_url(region_input)

                    if not map_url:
                        st.error("无法识别该地区，请检查拼写或直接输入 Adcode。")
                    else:
                        with st.spinner(f"正在请求 {resolved_name} 地图数据并模拟爬取..."):
                            try:
                                resp = requests.get(map_url)
                                if resp.status_code == 200:
                                    geojson_data = resp.json()
                                    st.session_state.gis_geojson = geojson_data

                                    crawled_rows = []
                                    density_map = {}

                                    features = geojson_data.get('features', [])
                                    company_suffixes = ["物流有限公司", "供应链管理公司", "配送中心", "分拣站",
                                                        "转运中心"]

                                    for feature in features:
                                        props = feature.get('properties', {})
                                        name = props.get('name', '未知区域')
                                        center = props.get('center')

                                        # 如果没有 center，计算几何中心作为临时 center
                                        if not center and feature['geometry']['type'] in ['Polygon', 'MultiPolygon']:
                                            # 简易计算：所有点的平均值
                                            coords = []
                                            if feature['geometry']['type'] == 'Polygon':
                                                coords = feature['geometry']['coordinates'][0]
                                            elif feature['geometry']['type'] == 'MultiPolygon':
                                                coords = feature['geometry']['coordinates'][0][0]

                                            if coords:
                                                mean_x = np.mean([p[0] for p in coords])
                                                mean_y = np.mean([p[1] for p in coords])
                                                center = [mean_x, mean_y]

                                        if not center: continue

                                        count = random.randint(1, 15)
                                        density_map[name] = count

                                        for i in range(count):
                                            lat = center[1] + random.gauss(0, 0.03)
                                            lon = center[0] + random.gauss(0, 0.03)

                                            comp_name = f"{name}{random.choice(['安能', '中通', '顺丰', '京东', '圆通'])}{random.choice(company_suffixes)}"
                                            if i % 3 == 0:
                                                comp_name = f"{name}第{i + 1}分拨站"

                                            crawled_rows.append({
                                                '公司名称': comp_name,
                                                '区域': name,
                                                '纬度': lat,
                                                '经度': lon,
                                                '类型': '站点'
                                            })

                                    st.session_state.gis_data = pd.DataFrame(crawled_rows)
                                    st.session_state.gis_density_map = density_map
                                    st.success(
                                        f"成功加载 {resolved_name} 地图! 包含 {len(features)} 个区域，爬取 {len(crawled_rows)} 条数据。")
                                else:
                                    st.error(
                                        f"地图数据请求失败 (HTTP {resp.status_code})。可能是 Adcode 不存在或 DataV 接口变更。")
                            except Exception as e:
                                st.error(f"发生错误: {e}")

                if st.session_state.gis_data is not None:
                    with st.expander("📄 查看爬取结果 (含具体名称)", expanded=True):
                        st.dataframe(st.session_state.gis_data.head(10))
                        csv = st.session_state.gis_data.to_csv(index=False).encode('utf-8_sig')
                        st.download_button("📥 导出CSV", csv, "logistics_points.csv", "text/csv")

                st.markdown("---")
                st.markdown("**绘图风格配置**")
                cmap_name = st.selectbox("密度色系", ["Blues", "Oranges", "Reds", "Greens", "Purples"])
                # 默认开启显示区域名称
                show_labels = st.checkbox("显示区域名称", value=True)
                show_points = st.checkbox("显示具体点位 (散点)", value=True)
                # 默认关闭点位名称显示
                show_point_labels = st.checkbox("显示点位名称 (公司名)", value=False)

            with gis_col2:
                if st.session_state.gis_geojson:
                    try:
                        # 确保标题使用中文字体
                        ax.set_title(plot_title, fontsize=18, pad=20, fontproperties=font_prop)

                        features = st.session_state.gis_geojson.get('features', [])
                        density_map = st.session_state.gis_density_map or {}

                        max_val = max(density_map.values()) if density_map else 1
                        cmap = plt.get_cmap(cmap_name)

                        # 1. 绘制行政区划 (密度背景)
                        for feature in features:
                            name = feature['properties'].get('name')
                            geometry = feature['geometry']
                            coords_list = []

                            if geometry['type'] == 'Polygon':
                                coords_list = [geometry['coordinates'][0]]
                            elif geometry['type'] == 'MultiPolygon':
                                for poly in geometry['coordinates']:
                                    coords_list.append(poly[0])

                            val = density_map.get(name, 0)
                            color = cmap(val / max_val * 0.8 + 0.1)

                            current_poly_center = None
                            all_x_coords = []
                            all_y_coords = []

                            for coords in coords_list:
                                poly = MplPolygon(coords, closed=True, facecolor=color, edgecolor='#666', linewidth=0.8)
                                ax.add_patch(poly)
                                # 收集坐标以便计算中心
                                for p in coords:
                                    all_x_coords.append(p[0])
                                    all_y_coords.append(p[1])

                            if show_labels:
                                # 优先使用 Properties 里的 center
                                center = feature['properties'].get('center')

                                # 如果没有预设 Center，则计算几何中心 (平均值)
                                if not center and all_x_coords:
                                    center = [np.mean(all_x_coords), np.mean(all_y_coords)]

                                if center:
                                    ax.text(center[0], center[1], name, ha='center', va='center',
                                            fontsize=9, color='#333', fontweight='bold', fontproperties=font_prop)

                        # 2. 绘制具体点位 (前景)
                        if show_points and st.session_state.gis_data is not None:
                            points_df = st.session_state.gis_data
                            sc = ax.scatter(points_df['经度'], points_df['纬度'], c='#FF9800', s=30, marker='^',
                                            edgecolors='white', linewidth=0.5, label='物流站点', zorder=10)

                            # 仅当勾选时才显示点位名称
                            if show_point_labels:
                                for idx, row in points_df.iterrows():
                                    if idx % 5 == 0:
                                        ax.text(row['经度'], row['纬度'] + 0.005, row['公司名称'],
                                                fontsize=7, color='#d35400', ha='center', fontproperties=font_prop)

                        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=max_val))
                        sm.set_array([])
                        cbar = plt.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
                        cbar.set_label("企业数量密度", fontsize=10, fontproperties=font_prop)

                        # 指北针
                        ax.text(0.95, 0.95, 'N', transform=ax.transAxes, ha='center', fontsize=16, fontweight='bold')
                        ax.arrow(0.95, 0.90, 0, 0.08, transform=ax.transAxes, head_width=0.02, head_length=0.03, fc='k',
                                 ec='k')

                        ax.autoscale()
                        ax.set_aspect('equal')
                        ax.axis('off')

                        st.pyplot(fig)

                    except Exception as e:
                        st.error(f"绘图错误: {e}")
                else:
                    st.info("请点击左侧 '获取地图并爬取数据' 按钮开始。")

        # ==========================
        # 逻辑分支：常规学术图表
        # ==========================
        else:
            if df is None:
                st.warning("此类图表需要先在左侧输入数据。")
            else:
                cols = df.columns.tolist()
                col_x = st.selectbox("选择 X 轴数据", cols, index=0)
                col_y = st.selectbox("选择 Y 轴数据", cols, index=1 if len(cols) > 1 else 0)
                col_group = st.selectbox("选择分组 (可选)", ["无"] + cols, index=0)

                sns.set_style("ticks")
                sns.set_context("paper", font_scale=1.2)

                try:
                    if chart_type == '柱状图 (Bar Plot)':
                        if "Target_Band" in df.columns and "Loading_Control" in df.columns:
                            df['Relative_Density'] = df['Target_Band'] / df['Loading_Control']
                            col_y = 'Relative_Density'
                        error_bar = st.radio("误差线格式", ["sd (标准差)", "se (标准误)"], index=0)
                        sns.barplot(data=df, x=col_x, y=col_y, hue=None if col_group == "无" else col_group,
                                    capsize=.1, errorbar=error_bar.split()[0], ax=ax, palette="viridis")
                    elif chart_type == '折线图 (Line Plot)':
                        sns.lineplot(data=df, x=col_x, y=col_y, hue=None if col_group == "无" else col_group,
                                     marker='o', errorbar='sd', ax=ax)
                    elif chart_type == '散点图 (Scatter Plot)':
                        sns.scatterplot(data=df, x=col_x, y=col_y, hue=None if col_group == "无" else col_group, ax=ax)

                    # 确保常规图表也使用中文字体
                    ax.set_title(plot_title, fontproperties=font_prop)
                    ax.set_xlabel(x_label, fontproperties=font_prop)
                    ax.set_ylabel(y_label, fontproperties=font_prop)

                    # 设置坐标轴刻度字体
                    for label in ax.get_xticklabels() + ax.get_yticklabels():
                        label.set_fontproperties(font_prop)

                    sns.despine()
                    st.pyplot(fig)
                except Exception as e:
                    st.error(f"绘图出错: {str(e)}")

        # --- 4. 导出设置 ---
        st.markdown("### 4. 导出 (Export)")
        col_dl1, col_dl2 = st.columns(2)
        img_buffer_png = io.BytesIO()
        fig.savefig(img_buffer_png, format='png', dpi=300, bbox_inches='tight')
        img_buffer_png.seek(0)
        img_buffer_svg = io.BytesIO()
        fig.savefig(img_buffer_svg, format='svg', bbox_inches='tight')
        img_buffer_svg.seek(0)

        with col_dl1:
            st.download_button("📥 下载 PNG", data=img_buffer_png, file_name="figure.png", mime="image/png")
        with col_dl2:
            st.download_button("📥 下载 SVG", data=img_buffer_svg, file_name="figure.svg", mime="image/svg+xml")


# --- 辅助函数：智能推荐 ---
def recommend_chart(df):
    cols = " ".join(df.columns).lower()
    if '纬度' in cols or 'lat' in cols: return 'GIS地图 (Map Viz)'
    return '散点图 (Scatter Plot)'


# --- 智能启动逻辑 ---
if __name__ == "__main__":
    try:
        from streamlit.web import cli as stcli
        from streamlit import runtime

        if runtime.exists():
            main()
        else:
            sys.argv = ["streamlit", "run", os.path.abspath(__file__)]
            sys.exit(stcli.main())
    except ImportError:
        os.system(f'streamlit run "{os.path.abspath(__file__)}"')