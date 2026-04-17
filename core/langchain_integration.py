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
import asyncio
import time
from datetime import datetime, UTC

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
        self.on_thought_callback: Optional[Callable] = None

    def set_thought_callback(self, callback: Callable):
        """Set callback for streaming thoughts to ADgents UI."""
        self.on_thought_callback = callback

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

                # Stream thought about tool usage
                if self.on_thought_callback:
                    self.on_thought_callback({
                        "step_type": "action",
                        "content": f"🔧 Using tool: {skill_name}",
                        "skill_used": skill_name,
                        "timestamp": datetime.now(UTC).isoformat()
                    })

                result = skill_handler(**input_data)

                # Stream tool result
                if self.on_thought_callback:
                    self.on_thought_callback({
                        "step_type": "observation",
                        "content": f"✅ Tool result: {str(result)[:200]}...",
                        "skill_result": str(result),
                        "timestamp": datetime.now(UTC).isoformat()
                    })

                return str(result)
            except Exception as e:
                logger.error(f"Error executing skill {skill_name}: {e}")
                if self.on_thought_callback:
                    self.on_thought_callback({
                        "step_type": "observation",
                        "content": f"❌ Tool error: {str(e)}",
                        "timestamp": datetime.now(UTC).isoformat()
                    })
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
        Run the agent with a user query asynchronously with thought streaming.
        
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
            # Stream initial thought
            if self.on_thought_callback:
                self.on_thought_callback({
                    "step_type": "thought",
                    "content": f"🤔 Analyzing query: {user_query[:100]}...",
                    "timestamp": datetime.now(UTC).isoformat()
                })

            # Run agent in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.executor.run, user_query)

            # Stream completion thought
            if self.on_thought_callback:
                self.on_thought_callback({
                    "step_type": "reflection",
                    "content": f"✅ Agent completed reasoning. Final answer ready.",
                    "timestamp": datetime.now(UTC).isoformat()
                })

            return {
                "success": True,
                "output": result,
                "memory": self.memory.buffer if self.memory else "",
            }
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            if self.on_thought_callback:
                self.on_thought_callback({
                    "step_type": "reflection",
                    "content": f"❌ Agent execution failed: {str(e)}",
                    "timestamp": datetime.now(UTC).isoformat()
                })
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
        self.task_decomposer = None

    def enable_deep_reasoning(self):
        """Enable deep reasoning mode for complex tasks."""
        try:
            from langchain.chains import LLMChain
            from langchain.prompts import PromptTemplate

            # Create a reasoning chain for complex tasks
            reasoning_prompt = PromptTemplate(
                input_variables=["task", "context"],
                template="""
You are an advanced AI agent with deep reasoning capabilities. Break down complex tasks into manageable steps.

Task: {task}

Current Context: {context}

Think step-by-step:
1. Analyze the task requirements
2. Identify key components and dependencies
3. Plan the execution strategy
4. Consider potential challenges
5. Provide a structured approach

Your response should be detailed and methodical.
"""
            )

            if self.adapter.llm:
                self.reasoning_chain = LLMChain(
                    llm=self.adapter.llm,
                    prompt=reasoning_prompt,
                    verbose=True
                )
                logger.info("Deep reasoning enabled")
            else:
                logger.warning("No LLM available for deep reasoning")
        except Exception as e:
            logger.error(f"Failed to enable deep reasoning: {e}")

    async def decompose_task(self, task: str) -> List[Dict]:
        """
        Decompose a complex task into subtasks using LLM.
        
        Args:
            task: The main task to decompose
        
        Returns:
            List of subtasks with parameters
        """
        if not self.reasoning_chain:
            return [{"task": task, "description": "Execute main task"}]

        try:
            # Stream decomposition thought
            if self.adapter.on_thought_callback:
                self.adapter.on_thought_callback({
                    "step_type": "thought",
                    "content": f"🔍 Decomposing complex task: {task[:100]}...",
                    "timestamp": datetime.now(UTC).isoformat()
                })

            # Use LLM to decompose task
            context = self.adapter.memory.buffer if self.adapter.memory else ""
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.reasoning_chain.run,
                task=task,
                context=context
            )

            # Parse result into subtasks (simplified parsing)
            subtasks = []
            lines = result.split('\n')
            current_task = ""

            for line in lines:
                line = line.strip()
                if line.startswith(('1.', '2.', '3.', '4.', '5.', '-')):
                    if current_task:
                        subtasks.append({"task": current_task, "description": current_task})
                    current_task = line.lstrip('12345.- ').strip()
                elif current_task and line:
                    current_task += " " + line

            if current_task:
                subtasks.append({"task": current_task, "description": current_task})

            if not subtasks:
                subtasks = [{"task": task, "description": "Execute main task"}]

            # Stream decomposition result
            if self.adapter.on_thought_callback:
                self.adapter.on_thought_callback({
                    "step_type": "thought",
                    "content": f"📋 Task decomposed into {len(subtasks)} subtasks",
                    "timestamp": datetime.now(UTC).isoformat()
                })

            return subtasks

        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            return [{"task": task, "description": "Execute main task"}]

    async def run_deep_agent(self, task: str) -> Dict[str, Any]:
        """
        Run deep agent with task decomposition and advanced reasoning.
        
        Args:
            task: The complex task to execute
        
        Returns:
            Result with detailed reasoning
        """
        try:
            # Enable deep reasoning if not already enabled
            if not self.reasoning_chain:
                self.enable_deep_reasoning()

            # Decompose task
            subtasks = await self.decompose_task(task)

            results = []
            for i, subtask in enumerate(subtasks, 1):
                if self.adapter.on_thought_callback:
                    self.adapter.on_thought_callback({
                        "step_type": "thought",
                        "content": f"🔄 Executing subtask {i}/{len(subtasks)}: {subtask['task'][:100]}...",
                        "timestamp": datetime.now(UTC).isoformat()
                    })

                # Run subtask
                result = await self.adapter.run_agent(subtask['task'])
                results.append({
                    "subtask": subtask['task'],
                    "result": result.get('output', ''),
                    "success": result.get('success', False)
                })

            # Combine results
            combined_output = "\n\n".join([
                f"Subtask: {r['subtask']}\nResult: {r['result']}"
                for r in results
            ])

            if self.adapter.on_thought_callback:
                self.adapter.on_thought_callback({
                    "step_type": "reflection",
                    "content": f"🎯 Deep agent completed all {len(subtasks)} subtasks",
                    "timestamp": datetime.now(UTC).isoformat()
                })

            return {
                "success": True,
                "output": combined_output,
                "subtasks_completed": len(results),
                "total_subtasks": len(subtasks)
            }

        except Exception as e:
            logger.error(f"Deep agent execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": None
            }


# Helper function to integrate with ADgents agents
def create_langchain_agent_from_adgent(adgent, llm=None, skills_list: List[Any] = None, on_thought_callback: Callable = None):
    """
    Convert an ADgents Agent to use LangChain backend.
    
    Args:
        adgent: The ADgents agent instance
        llm: Optional LangChain LLM instance
        skills_list: List of ADgents Skill objects to register
        on_thought_callback: Callback for streaming thoughts to ADgents UI
    
    Returns:
        Configured LangChainAdapter instance
    """
    adapter = LangChainAdapter(llm=llm)
    
    # Set thought callback for ADgents integration
    if on_thought_callback:
        adapter.set_thought_callback(on_thought_callback)
    
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


def create_deep_langchain_agent_from_adgent(adgent, llm=None, skills_list: List[Any] = None, on_thought_callback: Callable = None):
    """
    Convert an ADgents Agent to use LangChain Deep Agent backend.
    
    Args:
        adgent: The ADgents agent instance
        llm: Optional LangChain LLM instance
        skills_list: List of ADgents Skill objects to register
        on_thought_callback: Callback for streaming thoughts to ADgents UI
    
    Returns:
        Configured DeepAgentAdapter instance
    """
    adapter = LangChainAdapter(llm=llm)
    
    # Set thought callback for ADgents integration
    if on_thought_callback:
        adapter.set_thought_callback(on_thought_callback)
    
    if skills_list:
        for skill in skills_list:
            adapter.register_skill_as_tool(
                skill_name=skill.name,
                skill_description=skill.description,
                skill_handler=skill.handler,
                skill_params=skill.parameters
            )
    
    adapter.create_agent_executor()
    
    # Create deep agent adapter
    deep_adapter = DeepAgentAdapter(adapter)
    deep_adapter.enable_deep_reasoning()
    
    return deep_adapter
