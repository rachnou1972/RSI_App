import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_final_v7.db"
# Kräftige Farben für die Modul-Hintergründe (Blau, Grün, Lila, etc.)
COLORS = ["#2b306b", "#1b4d3e", "#4a1b41", "#3d1b4a", "#1b3d4a"]


# --- BASIS FUNKTIONEN ---
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

if not check_password():
    st.stop()

# GLOBALER CSS FIX (FÜR DAS MODUL-DESIGN)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }

    /* Laptop Zentrierung */
    @media (min-width: 768px) {
        .main .block-container { max-width: 850px; margin: auto; }
    }

    /* WICHTIG: Das umschließende Element (Modul) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 20px !important;
        margin-bottom: 40px !important;
        padding: 20px !important; /* Hierdurch wird die Hintergrundfarbe an den Seiten sichtbar */
        border: none !important;
    }

    /* Stufe 1: Header innerhalb des Moduls */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        color: white;
    }
    .header-left { display: flex; align-items: baseline; gap: 15px; }
    .stock-title { font-size: 2em; font-weight: bold; }
    .stock-isin { font-size: 0.9em; color: rgba(255,255,255,0.7); }
    .stock-price { font-size: 1.5em; margin-left: 10px; font-weight: bold; }

    /* RSI Bubble rechts */
    .rsi-bubble {
        padding: 10px 20px;
        border-radius: 15px;
        font-size: 1.2em;
        font-weight: bold;
        border: 2px solid white;
    }
    .buy { background: rgba(0,255,136,0.2); color: #00ff88; border-color: #00ff88; }
    .sell { background: rgba(255,78,78,0.2); color: #ff4e4e; border-color: #ff4e4e; }
    .neutral { background: rgba(255,204,0,0.2); color: #ffcc00; border-color: #ffcc00; }

    /* Button Styling am Ende */
    div.stButton > button {
        background-color: #ff4e4e !important;
        color: white !important;
        border-radius: 10px !important;
        height: 45px !important;
        border: none !important;
        margin-top: 20px !important;
    }

    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

with st.sidebar:
    st.header("⚙️ Menü")
    st.text_area("Backup Liste:", value=",".join(st.session_state.watchlist), height=80)
    if st.button("Abmelden", use_container_width=True):
        st.session_state.clear()
        trigger_rerun()

st.title("📈 RSI Tracker")

# SUCHE
search = st.text_input("Aktie / ISIN suchen:")
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
        bg_modul = COLORS[i % len(COLORS)]
        clean_id = ticker.replace(".", "_").replace("-", "_")

        # DER UMSCHLIESSENDE CONTAINER
        with st.container(border=True):
            # Wir setzen einen Marker, um genau diesen Container per CSS zu färben
            st.markdown(f'<div id="marker-{clean_id}"></div>', unsafe_allow_html=True)

            # SPEZIFISCHES CSS: Färbt den Rahmen-Container dieses Tickers
            st.markdown(f"""
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(#marker-{clean_id}) {{
                    background-color: {bg_modul} !important;
                }}
                </style>
                """, unsafe_allow_html=True)

            try:
                df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
                if not df.empty:
                    isin = get_isin(ticker)
                    rsi_v = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    cl = "buy" if rsi_v < 30 else "sell" if rsi_v > 70 else "neutral"
                    stat = "Kaufzone" if cl == "buy" else ("Verkaufzone" if cl == "sell" else "Neutral")

                    # STUFE 1: HEADER (Name, ISIN, Preis, Bubble)
                    st.markdown(f"""
                        <div class="module-header">
                            <div class="header-left">
                                <span class="stock-title">{ticker} : <span class="stock-isin">{isin}</span></span>
                                <span class="stock-price">{price:.2f}</span>
                            </div>
                            <div class="rsi-bubble {cl}">RSI (14): {rsi_v:.2f} - {stat}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # STUFE 2: CHART (Mittelteil)
                    # Der Chart hat seinen eigenen dunklen Hintergrund, die Modul-Farbe bildet den Rahmen
                    fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                    fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                    fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                    fig.update_layout(
                        height=180, margin=dict(l=5, r=5, t=5, b=5),
                        paper_bgcolor='#1a1a1a', plot_bgcolor='#1a1a1a',  # Dunkler Chart-Hintergrund
                        font=dict(color="white"), xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    # STUFE 3: BUTTON (Unterteil)
                    if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.cache_data.clear()
                        trigger_rerun()
            except:
                st.error(f"Fehler bei {ticker}")