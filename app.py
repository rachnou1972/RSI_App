import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK SETUP (Stabiler als JSON) ---
DB_NAME = "watchlist.db"


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
    # Falls DB leer, lade Standard aus Secrets oder Startwert
    if not data:
        initial = st.secrets.get("START_STOCKS", "AAPL,TSLA").split(",")
        return [s.strip() for s in initial]
    return data


def add_to_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO watchlist VALUES (?)', (symbol,))
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


# --- APP INITIALISIERUNG ---
init_db()


def trigger_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# --- SICHERHEIT ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Sicherer Zugriff")
        try:
            pw = st.secrets["MY_PASSWORD"]
        except:
            st.error("Fehler: MY_PASSWORD in Secrets fehlt!")
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


# --- DATEN HOLEN ---
@st.cache_data(ttl=300)
def get_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))


# --- LAYOUT ---
st.set_page_config(page_title="RSI Tracker", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #1a1c3d; color: white; }
    @media (min-width: 768px) { .main .block-container { max-width: 800px; margin: auto; } }
    div.stButton > button { background-color: #4e8cff !important; color: white !important; border-radius: 12px; font-weight: bold; height: 48px; }
    input { color: #000 !important; font-weight: bold !important; }
    .card { background: linear-gradient(135deg, #2b306b 0%, #1e224f 100%); padding: 20px; border-radius: 18px; border-left: 8px solid #4e8cff; margin-bottom: 5px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); }
    .buy { color: #00ff88; font-weight: bold; } .sell { color: #ff4e4e; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# --- SIDEBAR BACKUP (DEIN RETTER) ---
with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.write("Kopiere diese Liste als Backup:")
    current_list_str = ",".join(st.session_state.watchlist)
    st.code(current_list_str)
    if st.button("Abmelden"):
        st.session_state.clear()
        trigger_rerun()

# --- HAUPTTEIL ---
st.title("📈 RSI Tracker")
search = st.text_input("Aktie suchen...", placeholder="z.B. Apple, Tesla...")

if len(search) > 1:
    res = yf.Search(search, max_results=5).quotes
    if res:
        options = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
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
    all_data = get_data(st.session_state.watchlist)
    for ticker in st.session_state.watchlist:
        try:
            df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
            if not df.empty:
                rsi = calc_rsi(df['Close']).iloc[-1]
                price = df['Close'].iloc[-1]

                cl = "buy" if rsi < 30 else "sell" if rsi > 70 else ""
                txt = "ÜBERVERKAUFT" if rsi < 30 else "ÜBERKAUFT" if rsi > 70 else "Neutral"

                st.markdown(f"""<div class="card">
                    <div style="display:flex; justify-content:space-between;"><b>{ticker}</b><span class="{cl}">{txt}</span></div>
                    <div>Kurs: {price:.2f} | RSI: <b class="{cl}">{rsi:.2f}</b></div>
                </div>""", unsafe_allow_html=True)

                fig = go.Figure(go.Scatter(x=df.index, y=calc_rsi(df['Close']), line=dict(color='#4e8cff', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="red")
                fig.add_hline(y=30, line_dash="dash", line_color="green")
                fig.update_layout(height=160, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)',
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