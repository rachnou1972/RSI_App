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
    if len(series) < period: return pd.Series([50] * len(series))
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- UI SETUP ---
st.set_page_config(page_title="RSI Tracker", layout="wide")
init_db()

# --- EXAKTES CSS FÜR DAS BILD-LAYOUT ---
st.markdown("""
    <style>
    /* Mobile-First Design */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Laptop-Zentrierung (850px breit und mittig) */
    @media (min-width: 768px) {
        .main .block-container { 
            max-width: 850px !important; 
            margin: auto !important; 
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
    }
    
    /* ENTFERNT ALLE RÄNDER UND ABSTÄNDE */
    div[data-testid="stVerticalBlock"] > div[style*="flex"] {
        gap: 0px !important;
    }
    
    /* ÄUSSERER RAHMEN - KEINE LÜCKEN */
    .stock-module {
        border-radius: 25px !important;
        overflow: hidden !important;
        margin-bottom: 30px !important;
        border: none !important;
        padding: 0px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    
    /* WICHTIG: HEADER WIE AUF DEM BILD - ZWEI ZEILEN IM ERSTEN BLOCK */
    .header-block {
        padding: 25px 25px 10px 25px !important;
        width: 100% !important;
    }
    
    /* Erste Zeile: Symbol und Preis LINKS nebeneinander */
    .symbol-price-row {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-bottom: 8px !important;
        width: 100% !important;
    }
    
    /* Symbol links */
    .symbol-display {
        font-size: 2.2em !important;
        font-weight: bold !important;
        color: white !important;
        margin: 0 !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3) !important;
    }
    
    /* Preis rechts */
    .price-display {
        font-size: 1.8em !important;
        font-weight: bold !important;
        color: white !important;
        margin: 0 !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3) !important;
        background-color: rgba(255,255,255,0.15) !important;
        padding: 8px 16px !important;
        border-radius: 10px !important;
    }
    
    /* Zweite Zeile: ISIN und RSI nebeneinander */
    .isin-rsi-row {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        width: 100% !important;
    }
    
    /* ISIN links */
    .isin-display {
        font-size: 1.1em !important;
        color: rgba(255,255,255,0.9) !important;
        margin: 0 !important;
        padding: 5px 0 !important;
    }
    
    /* RSI Bewertung rechts (GELBE BOX) */
    .rsi-evaluation-box {
        background-color: #ffb400 !important;
        padding: 10px 20px !important;
        border-radius: 12px !important;
        color: black !important;
        font-weight: bold !important;
        font-size: 1.4em !important;
        border: 2px solid rgba(0,0,0,0.2) !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.2) !important;
        text-align: center !important;
        min-width: 180px !important;
    }
    
    /* CHART BEREICH (PFIRSICH) */
    .chart-container {
        background-color: #f7cbb4 !important;
        margin: 0 25px 15px 25px !important;
        border-radius: 20px !important;
        padding: 20px !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    
    /* BUTTON BEREICH (HELLGRÜN) */
    .button-container {
        background-color: #c4f3ce !important;
        margin: 0 25px 25px 25px !important;
        border-radius: 15px !important;
        padding: 0px !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
        overflow: hidden !important;
    }
    
    /* Entfernen-Button */
    .button-container button {
        background-color: transparent !important;
        color: #1a3d34 !important;
        border: none !important;
        height: 60px !important;
        font-size: 1.5em !important;
        font-weight: bold !important;
        width: 100% !important;
        border-radius: 0px !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .button-container button:hover {
        background-color: rgba(26, 61, 52, 0.1) !important;
    }
    
    /* Suchfeld */
    div.stTextInput > div > div > input {
        color: #000 !important;
        font-weight: bold !important;
        background-color: white !important;
        border-radius: 10px !important;
        padding: 12px !important;
        border: 2px solid #ddd !important;
    }
    
    /* Mobile Optimierung */
    @media (max-width: 600px) {
        .header-block {
            padding: 20px 15px 10px 15px !important;
        }
        
        .symbol-price-row {
            flex-direction: column !important;
            gap: 10px !important;
            text-align: center !important;
        }
        
        .isin-rsi-row {
            flex-direction: column !important;
            gap: 12px !important;
            text-align: center !important;
        }
        
        .symbol-display {
            font-size: 1.8em !important;
        }
        
        .price-display {
            font-size: 1.5em !important;
        }
        
        .rsi-evaluation-box {
            width: 100% !important;
            min-width: unset !important;
        }
        
        .chart-container {
            margin: 0 15px 10px 15px !important;
            padding: 15px !important;
        }
        
        .button-container {
            margin: 0 15px 20px 15px !important;
        }
        
        .button-container button {
            height: 50px !important;
            font-size: 1.3em !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Session State initialisieren
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

st.title("📈 RSI Tracker Pro")

# --- SUCHE ---
search = st.text_input("Aktie suchen (Name/Symbol/WKN):", placeholder="z.B. Apple, AAPL, US0378331005...")
if len(search) > 1:
    try:
        res = yf.Search(search, max_results=5).quotes
        if res:
            options = {}
            for r in res:
                if r.get('shortname') and r.get('symbol'):
                    name = r.get('shortname', 'Unbekannt')
                    symbol = r.get('symbol')
                    exchange = r.get('exchange', '')
                    options[f"{name} ({symbol})"] = symbol
            
            if options:
                selected = st.selectbox("Wähle eine Aktie:", list(options.keys()))
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("➕ Hinzufügen", use_container_width=True):
                        symbol_to_add = options[selected]
                        if symbol_to_add not in st.session_state.watchlist:
                            st.session_state.watchlist.append(symbol_to_add)
                            add_to_db(symbol_to_add)
                            st.rerun()
    except Exception as e:
        st.warning("Suche konnte nicht durchgeführt werden.")

st.divider()

# --- ANZEIGE DER AKTIEN-MODULE ---
if st.session_state.watchlist:
    try:
        all_data = yf.download(
            st.session_state.watchlist, 
            period="3mo", 
            interval="1d", 
            progress=False,
            group_by='ticker'
        )
    except:
        st.error("Fehler beim Laden der Aktiendaten")
        all_data = None
    
    if all_data is not None and not all_data.empty:
        for i, ticker in enumerate(st.session_state.watchlist):
            color = COLORS[i % len(COLORS)]
            
            # CSS für jedes Modul mit eigener Farbe
            st.markdown(f"""
                <style>
                .stock-module-{i} {{
                    background-color: {color} !important;
                }}
                </style>
            """, unsafe_allow_html=True)
            
            # ÄUSSERER MODUL-RAHMEN
            with st.container():
                st.markdown(f'<div class="stock-module stock-module-{i}">', unsafe_allow_html=True)
                
                try:
                    # Daten extrahieren
                    if len(st.session_state.watchlist) > 1:
                        df = all_data[ticker].copy()
                    else:
                        df = all_data.copy()
                    
                    if not df.empty and len(df) > 14:
                        # Berechnungen
                        rsi_series = calc_rsi(df['Close'])
                        rsi_value = rsi_series.iloc[-1]
                        current_price = df['Close'].iloc[-1]
                        
                        # RSI Text mit Farbe
                        if rsi_value > 70:
                            rsi_text = "Überkauft"
                            rsi_color = "#ff4444"
                        elif rsi_value < 30:
                            rsi_text = "Überverkauft"
                            rsi_color = "#44ff44"
                        else:
                            rsi_text = "Neutral"
                            rsi_color = "#ffaa00"
                        
                        # Versuche ISIN zu bekommen
                        try:
                            info = yf.Ticker(ticker).info
                            isin = info.get('isin', f"ISIN: unbekannt")
                            if isin == '-':
                                isin = f"ISIN: unbekannt"
                        except:
                            isin = f"ISIN: unbekannt"
                        
                        # --- HEADER WIE AUF DEM BILD ---
                        st.markdown(f"""
                            <div class="header-block">
                                <div class="symbol-price-row">
                                    <div class="symbol-display">{ticker}</div>
                                    <div class="price-display">${current_price:.2f}</div>
                                </div>
                                <div class="isin-rsi-row">
                                    <div class="isin-display">{isin}</div>
                                    <div class="rsi-evaluation-box">
                                        RSI: {rsi_value:.1f}<br>
                                        <span style="color: {rsi_color}; font-size: 0.9em;">{rsi_text}</span>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # --- CHART BEREICH ---
                        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                        
                        # RSI Chart
                        fig = go.Figure()
                        
                        # RSI Linie
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=rsi_series,
                            mode='lines',
                            line=dict(color='#1a3d5e', width=3),
                            fill='tozeroy',
                            fillcolor='rgba(26, 61, 94, 0.2)',
                            name='RSI (14)'
                        ))
                        
                        # Überkauft/Überverkauft Linien
                        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.7)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.7)
                        
                        # Layout
                        fig.update_layout(
                            height=220,
                            margin=dict(l=5, r=5, t=10, b=5),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#333", size=10),
                            xaxis=dict(
                                showgrid=False,
                                showticklabels=True,
                                tickformat="%b %d",
                                tickangle=0
                            ),
                            yaxis=dict(
                                range=[0, 100],
                                showgrid=False,
                                title_text="RSI",
                                tickvals=[0, 30, 50, 70, 100]
                            ),
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # --- BUTTON BEREICH ---
                        st.markdown('<div class="button-container">', unsafe_allow_html=True)
                        
                        if st.button(f"🗑️ {ticker} entfernen", key=f"remove_{ticker}", use_container_width=True):
                            st.session_state.watchlist.remove(ticker)
                            remove_from_db(ticker)
                            st.rerun()
                            
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    else:
                        st.error(f"Nicht genügend Daten für {ticker}")
                        
                except Exception as e:
                    st.error(f"Fehler bei {ticker}")
                    
                st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.warning("Keine Aktiendaten verfügbar.")
        
else:
    st.info("Deine Watchlist ist leer. Suche oben nach Aktien und füge sie hinzu!")

# Info Footer
st.markdown("---")
st.caption("📊 **RSI Tracker Pro** • Relative Strength Index (14 Tage) • Daten von Yahoo Finance")
