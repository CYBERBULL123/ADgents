"""
LangChain Integration for ADgents
Integrates LangChain's advanced agents and chains with ADgents framework.
"""

from typing import Any, Dict, List, Optional, Callable
from langchain.agents import Agent, AgentExecutor, Tool
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import OpenAI
import json
import logging

logger = logging.getLogger(__name__)


class LangChainAdapter:
    """
    Adapter to integrate LangChain agents with ADgents.
    Allows using LangChain's advanced agent features while maintaining ADgents API.
    """

    def __init__(self, llm=None, memory_buffer_size: int = 10):
        """
        Initialize LangChain adapter.
        
        Args:
            llm: LangChain LLM instance (default: OpenAI)
            memory_buffer_size: Size of conversation memory buffer
        """
        self.llm = llm
        self.memory = ConversationBufferMemory(k=memory_buffer_size)
        self.executor = None
        self.tools: Dict[str, Tool] = {}

    def register_skill_as_tool(self, skill_name: str, skill_description: str, 
                               skill_handler: Callable, skill_params: Dict) -> Tool:
        """
        Convert an ADgents Skill to a LangChain Tool.
        
        Args:
            skill_name: Name of the skill
            skill_description: What the tool does
            skill_handler: Function to execute
            skill_params: Parameter schema for the skill
        
        Returns:
            LangChain Tool instance
        """
        def skill_executor(input_str: str) -> str:
            try:
                # Parse input if it's JSON
                if isinstance(input_str, str) and input_str.startswith('{'):
                    input_data = json.loads(input_str)
                else:
                    input_data = {"query": input_str}
                
                result = skill_handler(**input_data)
                return str(result)
            except Exception as e:
                logger.error(f"Error executing skill {skill_name}: {e}")
                return f"Error: {str(e)}"

        tool = Tool(
            name=skill_name,
            func=skill_executor,
            description=f"{skill_description}\n\nParameters: {json.dumps(skill_params)}"
        )
        
        self.tools[skill_name] = tool
        return tool

    def create_agent_executor(self, agent_type: str = "zero-shot-react-description") -> AgentExecutor:
        """
        Create a LangChain agent executor with registered tools.
        
        Args:
            agent_type: Type of agent ("zero-shot-react-description", "react-docstore", etc.)
        
        Returns:
            Configured AgentExecutor instance
        """
        if not self.tools:
            logger.warning("No tools registered for agent")
            return None

        from langchain.agents import initialize_agent, AgentType
        
        agent_type_map = {
            "zero-shot-react-description": AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            "react-docstore": AgentType.REACT_DOCSTORE,
            "self-ask-with-search": AgentType.SELF_ASK_WITH_SEARCH,
            "conversational-react-description": AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        }
        
        agent_enum = agent_type_map.get(agent_type, AgentType.ZERO_SHOT_REACT_DESCRIPTION)
        
        self.executor = initialize_agent(
            tools=list(self.tools.values()),
            llm=self.llm,
            agent=agent_enum,
            memory=self.memory,
            verbose=True,
            max_iterations=10,
            early_stopping_method="generate"
        )
        
        return self.executor

    async def run_agent(self, user_query: str) -> Dict[str, Any]:
        """
        Run the agent with a user query.
        
        Args:
            user_query: The user's input/question
        
        Returns:
            Result dict with output and reasoning
        """
        if not self.executor:
            return {
                "success": False,
                "error": "Agent executor not initialized. Call create_agent_executor first."
            }

        try:
            result = self.executor.run(user_query)
            return {
                "success": True,
                "output": result,
                "memory": self.memory.buffer,
            }
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": None,
            }

    def get_memory_summary(self) -> str:
        """Get conversation memory summary."""
        return self.memory.buffer if self.memory else ""

    def clear_memory(self):
        """Clear conversation memory."""
        if self.memory:
            self.memory.clear()


class DeepAgentAdapter:
    """
    Adapter for LangChain's DeepAgent capability.
    Enables deep reasoning and multi-step task planning.
    """

    def __init__(self, langchain_adapter: LangChainAdapter):
        self.adapter = langchain_adapter
        self.reasoning_chain = None

    def enable_deep_reasoning(self):
        """Enable deep reasoning mode for complex tasks."""
        # This would configure the agent for deep reasoning
        # Using chain-of-thought and extended reasoning
        pass

    def decompose_task(self, task: str) -> List[Dict]:
        """
        Decompose a complex task into subtasks.
        
        Args:
            task: The main task to decompose
        
        Returns:
            List of subtasks with parameters
        """
        # This would use LLM to break down tasks
        return []


# Helper function to integrate with ADgents agents
def create_langchain_agent_from_adgent(adgent, llm=None, skills_list: List[Any] = None):
    """
    Convert an ADgents Agent to use LangChain backend.
    
    Args:
        adgent: The ADgents agent instance
        llm: Optional LangChain LLM instance
        skills_list: List of ADgents Skill objects to register
    
    Returns:
        Configured LangChainAdapter instance
    """
    adapter = LangChainAdapter(llm=llm)
    
    if skills_list:
        for skill in skills_list:
            adapter.register_skill_as_tool(
                skill_name=skill.name,
                skill_description=skill.description,
                skill_handler=skill.handler,
                skill_params=skill.parameters
            )
    
    adapter.create_agent_executor()
    return adapter
