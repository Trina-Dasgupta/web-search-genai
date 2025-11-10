from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import TypedDict, Callable
from langchain_tavily import TavilySearch
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


class State(TypedDict):
    topic: str
    search_results: str
    summary: str
    report: str


class ResearchGraph:
    def __init__(self):
        self.search_tool = TavilySearch(max_results=3)
        self.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        
        self.summary_prompt = ChatPromptTemplate.from_template(
            "Summarize this text clearly:\n{content}"
        )
        self.summary_chain = self.summary_prompt | self.llm
        
        self.report_prompt = ChatPromptTemplate.from_template(
            "Write a detailed report with citations based on this summary:\n{summary}"
        )
        self.report_chain = self.report_prompt | self.llm

        self.app = self._build_graph()
    
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
        return {"report": report.content}
    
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


if __name__ == "__main__":
    graph = ResearchGraph()
    result = graph.run_sync("Impact of quantum computing on cybersecurity")
    print(result["report"])