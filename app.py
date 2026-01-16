import streamlit as st
import pandas as pd
from datetime import date, datetime
from sqlalchemy import create_engine, text
from io import BytesIO

# ✅ PDF (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

# ----------------------------
# CONFIG UI
# ----------------------------
st.set_page_config(
    page_title="Controle de Compras",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------
# ✅ LIMPEZA SEGURA (ANTES DOS WIDGETS)
# ----------------------------
if st.session_state.get("_limpar_form"):
    for k in ["comprador", "fornecedor", "cidade_destino", "data_compra"]:
        st.session_state.pop(k, None)

    i = 0
    while True:
        ki = f"item_{i}"
        kq = f"qtd_{i}"
        if ki not in st.session_state and kq not in st.session_state:
            break
        st.session_state.pop(ki, None)
        st.session_state.pop(kq, None)
        i += 1

    st.session_state["qtd_itens"] = 1
    st.session_state.pop("remover_idx", None)
    st.session_state["_limpar_form"] = False

# -----------------------------
# CSS (com destaque no formulário)
# -----------------------------
CSS = """
<style>
  header[data-testid="stHeader"]{display:none;}
  [data-testid="stAppViewContainer"]{padding-top:0!important;margin-top:0!important;overflow-x:hidden!important;}
  .block-container{padding-top:0.8rem!important;padding-bottom:1.2rem!important;max-width:1200px!important;}
  html, body, [class*="css"]{font-size:13px!important;}

  .stApp{
    background: radial-gradient(circle at 30% 10%, #f7e9ff 0%, #f6f7ff 35%, #f3f6ff 100%);
  }

  section[data-testid="stSidebar"]{
    background: linear-gradient(180deg, #2b2f88 0%, #1f2a6d 55%, #14204f 100%);
  }
  section[data-testid="stSidebar"] *{color:#fff!important;}

  /* ===== TEXTO PRETO DENTRO DOS CAMPOS DA SIDEBAR ===== */
  section[data-testid="stSidebar"] input,
  section[data-testid="stSidebar"] textarea,
  section[data-testid="stSidebar"] input::placeholder,
  section[data-testid="stSidebar"] textarea::placeholder,
  section[data-testid="stSidebar"] .stDateInput input {
    color: #000 !important;
    -webkit-text-fill-color: #000 !important; /* ajuda no Chrome */
    font-weight: 700 !important;
  }

  /* Selectbox (valor selecionado) */
  section[data-testid="stSidebar"] div[data-baseweb="select"] * {
    color: #000 !important;
    -webkit-text-fill-color: #000 !important;
  }

  /* Opções do dropdown (quando abre) — às vezes fica fora da sidebar */
  div[role="listbox"] * {
    color: #000 !important;
  }

  section[data-testid="stSidebar"] input,
  section[data-testid="stSidebar"] .stDateInput input,
  section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"]{
    background: rgba(255,255,255,0.10) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 12px !important;
    color: #fff !important; /* cor geral, mas é sobrescrita acima nos campos */
  }

  .h-title{font-size:34px;font-weight:900;margin:0;color:#1f2a44;}
  .h-sub{margin-top:6px;color:#5a6780;}

  .metric-row{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:16px;
    margin-top:18px;
  }
  .metric-card{
    background: linear-gradient(180deg, #2b2f88 0%, #1b2462 100%);
    border-radius:14px;
    padding:14px 16px;
    box-shadow:0 10px 22px rgba(0,0,0,0.18);
    border:1px solid rgba(255,255,255,0.10);
  }
  .metric-label{color:rgba(255,255,255,0.75);font-size:13px;}
  .metric-value{color:#fff;font-size:20px;font-weight:900;margin-top:6px;}

  .panel{
    background: rgba(255,255,255,0.88);
    border: 1px solid rgba(100,120,170,0.20);
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 24px rgba(20,30,70,0.10);
    margin-bottom: 14px;
  }
  .panel-title{
    font-size:22px;
    font-weight:900;
    color:#4b46ff;
    display:flex;
    align-items:center;
    gap:10px;
    margin-bottom:10px;
  }

  .stTextInput label,
  .stNumberInput label,
  .stDateInput label,
  .stSelectbox label{
    color:#1f2433 !important;
    font-weight:800 !important;
    opacity:1 !important;
  }

  .stTextInput input,
  .stNumberInput input,
  .stDateInput input{
    background:#ffffff !important;
    color:#000000 !important;
    font-weight:700 !important;
    border: 1.5px solid rgba(60,70,170,0.35) !important;
    border-radius: 12px !important;
  }

  .stTextInput input:focus,
  .stNumberInput input:focus,
  .stDateInput input:focus{
    border: 2px solid #5a55ff !important;
    box-shadow: 0 0 0 4px rgba(90,85,255,0.15) !important;
  }

  .stButton>button{
    border-radius:12px;
    padding:0.55rem 0.95rem;
    font-weight:800;
  }

  div[data-testid="stDataFrame"]{border-radius:14px;overflow:hidden;}
  div[data-testid="stVerticalBlockBorderWrapper"]{background:transparent!important;border:0!important;box-shadow:none!important;}
  div[data-testid="stVerticalBlock"] > div:empty{display:none!important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------
# DB (SQLite)
# ----------------------------
engine = create_engine("sqlite:///compras.db", future=True)

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comprador TEXT NOT NULL,
            data_compra TEXT NOT NULL,
            fornecedor TEXT NOT NULL,
            cidade_destino TEXT NOT NULL,
            item TEXT NOT NULL,
            quantidade REAL NOT NULL,
            criado_em TEXT NOT NULL
        );
        """))

def inserir_compra(comprador, data_compra, fornecedor, cidade_destino, item, quantidade):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO compras (comprador, data_compra, fornecedor, cidade_destino, item, quantidade, criado_em)
                VALUES (:comprador, :data_compra, :fornecedor, :cidade_destino, :item, :quantidade, :criado_em)
            """),
            {
                "comprador": comprador.strip(),
                "data_compra": str(data_compra),
                "fornecedor": fornecedor.strip(),
                "cidade_destino": cidade_destino.strip(),
                "item": item.strip(),
                "quantidade": float(quantidade),
                "criado_em": datetime.now().isoformat(timespec="seconds"),
            }
        )

def deletar_compra(compra_id: int):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM compras WHERE id = :id"), {"id": compra_id})

def carregar_df():
    with engine.connect() as conn:
        df_ = pd.read_sql(text("SELECT * FROM compras ORDER BY data_compra DESC, id DESC"), conn)
    if not df_.empty:
        df_["data_compra"] = pd.to_datetime(df_["data_compra"]).dt.date
        df_["criado_em"] = pd.to_datetime(df_["criado_em"])
    return df_

init_db()
df = carregar_df()

# ----------------------------
# PDF helper
# ----------------------------
def gerar_pdf_pedido(
    *,
    numero_pedido: str,
    data_pedido: date,
    cnpj_faturamento: str,
    solicitante: str,
    fornecedor: str,
    destino: str,
    observacoes: str,
    itens_df: pd.DataFrame,
) -> bytes:
    """
    Gera PDF bonito (A4) com cabeçalho azul e tabela de itens.
    itens_df precisa ter colunas: Material, Quantidade
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Pedido de Compra",
        author="Sistema de Compras",
    )

    styles = getSampleStyleSheet()
    azul_escuro = colors.HexColor("#1f2a6d")
    azul_medio = colors.HexColor("#2b2f88")
    cinza_txt = colors.HexColor("#334155")

    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=azul_escuro,
        spaceAfter=10,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=azul_escuro,
        leading=13,
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=cinza_txt,
        leading=13,
    )

    elements = []

    elements.append(Paragraph("PEDIDO DE COMPRA", title_style))

    # Bloco de informações (2 colunas)
    info_rows = [
        [Paragraph("Nº do pedido:", label_style), Paragraph(numero_pedido or "-", value_style),
         Paragraph("Data:", label_style), Paragraph(data_pedido.strftime("%d/%m/%Y"), value_style)],
        [Paragraph("CNPJ faturamento:", label_style), Paragraph(cnpj_faturamento or "-", value_style),
         Paragraph("Solicitante:", label_style), Paragraph(solicitante or "-", value_style)],
        [Paragraph("Fornecedor:", label_style), Paragraph(fornecedor or "-", value_style),
         Paragraph("Destino (cidade):", label_style), Paragraph(destino or "-", value_style)],
    ]
    info_table = Table(info_rows, colWidths=[32*mm, 63*mm, 28*mm, 55*mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    if observacoes and observacoes.strip():
        obs = observacoes.strip().replace("\n", "<br/>")
        elements.append(Paragraph("Observações:", label_style))
        elements.append(Paragraph(obs, value_style))
        elements.append(Spacer(1, 10))

    # Tabela de itens
    data = [[
        Paragraph("<b>Material</b>", ParagraphStyle("h", parent=value_style, textColor=colors.white)),
        Paragraph("<b>Quantidade</b>", ParagraphStyle("h2", parent=value_style, textColor=colors.white)),
    ]]

    for _, r in itens_df.iterrows():
        material = str(r.get("Material", "")).strip()
        qtd = r.get("Quantidade", "")
        data.append([Paragraph(material, value_style), Paragraph(str(qtd), value_style)])

    t = Table(data, colWidths=[130*mm, 35*mm])

    t_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), azul_medio),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])

    # zebra striping
    for i in range(1, len(data)):
        bg = colors.whitesmoke if i % 2 == 1 else colors.HexColor("#eef2ff")
        t_style.add("BACKGROUND", (0, i), (-1, i), bg)

    t.setStyle(t_style)
    elements.append(t)

    doc.build(elements)
    return buf.getvalue()

# ----------------------------
# HEADER
# ----------------------------
st.markdown(
    """
    <div style="display:flex;gap:14px;align-items:center;">
      <div style="font-size:44px;">🧾</div>
      <div>
        <div class="h-title">Controle de Compras</div>
        <div class="h-sub">Registre compras e gere pedido ao fornecedor em PDF.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------
# ✅ ABAS
# ----------------------------
tab_controle, tab_pdf = st.tabs(["🧾 Controle de Compras", "🧾 Gerar pedido (PDF)"])

# ======================================================================
# ABA 1 - CONTROLE
# ======================================================================
with tab_controle:
    # ----------------------------
    # SIDEBAR (Filtros)
    # ----------------------------
    st.sidebar.header("🔎 Filtros")
    compradores = sorted(df["comprador"].unique().tolist()) if not df.empty else []
    fornecedores = sorted(df["fornecedor"].unique().tolist()) if not df.empty else []

    f_comprador = st.sidebar.selectbox("Comprador", ["(Todos)"] + compradores)
    f_fornecedor = st.sidebar.selectbox("Fornecedor", ["(Todos)"] + fornecedores)

    st.sidebar.divider()
    st.sidebar.header("📅 Período")
    col_a, col_b = st.sidebar.columns(2)
    data_ini = col_a.date_input("De", value=None, format="DD/MM/YYYY")
    data_fim = col_b.date_input("Até", value=None, format="DD/MM/YYYY")

    df_f = df.copy()
    if not df_f.empty:
        if f_comprador != "(Todos)":
            df_f = df_f[df_f["comprador"] == f_comprador]
        if f_fornecedor != "(Todos)":
            df_f = df_f[df_f["fornecedor"] == f_fornecedor]
        if data_ini is not None:
            df_f = df_f[df_f["data_compra"] >= data_ini]
        if data_fim is not None:
            df_f = df_f[df_f["data_compra"] <= data_fim]

    # ----------------------------
    # KPIs
    # ----------------------------
    total_registros = len(df_f)
    total_itens = float(df_f["quantidade"].sum()) if not df_f.empty else 0.0
    forn_unicos = df_f["fornecedor"].nunique() if not df_f.empty else 0
    itens_unicos = df_f["item"].nunique() if not df_f.empty else 0

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-label">Registros</div>
        <div class="metric-value">{total_registros}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Quantidade total</div>
        <div class="metric-value">{total_itens:g}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Fornecedores</div>
        <div class="metric-value">{forn_unicos}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Itens únicos</div>
        <div class="metric-value">{itens_unicos}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ----------------------------
    # LAYOUT
    # ----------------------------
    col_left, col_right = st.columns([1.55, 1.0], gap="large")

    # ============================
    # ESQUERDA - FORM
    # ============================
    with col_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">➕ Lançar compra</div>', unsafe_allow_html=True)

        if "qtd_itens" not in st.session_state:
            st.session_state.qtd_itens = 1

        with st.form("form_compra", clear_on_submit=False):
            c1, c2 = st.columns(2)

            comprador = c1.text_input("Comprador", placeholder="Ex.: Nathalia / Chefe", key="comprador")
            data_compra = c2.date_input(
                "Data do pedido",
                value=st.session_state.get("data_compra", date.today()),
                key="data_compra",
                format="DD/MM/YYYY",
            )

            fornecedor = st.text_input("Fornecedor", placeholder="Ex.: Fornecedor X", key="fornecedor")
            cidade_destino = st.text_input("Cidade destino", placeholder="Ex.: São Paulo / RJ / Belo Horizonte", key="cidade_destino")

            st.markdown('<div class="panel-title" style="font-size:22px;margin-top:10px;">Itens</div>', unsafe_allow_html=True)

            itens = []
            quantidades = []

            for i in range(st.session_state.qtd_itens):
                i1, i2 = st.columns([2.2, 1.0])

                item = i1.text_input(f"Item {i+1}", placeholder="Ex.: Cabo de rede, toner, etc.", key=f"item_{i}")
                qtd = i2.number_input(f"Qtd {i+1}", min_value=0.0, step=1.0, key=f"qtd_{i}")

                itens.append(item)
                quantidades.append(qtd)

            salvar = st.form_submit_button("Salvar", type="primary")

        # ===== BOTÕES EMBAIXO (fora do form) =====
        b1, b2, b3 = st.columns([1, 1, 1])

        if b1.button("➕ Adicionar item", use_container_width=True):
            st.session_state.qtd_itens += 1
            st.rerun()

        if "remover_idx" not in st.session_state:
            st.session_state.remover_idx = 1

        st.session_state.remover_idx = b2.selectbox(
            "Remover item",
            options=list(range(1, st.session_state.qtd_itens + 1)),
            index=min(st.session_state.remover_idx - 1, st.session_state.qtd_itens - 1),
            label_visibility="collapsed",
        )

        if b3.button("🗑️ Remover", use_container_width=True):
            idx = st.session_state.remover_idx - 1

            st.session_state.pop(f"item_{idx}", None)
            st.session_state.pop(f"qtd_{idx}", None)

            for j in range(idx + 1, st.session_state.qtd_itens):
                st.session_state[f"item_{j-1}"] = st.session_state.pop(f"item_{j}", "")
                st.session_state[f"qtd_{j-1}"] = st.session_state.pop(f"qtd_{j}", 0.0)

            st.session_state.qtd_itens = max(1, st.session_state.qtd_itens - 1)
            st.rerun()

        # ===== SALVAR =====
        if salvar:
            erros = False

            if not str(st.session_state.get("comprador", "")).strip():
                erros = True
            if not str(st.session_state.get("fornecedor", "")).strip():
                erros = True
            if not str(st.session_state.get("cidade_destino", "")).strip():
                erros = True

            for item, qtd in zip(itens, quantidades):
                if not str(item).strip() or float(qtd) <= 0:
                    erros = True

            if erros:
                st.error("Preencha comprador, fornecedor, cidade destino e todos os itens com quantidade maior que 0.")
            else:
                for item, qtd in zip(itens, quantidades):
                    inserir_compra(
                        st.session_state["comprador"],
                        st.session_state["data_compra"],
                        st.session_state["fornecedor"],
                        st.session_state["cidade_destino"],
                        item,
                        qtd,
                    )

                st.success("Compra salva!")
                st.session_state["_limpar_form"] = True
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ============================
    # DIREITA
    # ============================
    with col_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">📋 Compras</div>', unsafe_allow_html=True)

        if df_f.empty:
            st.info("Sem registros para mostrar com os filtros atuais.")
        else:
            st.dataframe(
                df_f[["id", "comprador", "data_compra", "fornecedor", "cidade_destino", "item", "quantidade", "criado_em"]],
                use_container_width=True,
                hide_index=True,
                height=220,
            )

        st.markdown('</div>', unsafe_allow_html=True)

        # ----------------------------
        # ✅ EXPORTAR PARA EXCEL
        # ----------------------------
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">⬇️ Exportar</div>', unsafe_allow_html=True)

        if df_f.empty:
            st.info("Sem dados para exportar com os filtros atuais.")
        else:
            df_xlsx = df_f.rename(columns={
                "comprador": "Comprador",
                "data_compra": "Data do pedido",
                "fornecedor": "Fornecedor",
                "cidade_destino": "Cidade destino",
                "item": "Item",
                "quantidade": "Quantidade",
            })[["Comprador", "Data do pedido", "Fornecedor", "Cidade destino", "Item", "Quantidade"]].copy()

            df_xlsx["Data do pedido"] = pd.to_datetime(df_xlsx["Data do pedido"]).dt.strftime("%d/%m/%Y")

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_xlsx.to_excel(writer, index=False, sheet_name="Compras")
                ws = writer.sheets["Compras"]
                ws.column_dimensions["A"].width = 18
                ws.column_dimensions["B"].width = 16
                ws.column_dimensions["C"].width = 28
                ws.column_dimensions["D"].width = 22
                ws.column_dimensions["E"].width = 30
                ws.column_dimensions["F"].width = 12

            st.download_button(
                "📥 Baixar Excel",
                data=output.getvalue(),
                file_name="compras.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.markdown('</div>', unsafe_allow_html=True)

        # ----------------------------
        # Excluir
        # ----------------------------
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">🗑️ Excluir um registro</div>', unsafe_allow_html=True)

        if df_f.empty:
            st.info("Sem registros para excluir.")
        else:
            id_del = st.number_input("ID para excluir", min_value=1, step=1)
            if st.button("Excluir", type="secondary"):
                deletar_compra(int(id_del))
                st.success("Registro excluído!")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# ======================================================================
# ABA 2 - ✅ GERAR PEDIDO (PDF)
# ======================================================================
with tab_pdf:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">🧾 Gerar pedido de compra (PDF)</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("Ainda não há compras lançadas para gerar um pedido.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Seletores para puxar itens lançados
        c1, c2, c3 = st.columns(3)
        fornecedor_sel = c1.selectbox("Fornecedor", sorted(df["fornecedor"].unique().tolist()))
        cidade_base = c2.selectbox("Destino (cidade) - baseado nos lançamentos", sorted(df["cidade_destino"].unique().tolist()))
        comprador_padrao = c3.selectbox("Solicitante (padrão)", sorted(df["comprador"].unique().tolist()))

        c4, c5, c6 = st.columns(3)
        periodo_ini = c4.date_input("Considerar lançamentos - De", value=None, format="DD/MM/YYYY")
        periodo_fim = c5.date_input("Considerar lançamentos - Até", value=None, format="DD/MM/YYYY")
        data_pedido = c6.date_input("Data do pedido (PDF)", value=date.today(), format="DD/MM/YYYY")

        st.markdown("<hr/>", unsafe_allow_html=True)

        # Campos manuais
        c7, c8, c9 = st.columns(3)
        numero_pedido = c7.text_input("Nº do pedido (opcional)", placeholder="Ex.: PC-2026-001")
        cnpj_faturamento = c8.text_input("CNPJ de faturamento (manual)", placeholder="00.000.000/0001-00")
        solicitante = c9.text_input("Nome do solicitante (manual)", value=comprador_padrao)

        destino_manual = st.text_input("Destino (cidade) - no PDF (manual)", value=cidade_base)
        observacoes = st.text_area("Observações (opcional)", placeholder="Ex.: Entregar até dia X, faturar para CNPJ Y, etc.", height=90)

        # Filtra base do pedido
        base = df.copy()
        base = base[(base["fornecedor"] == fornecedor_sel) & (base["cidade_destino"] == cidade_base)]
        if periodo_ini is not None:
            base = base[base["data_compra"] >= periodo_ini]
        if periodo_fim is not None:
            base = base[base["data_compra"] <= periodo_fim]

        if base.empty:
            st.warning("Não encontrei lançamentos com esse fornecedor/destino (e período). Ajuste os filtros.")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            # Agrupa itens somando quantidades
            pedido_df = (
                base.groupby("item", as_index=False)["quantidade"]
                .sum()
                .rename(columns={"item": "Material", "quantidade": "Quantidade"})
                .sort_values("Material")
                .reset_index(drop=True)
            )

            st.write("**Itens do pedido (você pode editar antes de gerar o PDF):**")
            pedido_edit = st.data_editor(
                pedido_df,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
            )

            # Validação simples
            def _pedido_ok(df_items: pd.DataFrame) -> bool:
                if df_items is None or df_items.empty:
                    return False
                if "Material" not in df_items.columns or "Quantidade" not in df_items.columns:
                    return False
                for _, r in df_items.iterrows():
                    if not str(r.get("Material", "")).strip():
                        return False
                    try:
                        if float(r.get("Quantidade", 0)) <= 0:
                            return False
                    except Exception:
                        return False
                return True

            if not _pedido_ok(pedido_edit):
                st.error("Revise os itens: 'Material' não pode ficar vazio e 'Quantidade' precisa ser maior que 0.")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                pdf_bytes = gerar_pdf_pedido(
                    numero_pedido=numero_pedido.strip(),
                    data_pedido=data_pedido,
                    cnpj_faturamento=cnpj_faturamento.strip(),
                    solicitante=solicitante.strip(),
                    fornecedor=fornecedor_sel,
                    destino=destino_manual.strip(),
                    observacoes=observacoes.strip(),
                    itens_df=pedido_edit,
                )

                nome_arquivo = f"pedido_{fornecedor_sel}_{destino_manual}_{data_pedido.strftime('%Y-%m-%d')}.pdf"
                nome_arquivo = nome_arquivo.replace(" ", "_").replace("/", "-")

                st.download_button(
                    "📄 Baixar Pedido (PDF)",
                    data=pdf_bytes,
                    file_name=nome_arquivo,
                    mime="application/pdf",
                )

        st.markdown('</div>', unsafe_allow_html=True)
