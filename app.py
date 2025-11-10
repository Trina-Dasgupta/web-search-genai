import streamlit as st
from graph_backend import ResearchGraph
import time

# Page config
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS for Perplexity-like styling
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stTextInput > div > div > input {
        font-size: 18px;
        padding: 20px;
    }
    .search-header {
        text-align: center;
        padding: 2rem 0;
    }
    .result-container {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin-top: 2rem;
    }
    .stage-indicator {
        padding: 10px 20px;
        border-radius: 5px;
        margin: 10px 0;
        border-left: 4px solid #2196F3;
    }
    .report-section {
        line-height: 1.8;
        font-size: 16px;
    }
    h1 {
        color: #1a1a1a;
        font-weight: 600;
    }
    .vector-db-indicator {
        background-color: #e8f5e8;
        border-left: 4px solid #4CAF50;
        padding: 10px;
        color: #256029;
        border-radius: 5px;
        margin: 5px 0;
    }
    .web-search-indicator {
        border-left: 4px solid #2196F3;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .error-indicator {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "research_graph" not in st.session_state:
    try:
        st.session_state.research_graph = ResearchGraph()
        st.success("✅ Research Assistant initialized successfully!")
    except Exception as e:
        st.error(f"❌ Failed to initialize Research Assistant: {str(e)}")
        st.session_state.research_graph = None

# Header
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown("<h1 style='text-align: center;'>🔍 AI Research Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Get comprehensive research reports on any topic</p>", unsafe_allow_html=True)

# Search input
with st.container():
    topic = st.text_input(
        "What would you like to research?",
        placeholder="e.g., Impact of quantum computing on cybersecurity",
        label_visibility="collapsed"
    )
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        search_button = st.button("🔍 Research", use_container_width=True, type="primary")

# Process search
if search_button and topic:
    if st.session_state.research_graph is None:
        st.error("Research Assistant is not properly initialized. Please refresh the page.")
    else:
        st.session_state.messages.append({"role": "user", "content": topic})
        
        with st.container():
            st.markdown(f"### 🎯 Researching: *{topic}*")
            
            # Progress indicators
            progress_container = st.container()
            result_container = st.container()
            
            with progress_container:
                # Check vector DB first
                vector_check = st.empty()
                vector_check.markdown(
                    "<div class='vector-db-indicator'>📚 <strong>Checking vector database...</strong></div>",
                    unsafe_allow_html=True
                )
                
                try:
                    # Check if topic exists in vector DB
                    vector_result = st.session_state.research_graph.check_vector_db(topic)
                    
                    if vector_result and vector_result.get("found_in_db", False):
                        vector_check.markdown(
                            f"<div class='vector-db-indicator'>✅ <strong>Found in database! Retrieving cached research...</strong></div>",
                            unsafe_allow_html=True
                        )
                        time.sleep(1)
                        
                        # Display results from vector DB
                        with result_container:
                            st.success("✅ Research retrieved from database!")
                            
                            # Create tabs for different views
                            tab1, tab2, tab3 = st.tabs(["📄 Report", "🔍 Sources", "📊 Summary"])
                            
                            with tab1:
                                st.markdown("<div class='report-section'>", unsafe_allow_html=True)
                                st.markdown(vector_result["report"])
                                st.markdown("</div>", unsafe_allow_html=True)
                                
                                # Download button
                                st.download_button(
                                    label="📥 Download Report",
                                    data=vector_result["report"],
                                    file_name=f"research_report_{topic[:30]}.txt",
                                    mime="text/plain"
                                )
                            
                            with tab2:
                                st.markdown("### Search Results")
                                with st.expander("View raw search data"):
                                    st.text(vector_result.get("search_results", "No search results available"))
                            
                            with tab3:
                                st.markdown("### Executive Summary")
                                st.info(vector_result["summary"])
                        
                        # Save to session state
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": vector_result["report"],
                            "metadata": {
                                "summary": vector_result["summary"],
                                "sources": vector_result.get("search_results", ""),
                                "from_vector_db": True
                            }
                        })
                        
                        vector_check.empty()
                        
                    else:
                        # Not found in vector DB, proceed with web search
                        vector_check.markdown(
                            "<div class='web-search-indicator'>🔍 <strong>Not found in database. Searching the web...</strong></div>",
                            unsafe_allow_html=True
                        )
                        
                        # Stage 1: Searching
                        stage1 = st.empty()
                        stage1.markdown(
                            "<div class='stage-indicator'>🔎 <strong>Searching the web...</strong></div>",
                            unsafe_allow_html=True
                        )
                        time.sleep(0.5)
                        
                        # Stage 2: Analyzing
                        stage2 = st.empty()
                        
                        # Stage 3: Generating Report
                        stage3 = st.empty()
                        
                        # Progress bar
                        progress_bar = st.progress(0)
                        
                        try:
                            # Run the research graph with streaming
                            def update_progress(event):
                                if "search" in event:
                                    progress_bar.progress(33)
                                    stage2.markdown(
                                        "<div class='stage-indicator'>🧠 <strong>Analyzing results...</strong></div>",
                                        unsafe_allow_html=True
                                    )
                                elif "summarize" in event:
                                    progress_bar.progress(66)
                                    stage3.markdown(
                                        "<div class='stage-indicator'>📝 <strong>Generating report...</strong></div>",
                                        unsafe_allow_html=True
                                    )
                            
                            # Execute research
                            result = st.session_state.research_graph.run(topic, stream_callback=update_progress)
                            
                            progress_bar.progress(100)
                            time.sleep(0.3)
                            
                            # Clear progress indicators
                            vector_check.empty()
                            stage1.empty()
                            stage2.empty()
                            stage3.empty()
                            progress_bar.empty()
                            
                            # Display results
                            with result_container:
                                st.success("✅ Research complete! (Saved to database)")
                                
                                # Create tabs for different views
                                tab1, tab2, tab3 = st.tabs(["📄 Report", "🔍 Sources", "📊 Summary"])
                                
                                with tab1:
                                    st.markdown("<div class='report-section'>", unsafe_allow_html=True)
                                    st.markdown(result["report"])
                                    st.markdown("</div>", unsafe_allow_html=True)
                                    
                                    # Download button
                                    st.download_button(
                                        label="📥 Download Report",
                                        data=result["report"],
                                        file_name=f"research_report_{topic[:30]}.txt",
                                        mime="text/plain"
                                    )
                                
                                with tab2:
                                    st.markdown("### Search Results")
                                    with st.expander("View raw search data"):
                                        st.text(result["search_results"])
                                
                                with tab3:
                                    st.markdown("### Executive Summary")
                                    st.info(result["summary"])
                            
                            # Save to session state
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": result["report"],
                                "metadata": {
                                    "summary": result["summary"],
                                    "sources": result["search_results"],
                                    "from_vector_db": False
                                }
                            })
                            
                        except Exception as e:
                            progress_bar.empty()
                            vector_check.empty()
                            stage1.empty()
                            stage2.empty()
                            stage3.empty()
                            st.error(f"❌ An error occurred during research: {str(e)}")
                            
                except Exception as e:
                    vector_check.markdown(
                        f"<div class='error-indicator'>❌ <strong>Error checking database: {str(e)}</strong></div>",
                        unsafe_allow_html=True
                    )
                    st.error(f"Database error: {str(e)}")

# Display conversation history
if len(st.session_state.messages) > 0:
    st.markdown("---")
    st.markdown("### 📚 Research History")
    
    for i, msg in enumerate(reversed(st.session_state.messages)):
        if msg["role"] == "user":
            with st.expander(f"🔍 {msg['content']}", expanded=False):
                if i > 0 and st.session_state.messages[-(i)]["role"] == "assistant":
                    assistant_msg = st.session_state.messages[-(i)]
                    source_info = " (from database)" if assistant_msg.get("metadata", {}).get("from_vector_db") else " (from web search)"
                    st.markdown(f"**Source:**{source_info}")
                    st.markdown(assistant_msg["content"])

# Sidebar with info
with st.sidebar:
    st.markdown("## ℹ️ About")
    st.markdown("""
    This AI Research Assistant uses:
    - **Vector Database**: Fast retrieval of cached research
    - **Web Search**: Real-time information gathering when needed
    - **AI Analysis**: Intelligent summarization
    - **Report Generation**: Comprehensive reports with citations
    """)
    
    st.markdown("---")
    st.markdown("## 🎯 Example Topics")
    example_topics = [
        "Impact of AI on healthcare",
        "Climate change solutions 2024",
        "Latest developments in renewable energy",
        "Blockchain technology applications"
    ]
    
    for example in example_topics:
        if st.button(example, key=f"example_{example}"):
            st.session_state.example_topic = example
            st.rerun()
    
    st.markdown("---")
    
    if st.button("🗑️ Clear History"):
        st.session_state.messages = []
        st.rerun()
    
    # Vector DB stats
    if st.button("📊 Database Info"):
        try:
            if st.session_state.research_graph:
                stats = st.session_state.research_graph.get_vector_db_stats()
                st.markdown("### Database Statistics")
                st.write(f"Total research topics: {stats.get('total_topics', 0)}")
            else:
                st.info("Research Assistant not initialized")
        except Exception as e:
            st.info(f"Database statistics not available: {e}")