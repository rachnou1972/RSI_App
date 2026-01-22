import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import os

# --- DATENBANK ---
DB_NAME = "watchlist_final_master.db"
# Kräftige Farben für jedes Aktien-Modul
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

# --- NEUES CSS FÜR DAS BILD-LIKE LAYOUT ---
st.markdown("""
    <style>
    /* Hintergrund der Seite */
    .stApp { background-color: #0e1117 !important; }

    /* Zentrierung des Hauptinhalts */
    @media (min-width: 768px) {
        .main .block-container { 
            max-width: 850px !important; 
            margin: auto !important; 
            padding-top: 2rem !important;
        }
    }

    /* AKTIEN-MODUL STYLING (wie auf dem Bild) */
    .stock-module {
        border-radius: 20px !important;
        padding: 0px !important;
        margin-bottom: 30px !important;
        overflow: hidden !important;
        border: 2px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* HEADER-BEREICH mit Symbol, ISIN, Preis */
    .module-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 25px 15px 25px;
        background-color: rgba(255, 255, 255, 0.1);
        border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    }

    .symbol-section {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .symbol-name {
        font-size: 1.8em !important;
        font-weight: bold !important;
        color: white !important;
        margin: 0 !important;
    }

    .symbol-details {
        font-size: 0.9em !important;
        color: rgba(255, 255, 255, 0.8) !important;
        margin: 0 !important;
    }

    .price-section {
        text-align: right;
    }

    .current-price {
        font-size: 2em !important;
        font-weight: bold !important;
        color: white !important;
        margin: 0 !important;
    }

    /* RSI-BEWERTUNGSBEREICH */
    .rsi-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px 25px;
        background-color: rgba(0, 0, 0, 0.2);
    }

    .rsi-value {
        font-size: 1.8em !important;
        font-weight: bold !important;
        color: white !important;
        margin: 0 !important;
    }

    .rsi-label {
        font-size: 1.1em !important;
        color: rgba(255, 255, 255, 0.9) !important;
        margin: 0 !important;
    }

    .rsi-evaluation {
        font-size: 1.3em !important;
        font-weight: bold !important;
        padding: 8px 20px;
        border-radius: 20px;
        text-align: center;
        min-width: 150px;
    }

    .rsi-overbought {
        background-color: #ff4444 !important;
        color: white !important;
    }

    .rsi-oversold {
        background-color: #44ff44 !important;
        color: black !important;
    }

    .rsi-neutral {
        background-color: #ffaa00 !important;
        color: black !important;
    }

    /* CHART-BEREICH */
    .chart-container {
        background-color: rgba(255, 255, 255, 0.95) !important;
        margin: 0px !important;
        padding: 15px !important;
        border-radius: 0px !important;
    }

    /* BUTTON-BEREICH */
    .button-container {
        background-color: rgba(255, 255, 255, 0.1) !important;
        padding: 0px !important;
        margin: 0px !important;
        border-radius: 0px !important;
        border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    /* Entfernen-Button Styling */
    .stButton > button {
        background-color: transparent !important;
        color: white !important;
        border: none !important;
        height: 60px !important;
        font-size: 1.3em !important;
        font-weight: bold !important;
        width: 100% !important;
        border-radius: 0px !important;
        transition: background-color 0.3s !important;
    }

    .stButton > button:hover {
        background-color: rgba(255, 0, 0, 0.2) !important;
    }

    /* Suchfeld Styling */
    .stTextInput > div > div > input {
        color: #000 !important;
        font-weight: bold !important;
        background-color: white !important;
        border-radius: 10px !important;
        padding: 12px !important;
    }

    /* Smartphone Optimierung */
    @media (max-width: 600px) {
        .module-header { 
            flex-direction: column; 
            text-align: center;
            gap: 10px; 
            padding: 15px; 
        }
        
        .price-section {
            text-align: center;
        }
        
        .rsi-section {
            flex-direction: column;
            gap: 10px;
            text-align: center;
        }
        
        .symbol-name { font-size: 1.5em !important; }
        .current-price { font-size: 1.7em !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# Session State initialisieren
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# SUCHE
search = st.text_input("Aktie suchen (Name/ISIN/WKN):", placeholder="Hier tippen...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            opts = {f"{r.get('shortname')} ({r.get('symbol')})": r.get('symbol') for r in res if r.get('shortname')}
            sel = st.selectbox("Ergebnis wählen:", opts.keys())
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("➕ Hinzufügen", key="add_btn"):
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
    # Batch-Download aller Aktiendaten
    all_data = yf.download(st.session_state.watchlist, period="3mo", interval="1d", progress=False)

    for i, ticker in enumerate(st.session_state.watchlist):
        color = COLORS[i % len(COLORS)]
        safe_id = ticker.replace(".", "").replace("-", "")
        
        # Versuche, zusätzliche Informationen über die Aktie zu bekommen
        try:
            stock_info = yf.Ticker(ticker).info
            company_name = stock_info.get('longName', ticker)
            # Für echte ISIN müsstest du eine andere API oder Datenquelle nutzen
            isin_display = f"ISIN: US{ticker.ljust(9, '0')[:9]}0"  # Platzhalter
        except:
            company_name = ticker
            isin_display = "ISIN: -"
        
        # CSS für jedes Modul mit eigener Farbe
        st.markdown(f"""
            <style>
            #module-{safe_id} {{
                background-color: {color} !important;
            }}
            </style>
            """, unsafe_allow_html=True)
        
        # Hauptcontainer für jede Aktie
        with st.container():
            st.markdown(f'<div class="stock-module" id="module-{safe_id}">', unsafe_allow_html=True)
            
            try:
                # Daten für diese spezifische Aktie extrahieren
                if len(st.session_state.watchlist) > 1:
                    df = all_data.xs(ticker, axis=1, level=1)
                else:
                    df = all_data
                
                if not df.empty and len(df) > 14:
                    # RSI und Preis berechnen
                    rsi_series = calc_rsi(df['Close'])
                    rsi_value = rsi_series.iloc[-1]
                    price = df['Close'].iloc[-1]
                    
                    # RSI Bewertung
                    if rsi_value > 70:
                        eval_txt = "Überkauft"
                        eval_class = "rsi-overbought"
                    elif rsi_value < 30:
                        eval_txt = "Überverkauft"
                        eval_class = "rsi-oversold"
                    else:
                        eval_txt = "Neutral"
                        eval_class = "rsi-neutral"
                    
                    # --- HEADER: Symbol, ISIN, Preis ---
                    st.markdown(f"""
                        <div class="module-header">
                            <div class="symbol-section">
                                <div class="symbol-name">{ticker}</div>
                                <div class="symbol-details">{company_name}<br>{isin_display}</div>
                            </div>
                            <div class="price-section">
                                <div class="current-price">{price:.2f} USD</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # --- RSI BEWERTUNG ---
                    st.markdown(f"""
                        <div class="rsi-section">
                            <div>
                                <div class="rsi-label">RSI (14)</div>
                                <div class="rsi-value">{rsi_value:.2f}</div>
                            </div>
                            <div class="rsi-evaluation {eval_class}">
                                {eval_txt}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # --- CHART ---
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    fig = go.Figure(
                        go.Scatter(
                            x=df.index, 
                            y=rsi_series, 
                            line=dict(color='#1a3d5e', width=3),
                            fill='tozeroy',
                            fillcolor='rgba(26, 61, 94, 0.1)'
                        )
                    )
                    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.7)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.7)
                    fig.update_layout(
                        height=200, 
                        margin=dict(l=0, r=0, t=0, b=0),
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="#333", size=10),
                        xaxis=dict(
                            showgrid=False,
                            showticklabels=False
                        ), 
                        yaxis=dict(
                            range=[0, 100], 
                            showgrid=False,
                            title_text="RSI"
                        ),
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # --- ENTFERNEN BUTTON ---
                    st.markdown('<div class="button-container">', unsafe_allow_html=True)
                    if st.button(f"🗑️ {ticker} entfernen", key=f"del_{safe_id}", use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        remove_from_db(ticker)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                else:
                    st.error(f"Keine ausreichenden Daten für {ticker}")
                    
            except Exception as e:
                st.error(f"Fehler beim Laden von {ticker}: {str(e)}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
else:
    st.info("Keine Aktien in der Watchlist. Füge Aktien über das Suchfeld oben hinzu.")
