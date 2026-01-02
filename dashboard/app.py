import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
import plotly.graph_objects as go
from datetime import datetime
import glob
import sys
from dotenv import load_dotenv

# Add parent dir to path to import security
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tradingagents.security import DataProtection
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Load environment variables
load_dotenv()

# Bridge for Streamlit Cloud Secrets (if running online)
if hasattr(st, "secrets"):
    for key, value in st.secrets.items():
        if key not in os.environ:
            os.environ[key] = str(value)

st.set_page_config(page_title="TradingAgents Monitor", layout="wide")
st.title("🤖 TradingAgents Monitoring Dashboard")

# Initialize Security
security = DataProtection()

# Sidebar configuration
st.sidebar.header("Configuration")
results_dir = st.sidebar.text_input("Results Directory", "./results")
live_dir = os.path.join(results_dir, "live")
historical_dir = results_dir

# Tabs
tab1, tab2, tab3 = st.tabs(["🚀 Run Analysis", "🔴 Live Pipeline Monitor", "📚 Historical Reports"])

def load_json_file(filepath):
    """Load and optionally decrypt a JSON file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Try to parse as JSON directly
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If valid JSON fails, it might be encrypted
            try:
                decrypted_bytes = security.decrypt_file(filepath)
                if decrypted_bytes:
                    return json.loads(decrypted_bytes.decode())
            except Exception:
                pass
            return None
    except Exception as e:
        return None

with tab1:
    st.header("Start New Analysis")
    
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        ticker_input = st.text_input("Ticker Symbol", value="RELIANCE.NS", help="e.g. RELIANCE.NS, TCS.NS, SPY, AAPL")
    
    with col_input2:
        date_input = st.date_input("Analysis Date", datetime.now())
    
    analysts_options = ["market", "social", "news", "fundamentals"]
    selected_analysts = st.multiselect("Select Analysts", analysts_options, default=analysts_options)
    
    if st.button("🚀 Start Analysis", type="primary"):
        if not ticker_input:
            st.error("Please enter a ticker symbol.")
        else:
            status_container = st.status("Initializing agents...", expanded=True)
            try:
                # Initialize Graph
                status_container.write("Initializing Trading Agents Graph...")
                graph = TradingAgentsGraph(
                    selected_analysts=selected_analysts,
                    config=DEFAULT_CONFIG,
                    debug=True # Debug true might print to console, but we want to capture it if possible. 
                               # For now, we just let it run.
                )
                
                # Run Analysis
                date_str = date_input.strftime("%Y-%m-%d")
                status_container.write(f"Running propagation for {ticker_input} on {date_str}...")
                status_container.write("Agents are gathering data and debating... (This may take a minute)")
                
                # Execute
                final_state, decision = graph.propagate(ticker_input, date_str)
                
                status_container.update(label="Analysis Complete!", state="complete", expanded=False)
                
                st.success(f"Analysis completed for {ticker_input}")
                
                # Display Results
                st.divider()
                st.subheader("🏆 Final Decision")
                
                # Parse decision for display
                decision_action = "UNKNOWN"
                decision_reason = ""
                if isinstance(decision, dict):
                    decision_action = decision.get("action", "UNKNOWN")
                    decision_reason = str(decision)
                else:
                    decision_action = str(decision)
                
                metric_col1, metric_col2 = st.columns([1, 3])
                metric_col1.metric("Recommendation", decision_action)
                
                with metric_col2:
                    st.info(f"**Decision Details:**\n\n{decision_reason}")

                # Display detailed reports from final_state
                st.subheader("📝 Detailed Reports")
                
                # Helper to display report if exists
                def display_report_tab(title, content_key):
                    if final_state.get(content_key):
                        with st.expander(title):
                            st.markdown(final_state[content_key])

                display_report_tab("Market Analysis", "market_report")
                display_report_tab("Social Sentiment", "sentiment_report")
                display_report_tab("News Analysis", "news_report")
                display_report_tab("Fundamentals", "fundamentals_report")
                
                # Debate and Plans
                if final_state.get("trader_investment_plan"):
                    with st.expander("💰 Trading Plan", expanded=True):
                        st.markdown(final_state["trader_investment_plan"])
                
                if final_state.get("investment_debate_state", {}).get("judge_decision"):
                    with st.expander("⚖️ Research Consensus"):
                        st.markdown(final_state["investment_debate_state"]["judge_decision"])
                
                if final_state.get("final_trade_decision"): # Sometimes this holds the final rationale
                     with st.expander("🏁 Portfolio Manager Final Rationale"):
                        st.markdown(final_state["final_trade_decision"])

                # Save results automatically
                save_path = Path(results_dir) / ticker_input / date_str
                save_path.mkdir(parents=True, exist_ok=True)
                
                # Save reports
                reports_dir = save_path / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                
                if final_state.get("market_report"):
                    with open(reports_dir / "market_report.md", "w") as f: f.write(final_state["market_report"])
                # ... (saving all reports is good, but for now we rely on the graph or just the main JSON)
                
                # Save full state JSON like realtime runner
                output_data = {
                    "timestamp": datetime.now().isoformat(),
                    "ticker": ticker_input,
                    "decision": decision,
                    "final_state": final_state
                }
                json_path = save_path / "analysis_result.json"
                with open(json_path, "w") as f:
                    json.dump(output_data, f, indent=2, default=str)
                st.toast(f"Result saved to {json_path}")

            except Exception as e:
                status_container.update(label="Analysis Failed", state="error")
                st.error(f"An error occurred during analysis: {str(e)}")
                st.exception(e)

with tab1:
    st.header("Real-time Analysis Runs")
    
    if os.path.exists(live_dir):
        files = glob.glob(os.path.join(live_dir, "*.json"))
        files.sort(key=os.path.getmtime, reverse=True)
        
        if not files:
            st.info("No live run data found.")
        else:
            # Load latest run
            latest_file = files[0]
            data = load_json_file(latest_file)
            
            if data:
                # Top metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Latest Ticker", data.get("ticker", "N/A"))
                col2.metric("Timestamp", data.get("timestamp", "N/A"))
                
                decision = data.get("decision", {})
                action = "HOLD"
                if isinstance(decision, str):
                    action = decision
                elif isinstance(decision, dict):
                    action = decision.get("action", "HOLD")
                    
                col3.metric("Latest Decision", action)
                
                # Decision Details
                st.subheader("Decision Logic")
                st.json(decision)
                
                # State Inspection
                with st.expander("Full Agent State"):
                    st.json(data.get("final_state", {}))
                
                # History Table
                st.subheader("Recent Run History")
                history_data = []
                for f in files[:10]:
                    d = load_json_file(f)
                    if d:
                        history_data.append({
                            "Time": d.get("timestamp"),
                            "Ticker": d.get("ticker"),
                            "Decision": str(d.get("decision"))[:50] + "..."
                        })
                
                if history_data:
                    st.dataframe(pd.DataFrame(history_data))
            else:
                st.error("Failed to load or decrypt the latest file.")
    else:
        st.warning(f"Live directory not found: {live_dir}")

with tab2:
    st.header("Historical Analysis Reports")
    
    # List tickers
    if os.path.exists(historical_dir):
        # Assuming structure: results/TICKER/DATE/reports
        tickers = [d for d in os.listdir(historical_dir) if os.path.isdir(os.path.join(historical_dir, d)) and d != "live"]
        
        selected_ticker = st.selectbox("Select Ticker", [""] + tickers)
        
        if selected_ticker:
            ticker_path = os.path.join(historical_dir, selected_ticker)
            dates = [d for d in os.listdir(ticker_path) if os.path.isdir(os.path.join(ticker_path, d))]
            selected_date = st.selectbox("Select Date", [""] + dates)
            
            if selected_date:
                report_path = os.path.join(ticker_path, selected_date, "reports")
                if os.path.exists(report_path):
                    reports = glob.glob(os.path.join(report_path, "*.md"))
                    
                    for report in reports:
                        report_name = os.path.basename(report).replace(".md", "")
                        with st.expander(f"📄 {report_name.replace('_', ' ').title()}"):
                            with open(report, 'r') as f:
                                st.markdown(f.read())
                else:
                    st.info("No reports found for this date.")
    else:
        st.error("Results directory not found.")

st.sidebar.markdown("---")
st.sidebar.caption("TradingAgents Dashboard v1.0")
