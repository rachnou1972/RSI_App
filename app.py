import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- SETUP & DATENBANK ---
DB_NAME = "watchlist_ultimate_v50.db"
# Kräftige Farben für die Modul-Hintergründe (Blau, Grün, Lila, etc.)
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#312e81", "#134e4a"]


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()


def load_watchlist():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT symbol FROM watchlist')
    data = [row[0] for row in c.fetchall()]
    conn.close()
    if not data: return ["AAPL", "TSLA"]
    return data


def add_to_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('INSERT OR REPLACE INTO watchlist VALUES (?)', (symbol,))
        conn.commit()
    except:
        pass
    conn.close()


def remove_from_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()


def calc_rsi(series, period=14):
    if len(series) < period: return pd.Series([50] * len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker", layout="wide")
init_db()

# --- CSS: DAS ERZWINGT DEN FARBIGEN BLOCK UM ALLES ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }

    @media (min-width: 768px) {
        .main .block-container { max-width: 850px; margin: auto; }
    }

    /* 1. DER GANZE BLOCK (HEADER, CHART, BUTTON) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.color-sticker) {
        border-radius: 35px !important;
        border: none !important;
        padding: 25px !important; /* Erzeugt den farbigen Rand um Chart/Button */
        margin-bottom: 40px !important;
        display: block !important;
    }

    /* Entfernt schwarzen Abstand zwischen Elementen im Modul */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.color-sticker) div[data-testid="stVerticalBlock"] {
        gap: 0px !important;
    }

    /* 2. STUFE: HEADER BOXEN */
    .header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        width: 100%;
    }
    .box-info {
        background-color: #d1e8ff; 
        padding: 10px 18px;
        border-radius: 5px;
        color: #ff0000;
        font-weight: bold;
        font-size: 1.1em;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .box-rsi {
        background-color: #ffb400; 
        padding: 10px 18px;
        border-radius: 5px;
        color: black;
        font-weight: bold;
        font-size: 1.3em;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    /* 3. STUFE: CHART BOX (Pfirsich) */
    .chart-wrapper {
        background-color: #f7cbb4; 
        border-radius: 20px;
        padding: 10px;
        margin-bottom: 20px;
        border: 1px solid rgba(0,0,0,0.1);
    }

    /* 4. STUFE: BUTTON (Grün) */
    div.stButton > button {
        background-color: #c4f3ce !important; 
        color: #1a3d34 !important;
        border-radius: 15px !important;
        height: 60px !important;
        font-size: 1.5em !important;
        font-weight: bold !important;
        border: 1px solid rgba(0,0,0,0.2) !important;
        width: 100% !important;
    }

    /* Mobil-Anpassung */
    @media (max-width: 600px) {
        .header-row { flex-direction: column; gap: 10px; }
        .box-info, .box-rsi { width: 100%; text-align: center; }
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# SUCHE
search = st.text_input("Suchen (Name/ISIN/Symbol):", placeholder="Tippen zum Suchen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Wähle:", opts.keys())
            if st.button("➕ Hinzufügen", use_container_width=True):
                s = opts[sel]
                if s not in st.session_state.watchlist:
                    st.session_state.watchlist.append(s)
                    add_to_db(s)
                    st.rerun()
    except:
        pass

st.divider()

# --- MODULE ANZEIGEN ---
if st.session_state.watchlist:
    try:
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.error("Datenfehler.")
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        bg = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")

        # DER UMSCHLIESSENDE CONTAINER (Das Modul)
        with st.container(border=True):
            # Der Sticker ist der Schlüssel: Er identifiziert diesen Block für das CSS
            st.markdown(f"""
                <div class="color-sticker" id="s-{safe_id}"></div>
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#s-{safe_id}) {{
                    background-color: {bg} !important;
                }}
                </style>
                """, unsafe_allow_html=True)

            try:
                if len(st.session_state.watchlist) > 1:
                    df = all_data.xs(ticker, axis=1, level=1)
                else:
                    df = all_data

                if not df.empty:
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    eval_txt = "Überkauft" if rsi_v > 70 else ("Überverkauft" if rsi_v < 30 else "Neutral")

                    # 1. STUFE: HEADER
                    st.markdown(f"""
                        <div class="header-row">
                            <div class="info-box">{ticker} : {price:.2f}</div>
                            <div class="box-rsi">RSI (14): {rsi_v:.2f} - {eval_txt}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # 2. STUFE: CHART IN PFIRSICH BOX
                    st.markdown('<div class="chart-wrapper">', unsafe_allow_html=True)
                    fig = go.Figure(
                        go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                    fig.add_hline(y=70, line_dash="dash", line_color="red")
                    fig.add_hline(y=30, line_dash="dash", line_color="green")
                    fig.update_layout(
                        height=200, margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor='#f7cbb4', plot_bgcolor='#f7cbb4',
                        font=dict(color="#1a3d5e", size=11),
                        xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div>', unsafe_allow_html=True)

                    # 3. STUFE: BUTTON (Grün)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()

            except:
                continue