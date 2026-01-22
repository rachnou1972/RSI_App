import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- KONFIGURATION ---
DB_NAME = "watchlist_pro.db"
COLORS = ["#2b306b", "#1e4f47", "#4f1e3a", "#3e1e4f", "#1e3b4f"]  # Verschiedene Hintergrundfarben


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY, info TEXT)')
    conn.commit()
    conn.close()


def load_watchlist():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT symbol FROM watchlist')
    data = [row[0] for row in c.fetchall()]
    conn.close()
    if not data:
        initial = st.secrets.get("START_STOCKS", "AAPL,TSLA,SAP.DE").split(",")
        return [s.strip() for s in initial]
    return data


def add_to_db(symbol):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO watchlist (symbol) VALUES (?)', (symbol,))
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
        pw = st.secrets.get("MY_PASSWORD", "trader2025")
        u_input = st.text_input("Passwort", type="password")
        if st.button("Anmelden", use_container_width=True):
            if u_input == pw:
                st.session_state.password_correct = True
                trigger_rerun()
            else:
                st.error("Falsches Passwort!")
        return False
    return True


if not check_password(): st.stop()


# --- DATEN-LOGIK ---
@st.cache_data(ttl=300)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    return yf.download(tickers, period="3mo", interval="1d", progress=False)


def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# --- UI SETUP ---
st.set_page_config(page_title="RSI Ultimate", layout="wide")
init_db()

st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e1117; color: white; }}
    @media (min-width: 768px) {{
        .main .block-container {{ max-width: 850px; margin: auto; }}
    }}
    /* Design für die Super-Card */
    .super-card {{
        padding: 25px;
        border-radius: 20px;
        margin-bottom: 25px;
        border-left: 10px solid #4e8cff;
        box-shadow: 0 8px 20px rgba(0,0,0,0.5);
    }}
    .stock-title {{ font-size: 1.8em; font-weight: bold; margin-bottom: 0px; }}
    .stock-meta {{ font-size: 0.9em; color: #ccc; margin-bottom: 15px; }}
    .rsi-box {{ font-size: 1.2em; padding: 5px 10px; border-radius: 8px; display: inline-block; }}
    .buy {{ background-color: #00ff8822; color: #00ff88; border: 1px solid #00ff88; }}
    .sell {{ background-color: #ff4e4e22; color: #ff4e4e; border: 1px solid #ff4e4e; }}
    .neutral {{ background-color: #ffcc0022; color: #ffcc00; border: 1px solid #ffcc00; }}
    div.stButton > button {{ background-color: #4e8cff !important; color: white !important; border-radius: 10px; font-weight: bold; height: 45px; border: none; }}
    input {{ color: #000 !important; font-weight: bold !important; }}
    </style>
    """, unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Ultimate Tracker")

# --- SUCHE (Mit Markt-Auswahl) ---
search = st.text_input("Aktie/ISIN suchen...", placeholder="Name, ISIN oder WKN eingeben...")
if len(search) > 1:
    res = yf.Search(search, max_results=8).quotes
    if res:
        # Hier zeigen wir den Markt (Exchange) mit an, um die richtige ISIN/Börse zu finden
        options = {f"{r.get('shortname')} ({r.get('symbol')}) - Markt: {r.get('exchDisp')}": r.get('symbol') for r in
                   res if r.get('shortname')}
        sel = st.selectbox("Wähle den genauen Börsenplatz:", options.keys())
        if st.button("➕ Zu meiner Liste hinzufügen", use_container_width=True):
            sym = options[sel]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                add_to_db(sym)
                st.cache_data.clear()
                trigger_rerun()

st.divider()

# --- ANZEIGE DER SUPER-CARDS ---
if st.session_state.watchlist:
    all_data = fetch_data(st.session_state.watchlist)

    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            # Hintergrundfarbe wechseln
            bg_color = COLORS[i % len(COLORS)]

            # Ticker Details holen (für ISIN)
            t_info = yf.Ticker(ticker)
            isin = t_info.isin if hasattr(t_info, 'isin') else "N/A"

            # Kursdaten
            df = all_data.xs(ticker, axis=1, level=1) if len(st.session_state.watchlist) > 1 else all_data
            if not df.empty:
                rsi_series = calc_rsi(df['Close'])
                curr_rsi = rsi_series.iloc[-1]
                curr_price = df['Close'].iloc[-1]

                # Bewertung
                cl_name = "buy" if curr_rsi < 30 else "sell" if curr_rsi > 70 else "neutral"
                rating_text = "ÜBERVERKAUFT (KAUFZONE)" if curr_rsi < 30 else "ÜBERKAUFT (VERKAUFZONE)" if curr_rsi > 70 else "NEUTRAL"

                # Die Super-Card (HTML Teil)
                st.markdown(f"""
                <div class="super-card" style="background-color: {bg_color};">
                    <div class="stock-title">{ticker}</div>
                    <div class="stock-meta">ISIN: {isin} | Preis: {curr_price:.2f}</div>
                    <div class="rsi-box {cl_name}">RSI (14): {curr_rsi:.2f} - {rating_text}</div>
                </div>
                """, unsafe_allow_html=True)

                # Chart direkt unter dem Text (noch innerhalb des visuellen Elements)
                fig = go.Figure(go.Scatter(x=df.index, y=rsi_series, line=dict(color='white', width=3)))
                fig.add_hline(y=70, line_dash="dash", line_color="#ff4e4e")
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff88")
                fig.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)',
                                  plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                                  xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=False))

                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                if st.button(f"🗑️ {ticker} entfernen", key="del_" + ticker, use_container_width=True):
                    st.session_state.watchlist.remove(ticker)
                    remove_from_db(ticker)
                    st.cache_data.clear()
                    trigger_rerun()
                st.markdown("<br>", unsafe_allow_html=True)
        except:
            continue