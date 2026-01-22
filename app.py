import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_ultimate.db"
COLORS = ["#2b306b", "#1e4f47", "#4f1e3a", "#3e1e4f", "#1e3b4f"]


# --- DATENBANK FUNKTIONEN ---
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

    # TRICK: Wenn DB leer ist, schaue in die Secrets
    if not data:
        try:
            secret_list = st.secrets.get("START_STOCKS", "")
            if secret_list:
                data = [s.strip() for s in secret_list.split(",") if s.strip()]
                # Automatisch in DB speichern, damit sie bleibt
                for s in data: add_to_db(s)
        except:
            data = ["AAPL"]  # Absoluter Notfall-Wert
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
            st.error("Fehler: Passwort in Secrets fehlt!")
            st.stop()
        u_input = st.text_input("Passwort", type="password")
        if st.button("Anmelden", use_container_width=True):
            if u_input == pw:
                st.session_state.password_correct = True
                trigger_rerun()
            else:
                st.error("Falsch!")
        return False
    return True


if not check_password(): st.stop()


# --- DATEN LOGIK ---
@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Pro", layout="wide")
init_db()

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    @media (min-width: 768px) { .main .block-container { max-width: 800px; margin: auto; } }
    .super-card { padding: 25px; border-radius: 20px; margin-bottom: 20px; border-left: 10px solid #4e8cff; box-shadow: 0 8px 20px rgba(0,0,0,0.5); }
    .stock-title { font-size: 1.8em; font-weight: bold; margin-bottom: 0px; }
    .stock-meta { font-size: 0.9em; color: #ccc; margin-bottom: 15px; }
    .rsi-box { font-size: 1.1em; padding: 6px 12px; border-radius: 8px; display: inline-block; font-weight: bold; }
    .buy { background-color: #00ff8822; color: #00ff88; border: 1px solid #00ff88; }
    .sell { background-color: #ff4e4e22; color: #ff4e4e; border: 1px solid #ff4e4e; }
    .neutral { background-color: #ffcc0022; color: #ffcc00; border: 1px solid #ffcc00; }
    div.stButton > button { background-color: #4e8cff !important; color: white !important; border-radius: 10px; font-weight: bold; height: 45px; border: none; }
    input { color: #000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# --- SIDEBAR: BACKUP & ABMELDEN ---
with st.sidebar:
    st.header("⚙️ Menü")
    st.write("Deine aktuelle Liste zum Speichern:")
    # Hier kannst du die Liste immer kopieren
    current_list_str = ",".join(st.session_state.watchlist)
    st.text_area("Kopieren & in Secrets speichern:", value=current_list_str, height=100)

    if st.button("Abmelden"):
        st.session_state.clear()
        trigger_rerun()
    st.divider()
    if st.button("🔄 Liste neu laden (Secrets)"):
        st.session_state.watchlist = []  # Leeren erzwingt neu laden
        trigger_rerun()

st.title("📈 RSI Ultimate")

# --- SUCHE ---
search = st.text_input("Suchen (Name, ISIN, Symbol)...")
if len(search) > 1:
    res = yf.Search(search, max_results=8).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')}) - {r.get('exchDisp')}": r.get('symbol') for r in res if
                   r.get('shortname')}
        sel = st.selectbox("Wähle:", options.keys())
        if st.button("➕ Hinzufügen", use_container_width=True):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                add_to_db(sym)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# --- ANZEIGE ---
if st.session_state.watchlist:
    all_data = fetch_data(st.session_state.watchlist)

    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            bg = COLORS[i % len(COLORS)]
            df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data

            if not df.empty:
                rsi_val = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]

                cl = "buy" if rsi_val < 30 else "sell" if rsi_val > 70 else "neutral"
                txt = "KAUFZONE" if rsi_val < 30 else "VERKAUFZONE" if rsi_val > 70 else "Neutral"

                st.markdown(f"""
                <div class="super-card" style="background-color: {bg};">
                    <div class="stock-title">{ticker}</div>
                    <div class="stock-meta">Preis: {price:.2f}</div>
                    <div class="rsi-box {cl}">RSI (14): {rsi_val:.2f} - {txt}</div>
                </div>
                """, unsafe_allow_html=True)

                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=180, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)',
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  yaxis=dict(range=[0, 100], showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                if st.button(f"🗑️ {ticker} löschen", key="del_" + ticker, use_container_width=True):
                    st.session_state.watchlist.remove(ticker)
                    remove_from_db(ticker)
                    st.cache_data.clear()
                    trigger_rerun()
        except:
            continue