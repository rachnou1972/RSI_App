import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3

# --- DATENBANK ---
DB_NAME = "watchlist.db"
COLORS = ["#1e3a8a", "#064e3b", "#581c87", "#0f766e", "#334155"]

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
    return data if data else ["AAPL", "TSLA"]

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
    if len(series) < period: 
        return pd.Series([50] * len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker", layout="wide")
init_db()

# --- CSS KORREKTUR ---
st.markdown("""
    <style>
    /* Mobile-First Design */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Laptop-Zentrierung (850px) */
    @media (min-width: 768px) {
        .main .block-container { 
            max-width: 850px !important; 
            margin: auto !important; 
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
    }
    
    /* ÄUSSERER RAHMEN - KEINE LÜCKEN */
    .outer-module {
        border-radius: 25px !important;
        overflow: hidden !important;
        margin-bottom: 30px !important;
        border: none !important;
        padding: 0px !important;
    }
    
    /* HEADER WIE AUF DEM BILD - 2 ZEILEN */
    .module-header {
        padding: 20px 20px 15px 20px !important;
    }
    
    /* 1. ZEILE: Symbol und Preis nebeneinander */
    .top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .symbol-text {
        font-size: 1.8em !important;
        font-weight: bold !important;
        color: white !important;
        margin: 0 !important;
    }
    
    .price-text {
        font-size: 1.6em !important;
        font-weight: bold !important;
        color: white !important;
        margin: 0 !important;
        background-color: rgba(255,255,255,0.2) !important;
        padding: 5px 12px !important;
        border-radius: 8px !important;
    }
    
    /* 2. ZEILE: ISIN links, RSI rechts */
    .bottom-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .isin-text {
        font-size: 1em !important;
        color: rgba(255,255,255,0.9) !important;
        margin: 0 !important;
    }
    
    .rsi-box {
        background-color: #ffb400 !important;
        padding: 8px 16px !important;
        border-radius: 10px !important;
        color: black !important;
        font-weight: bold !important;
        font-size: 1.2em !important;
        border: 2px solid rgba(0,0,0,0.2) !important;
        text-align: center !important;
    }
    
    /* CHART CONTAINER (PFIRSICH) */
    .chart-area {
        background-color: #f7cbb4 !important;
        margin: 0 20px 15px 20px !important;
        border-radius: 15px !important;
        padding: 15px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
    }
    
    /* BUTTON CONTAINER (HELLGRÜN) */
    .button-area {
        background-color: #c4f3ce !important;
        margin: 0 20px 20px 20px !important;
        border-radius: 12px !important;
        padding: 0px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        overflow: hidden !important;
    }
    
    /* Entfernen-Button */
    .button-area button {
        background-color: transparent !important;
        color: #1a3d34 !important;
        border: none !important;
        height: 50px !important;
        font-size: 1.3em !important;
        font-weight: bold !important;
        width: 100% !important;
        margin: 0 !important;
    }
    
    /* Mobile */
    @media (max-width: 600px) {
        .top-row {
            flex-direction: column;
            gap: 10px;
            text-align: center;
        }
        
        .bottom-row {
            flex-direction: column;
            gap: 10px;
            text-align: center;
        }
        
        .symbol-text { font-size: 1.5em !important; }
        .price-text { font-size: 1.3em !important; }
        
        .chart-area, .button-area {
            margin-left: 15px !important;
            margin-right: 15px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Session State
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# Suche
search = st.text_input("Aktie suchen (Name/Symbol/WKN):", placeholder="Hier tippen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') 
                   for r in res if r.get('shortname')}
            sel = st.selectbox("Ergebnis wählen:", opts.keys())
            if st.button("➕ Hinzufügen", key="add_btn"):
                s = opts[sel]
                if s not in st.session_state.watchlist:
                    st.session_state.watchlist.append(s)
                    add_to_db(s)
                    st.rerun()
    except:
        pass

st.divider()

# Anzeige
if st.session_state.watchlist:
    all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)
    
    for i, ticker in enumerate(st.session_state.watchlist):
        color = COLORS[i % len(COLORS)]
        
        # Äußerer Rahmen mit Farbe
        st.markdown(f"""
            <style>
            .module-{i} {{
                background-color: {color} !important;
            }}
            </style>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown(f'<div class="outer-module module-{i}">', unsafe_allow_html=True)
            
            try:
                # Daten
                if len(st.session_state.watchlist) > 1:
                    df = all_data.xs(ticker, axis=1, level=1)
                else:
                    df = all_data
                
                if not df.empty:
                    rsi_val = calc_rsi(df['Close']).iloc[-1]
                    price = df['Close'].iloc[-1]
                    
                    # RSI Bewertung
                    if rsi_val > 70:
                        rsi_text = "Überkauft"
                    elif rsi_val < 30:
                        rsi_text = "Überverkauft"
                    else:
                        rsi_text = "Neutral"
                    
                    # ISIN (Placeholder)
                    isin = f"ISIN: US{ticker.ljust(9, '0')[:9]}0"
                    
                    # HEADER WIE AUF DEM BILD
                    st.markdown(f"""
                        <div class="module-header">
                            <div class="top-row">
                                <div class="symbol-text">{ticker}</div>
                                <div class="price-text">${price:.2f}</div>
                            </div>
                            <div class="bottom-row">
                                <div class="isin-text">{isin}</div>
                                <div class="rsi-box">
                                    RSI: {rsi_val:.1f}<br>
                                    <small>{rsi_text}</small>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # CHART
                    st.markdown('<div class="chart-area">', unsafe_allow_html=True)
                    fig = go.Figure(go.Scatter(
                        x=df.index, 
                        y=calc_rsi(df['Close']), 
                        line=dict(color='#1a3d5e', width=3)
                    ))
                    fig.add_hline(y=70, line_dash="dash", line_color="red")
                    fig.add_hline(y=30, line_dash="dash", line_color="green")
                    fig.update_layout(
                        height=200,
                        margin=dict(l=5, r=5, t=5, b=5),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=False, showticklabels=True),
                        yaxis=dict(range=[0, 100], showgrid=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # BUTTON
                    st.markdown('<div class="button-area">', unsafe_allow_html=True)
                    if st.button(f"🗑️ {ticker} entfernen", key=f"del_{ticker}"):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"Fehler bei {ticker}")
            
            st.markdown('</div>', unsafe_allow_html=True)
