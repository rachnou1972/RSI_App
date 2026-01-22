import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK & SETUP ---
DB_NAME = "watchlist_final_v40.db"
# Kräftige Modul-Farben (Blau, Dunkelgrün, Weinrot, Violett, Petrol)
COLORS = ["#1e3a8a", "#064e3b", "#7d1e3d", "#312e81", "#134e4a"]


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
st.set_page_config(page_title="RSI Tracker Pro", layout="wide")
init_db()

# --- CSS: DAS ERZWINGT DIE FARBEN OHNE SCHWARZE LÜCKEN ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }

    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* Entfernt die schwarzen Lücken zwischen den Elementen im Modul */
    div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
        gap: 0px !important;
    }

    /* Das umschließende Modul (Rahmen) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 0px !important;
        border: none !important;
        border-radius: 30px !important;
        overflow: hidden !important;
        margin-bottom: 40px !important;
    }

    /* Header Bereich */
    .custom-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 25px;
        width: 100%;
    }
    .info-box {
        background-color: #d1e8ff; 
        padding: 8px 15px;
        border-radius: 5px;
        color: #ff0000;
        font-weight: bold;
        font-size: 1.1em;
    }
    .rsi-box-eval {
        background-color: #ffb400; 
        padding: 8px 15px;
        border-radius: 5px;
        color: black;
        font-weight: bold;
        font-size: 1.2em;
    }

    /* Chart Bereich (Pfirsich Rahmen) */
    .chart-outer {
        background-color: transparent; /* Nimmt die Modul-Farbe an */
        padding: 0px 20px 20px 20px;
    }
    .chart-inner {
        background-color: #f7cbb4; /* Pfirsich-Farbe für den Chart selbst */
        border-radius: 15px;
        padding: 10px;
        border: 1px solid rgba(0,0,0,0.1);
    }

    /* Button Bereich (Grüner Button auf Modul-Farbe) */
    .button-area {
        padding: 0px 20px 20px 20px;
    }
    div.stButton > button {
        background-color: #c4f3ce !important; 
        color: #1a3d34 !important;
        border-radius: 15px !important;
        height: 55px !important;
        width: 100% !important;
        font-weight: bold !important;
        font-size: 1.3em !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Aktie suchen (Name/ISIN/WKN):", placeholder="Tippen...")
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

# --- ANZEIGE DER MODULE ---
if st.session_state.watchlist:
    try:
        all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    except:
        st.error("Datenfehler.")
        st.stop()

    for i, ticker in enumerate(st.session_state.watchlist):
        bg_color = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")

        # DER CONTAINER UM ALLES (Header, Chart, Button)
        with st.container(border=True):
            # CSS Injektion um genau DIESEN Container zu färben
            st.markdown(f"""
                <div id="m-{safe_id}"></div>
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#m-{safe_id}) {{
                    background-color: {bg_color} !important;
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
                        <div class="custom-header">
                            <div class="info-box">{ticker} : {price:.2f}</div>
                            <div class="rsi-box-eval">RSI (14): {rsi_v:.2f} - {eval_txt}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # 2. STUFE: CHART IN PFIRSICH-BOX
                    st.markdown('<div class="chart-outer"><div class="chart-inner">', unsafe_allow_html=True)
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
                    st.markdown('</div></div>', unsafe_allow_html=True)

                    # 3. STUFE: BUTTON IN GRÜN
                    st.markdown('<div class="button-area">', unsafe_allow_html=True)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            except:
                continue