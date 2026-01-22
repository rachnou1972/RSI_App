import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_final_v4.db"
# Kräftige Farben für die Module
MODULE_COLORS = ["#2b306b", "#1e4f42", "#4f1e3a", "#3e1e4f", "#1e3b4f"]


# --- DATENBANK ---
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
            secret_list = st.secrets.get("START_STOCKS", "")
            if secret_list:
                data = [s.strip() for s in secret_list.split(",") if s.strip()]
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


# --- SICHERHEIT ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Trader Login")
        try:
            pw = st.secrets["MY_PASSWORD"]
        except:
            st.error("Bitte MY_PASSWORD in Secrets setzen!"); st.stop()
        u_input = st.text_input("Passwort", type="password")
        if st.button("Anmelden", use_container_width=True):
            if u_input == pw:
                st.session_state.password_correct = True
                trigger_rerun()
            else:
                st.error("Falsch!")
        return False
    return True


# --- DATEN LOGIK ---
@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


@st.cache_data(ttl=3600)
def get_isin_fast(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
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

if not check_password():
    st.stop()

# CSS FÜR DAS EINGESCHLOSSENE MODUL
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }

    /* Laptop-Zentrierung */
    @media (min-width: 768px) {
        .main .block-container { max-width: 900px; margin: auto; }
    }

    /* Styling für den umschließenden Block eines Tickers */
    [data-testid="stVerticalBlockBorderWrapper"]:has(div[id^="stock-block-"]) {
        border-radius: 20px !important;
        padding: 0px !important;
        margin-bottom: 25px !important;
        overflow: hidden !important;
        border: none !important;
    }

    /* Header Bereich */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        width: 100%;
    }

    .info-left { display: flex; align-items: baseline; gap: 15px; }
    .title-text { font-size: 2.2em; font-weight: bold; }
    .isin-text { font-size: 1em; color: #bbb; }
    .price-text { font-size: 1.5em; margin-left: 10px; }

    /* RSI Bubble */
    .rsi-bubble {
        padding: 10px 18px;
        border-radius: 12px;
        font-size: 1.3em;
        font-weight: bold;
        border: 2px solid;
    }
    .buy { border-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }
    .sell { border-color: #ff4e4e; color: #ff4e4e; background: rgba(255,78,78,0.1); }
    .neutral { border-color: #ffcc00; color: #ffcc00; background: rgba(255,204,0,0.1); }

    /* Button Fix: Ganz unten im Block */
    div.stButton > button {
        border-radius: 0px 0px 15px 15px !important;
        height: 50px !important;
        background-color: #ff4e4e !important;
        border: none !important;
        margin-top: -10px !important;
    }

    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

with st.sidebar:
    st.header("⚙️ Backup")
    st.text_area("Liste kopieren:", value=",".join(st.session_state.watchlist), height=80)
    if st.button("Abmelden", use_container_width=True):
        st.session_state.clear()
        trigger_rerun()

st.title("📈 RSI Tracker")

# SUCHE
search = st.text_input("Suche (Name/WKN/ISIN):")
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

# MODULE ANZEIGEN
if st.session_state.watchlist:
    all_data = fetch_data(st.session_state.watchlist)

    for i, ticker in enumerate(st.session_state.watchlist):
        bg_color = MODULE_COLORS[i % len(MODULE_COLORS)]

        # Erzeuge einen Container mit Rahmen (Border), den wir per CSS färben
        with st.container(border=True):
            # Unsichtbarer Marker für CSS-Targeting
            st.markdown(f'<div id="stock-block-{ticker}"></div>', unsafe_allow_html=True)

            # CSS Injektion um genau DIESEN Container zu färben
            st.markdown(f"""
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="stock-block-{ticker}"]) {{
                    background-color: {bg_color} !important;
                }}
                </style>
                """, unsafe_allow_html=True)

            try:
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    isin = get_isin_fast(ticker)
                    rsi_val = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                    status = "Neutral" if cl == "neutral" else ("Kaufzone" if cl == "buy" else "Verkaufzone")

                    # STUFE 1: HEADER
                    st.markdown(f"""
                        <div class="module-header">
                            <div class="info-left">
                                <span class="title-text">{ticker} : <span class="isin-text">{isin}</span></span>
                                <span class="price-text">Preis: {price:.2f}</span>
                            </div>
                            <div class="rsi-bubble {cl}">RSI (14): {rsi_val:.2f} - {status}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART (Transparent)
                    fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                    fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                    fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                    fig.update_layout(
                        height=180, margin=dict(l=10, r=10, t=0, b=0),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="white"), xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # STUFE 3: BUTTON (Bündig am unteren Rand)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.cache_data.clear()
                        trigger_rerun()
            except:
                st.error(f"Fehler bei {ticker}")