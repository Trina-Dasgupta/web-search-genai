from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
from typing import TypedDict, Callable
from langchain_tavily import TavilySearch
from langchain_core.prompts import ChatPromptTemplate
import chromadb
import json
import hashlib
import uuid

load_dotenv()


class State(TypedDict):
    topic: str
    search_results: str
    summary: str
    report: str
    found_in_db: bool


class ResearchGraph:
    def __init__(self):
        self.search_tool = TavilySearch(max_results=3)
        self.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        self.embeddings = OpenAIEmbeddings()
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path="./research_db")
        self.collection = self.client.get_or_create_collection(
            name="research_reports",
            metadata={"description": "Stores research reports and summaries"}
        )
        
        self.summary_prompt = ChatPromptTemplate.from_template(
            "Summarize this text clearly:\n{content}"
        )
        self.summary_chain = self.summary_prompt | self.llm
        
        self.report_prompt = ChatPromptTemplate.from_template(
            "Write a detailed report with citations based on this summary:\n{summary}"
        )
        self.report_chain = self.report_prompt | self.llm

        self.app = self._build_graph()
    
    def _get_topic_hash(self, topic: str) -> str:
        """Generate a consistent hash for the topic"""
        return hashlib.md5(topic.encode()).hexdigest()
    
    def check_vector_db(self, topic: str) -> dict:
        """Check if research exists in vector database"""
        try:
            topic_hash = self._get_topic_hash(topic)
            
            # Search for similar topics
            results = self.collection.get(
                where={"topic_hash": topic_hash},
                include=["metadatas", "documents"]
            )
            
            if results['ids']:
                # Found in database
                metadata = results['metadatas'][0]
                return {
                    "found_in_db": True,
                    "report": results['documents'][0],
                    "summary": metadata.get('summary', ''),
                    "search_results": metadata.get('search_results', ''),
                    "topic": metadata.get('topic', topic)
                }
            else:
                # Not found in database
                return {"found_in_db": False}
                
        except Exception as e:
            print(f"Error checking vector DB: {e}")
            return {"found_in_db": False}
    
    def save_to_vector_db(self, state: State):
        """Save research results to vector database"""
        try:
            topic_hash = self._get_topic_hash(state["topic"])
            
            # Generate embedding for the report
            report_embedding = self.embeddings.embed_query(state["report"])
            
            # Prepare metadata
            metadata = {
                "topic": state["topic"],
                "topic_hash": topic_hash,
                "summary": state["summary"],
                "search_results": state.get("search_results", ""),
                "timestamp": str(uuid.uuid4())
            }
            
            # Store in ChromaDB
            self.collection.add(
                ids=[topic_hash],
                embeddings=[report_embedding],
                metadatas=[metadata],
                documents=[state["report"]]
            )
            
            print(f"Research saved to vector DB for topic: {state['topic']}")
            
        except Exception as e:
            print(f"Error saving to vector DB: {e}")
    
    def search_node(self, state: State):
        """Search for information on the topic"""
        results = self.search_tool.invoke(state["topic"])
        return {"search_results": str(results)}
    
    def summarize_node(self, state: State):
        """Summarize the search results"""
        summary = self.llm.invoke(f"summarize:{state['search_results']}")
        return {"summary": summary.content}
    
    def report_node(self, state: State):
        """Generate a detailed report from the summary"""
        report = self.report_chain.invoke({"summary": state["summary"]})
        
        # Prepare final state
        final_state = {
            "report": report.content,
            "summary": state["summary"],
            "search_results": state["search_results"],
            "topic": state["topic"],
            "found_in_db": False
        }
        
        # Save to vector DB
        self.save_to_vector_db(final_state)
        
        return final_state
    
    def _build_graph(self):
        """Build and compile the LangGraph workflow"""
        graph = StateGraph(State)
        
        # Add nodes
        graph.add_node("search", self.search_node)
        graph.add_node("summarize", self.summarize_node)
        graph.add_node("report", self.report_node)
        
        # Add edges
        graph.add_edge("search", "summarize")
        graph.add_edge("summarize", "report")
        
        # Set entry and finish points
        graph.set_entry_point("search")
        graph.set_finish_point("report")
        
        return graph.compile()
    
    def run(self, topic: str, stream_callback: Callable = None):
        """
        Run the research workflow
        
        Args:
            topic: The research topic
            stream_callback: Optional callback function to stream intermediate results
        
        Returns:
            Dictionary containing the final state with report
        """
        if stream_callback:
            # Stream intermediate results
            for event in self.app.stream({"topic": topic}):
                stream_callback(event)
        
        # Return final result
        result = self.app.invoke({"topic": topic})
        return result
    
    def run_sync(self, topic: str):
        """Run the workflow synchronously and return the final result"""
        return self.app.invoke({"topic": topic})
    
    def get_vector_db_stats(self):
        """Get statistics about the vector database"""
        try:
            count = self.collection.count()
            return {"total_topics": count}
        except Exception as e:
            print(f"Error getting DB stats: {e}")
            return {"total_topics": 0}


if __name__ == "__main__":
    graph = ResearchGraph()
    
    # Test with a sample topic
    topic = "Impact of quantum computing on cybersecurity"
    
    # First check vector DB
    cached_result = graph.check_vector_db(topic)
    if cached_result["found_in_db"]:
        print("Found in database!")
        print(cached_result["report"])
    else:
        print("Not in database, searching web...")
        result = graph.run_sync(topic)
        print(result["report"])