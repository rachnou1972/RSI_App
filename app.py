import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION & DATENBANK ---
DB_NAME = "watchlist_final_v10.db"
# Kräftige Modul-Farben (Blau, Dunkelgrün, Weinrot, Violett, Petrol)
COLORS = ["#1e537d", "#145c48", "#7d1e3d", "#4b1e7d", "#1e727d"]


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
    if not data:
        try:
            sl = st.secrets.get("START_STOCKS", "")
            if sl:
                data = [s.strip() for s in sl.split(",") if s.strip()]
                for s in data: add_to_db(s)
        except:
            data = ["AAPL"]
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


def trigger_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# --- DATEN LOGIK ---
@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


@st.cache_data(ttl=3600)
def get_isin(symbol):
    try:
        t = yf.Ticker(symbol)
        return t.isin if t.isin else "-"
    except:
        return "-"


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker Ultimate", layout="wide")
init_db()

# --- CSS FÜR DAS DESIGN NACH ZEICHNUNG ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }

    /* Laptop-Zentrierung */
    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* Das umschließende UI-Element (Modul) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.stock-marker) {
        border-radius: 40px !important; /* Sehr rund wie in Zeichnung */
        padding: 25px !important;
        margin-bottom: 40px !important;
        border: none !important;
    }

    /* Header Bereich */
    .header-box {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        padding-bottom: 15px;
    }
    .header-left { font-size: 1.8em; font-weight: bold; color: white; }
    .header-left-isin { font-size: 0.6em; color: rgba(255,255,255,0.7); font-weight: normal; }
    .header-right { font-size: 1.6em; font-weight: bold; }

    /* Schwebendes Chart Element */
    .chart-container {
        border-radius: 20px;
        overflow: hidden;
        margin: 15px 0;
        border: 2px solid rgba(255,255,255,0.1);
    }

    /* Schwebender Button */
    div.stButton > button {
        background-color: #c4f3ce !important; /* Hellgrün wie in Zeichnung */
        color: #1a3d34 !important;
        border-radius: 20px !important;
        height: 60px !important;
        font-size: 1.5em !important;
        font-weight: bold !important;
        border: none !important;
        margin-top: 10px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }

    input { color: #000 !important; font-weight: bold !important; background-color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# SIDEBAR NUR FÜR BACKUP
with st.sidebar:
    st.header("⚙️ Backup")
    st.text_area("Liste:", value=",".join(st.session_state.watchlist), height=80)

st.title("📈 RSI Tracker")

# SUCHE
search = st.text_input("Aktie suchen (Name/ISIN/WKN):")
if len(search) > 1:
    res = yf.Search(search, max_results=5).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res}
        sel = st.selectbox("Wähle:", options.keys())
        if st.button("➕ Hinzufügen", use_container_width=True):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                add_to_db(sym)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# ANZEIGE DER MODULE NACH ZEICHNUNG
if st.session_state.watchlist:
    all_data = fetch_data(st.session_state.watchlist)

    for i, ticker in enumerate(st.session_state.watchlist):
        bg_modul = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")

        with st.container(border=True):
            # Marker für CSS
            st.markdown(f'<div class="stock-marker" id="m-{safe_id}"></div>', unsafe_allow_html=True)
            st.markdown(
                f"""<style>div[data-testid="stVerticalBlockBorderWrapper"]:has(#m-{safe_id}) {{ background-color: {bg_modul} !important; }}</style>""",
                unsafe_allow_html=True)

            try:
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    isin = get_isin(ticker)
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]

                    # Header
                    st.markdown(f"""
                        <div class="header-box">
                            <div class="header-left">{ticker} : <span class="header-left-isin">{isin}</span> &nbsp; {price:.2f}</div>
                            <div class="header-right">RSI (14): {rsi_v:.2f} - Neutral</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Chart (Mitte)
                    fig = go.Figure(
                        go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#1a3d5e', width=4)))
                    fig.add_hline(y=70, line_dash="dash", line_color="red")
                    fig.add_hline(y=30, line_dash="dash", line_color="green")
                    fig.update_layout(
                        height=200, margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor='#f7cbb4', plot_bgcolor='#f7cbb4',  # Hautfarbe wie in Zeichnung
                        font=dict(color="#1a3d5e", size=12),
                        xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # Button (Unten)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.cache_data.clear()
                        trigger_rerun()
            except:
                st.error(f"Fehler bei {ticker}")