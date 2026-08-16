"""
ADgents Agent OS — SRE Supervisor Agent
A privileged diagnostic agent that monitors agent pod execution, analyzes errors,
and applies memory or configuration patches to heal failing agents.
"""
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .llm import LLM_ROUTER
from .trace_db import (
    create_healing_intervention,
    get_pod,
    get_span,
    get_trace_spans,
    update_span,
    update_pod
)

logger = logging.getLogger(__name__)

SRE_DIAGNOSTIC_PROMPT = """You are the ADgents SRE Supervisor Agent (Site Reliability Engineering Kernel). 
Your job is to diagnose why a running Agent Pod failed during its execution and apply a corrective patch (Self-Healing) to keep it working.

## Target Agent Information
- Role: {agent_role}
- Backstory: {agent_backstory}
- Available Skills: {agent_skills}

## Master Task assigned to Pod
{task_text}

## Recent Execution History (Spans)
{history_spans}

## Failed Step Details
- Span ID: {failed_span_id}
- Step Name: {failed_span_name}
- Type: {failed_span_type}
- Input: {failed_span_input}
- Error Message: {error_message}

## Healing Requirements
You must formulate:
1. **Diagnosis**: Explain exactly why this step failed (e.g. missing dependencies, loop repetitiveness, bad inputs, context truncation).
2. **Patch Type**: Choose one of:
   - `memory_append`: Append a critical instruction or correction to the agent's short-term working memory so it knows what went wrong and how to work around it in its next ReAct step.
   - `param_override`: Correct the parameters for the tool call so it can be retried successfully.
3. **Patch Content**: 
   - For `memory_append`: A concise instruction (e.g., "Do not use code_execute for HTTP requests. Use api_call instead with URL: http://...").
   - For `param_override`: A JSON object of corrected arguments to retry the tool call.

Return ONLY a valid JSON object with the following keys. Do not output markdown code blocks or explanations:
{{
  "diagnosis": "Detailed SRE explanation of the failure.",
  "patch_type": "memory_append" | "param_override",
  "patch_content": "Instruction text or JSON arguments"
}}
"""

class SRESupervisor:
    """Central manager for SRE diagnostics and healing interventions."""

    def __init__(self, llm_router=None):
        self.llm = llm_router or LLM_ROUTER

    def diagnose_and_heal(self, pod_id: str, span_id: str, error_message: str, active_agent: Any) -> Dict[str, Any]:
        """
        Diagnose a failed span in a pod, generate a corrective patch,
        apply it to the agent instance, and record the intervention.
        """
        logger.info(f"[SRE Kernel] Diagnosing Pod {pod_id}, Span {span_id}...")
        
        # 1. Gather context from DB
        pod = get_pod(pod_id)
        failed_span = get_span(span_id)
        if not pod or not failed_span:
            raise ValueError(f"Could not find Pod {pod_id} or Span {span_id} in trace database.")
        
        trace_id = failed_span["trace_id"]
        spans = get_trace_spans(trace_id)
        
        # Format execution history
        history_lines = []
        for s in spans[-8:]:  # last 8 steps
            status_symbol = "✅" if s["status"] == "success" else "❌" if s["status"] == "error" else "⏳"
            history_lines.append(
                f"- [{s['started_at']}] {s['name']} ({s['span_type']}): {status_symbol} "
                f"Input: {s['input'][:150] if s['input'] else 'None'} -> Output: {s['output'][:150] if s['output'] else 'None'}"
            )
        history_spans = "\n".join(history_lines)
        
        # Format target agent data
        agent_role = active_agent.persona.role if active_agent else pod["name"]
        agent_backstory = active_agent.persona.backstory if active_agent else ""
        agent_skills = ", ".join(active_agent.persona.skills or []) if active_agent else ""
        
        # 2. Build SRE prompt
        prompt = SRE_DIAGNOSTIC_PROMPT.format(
            agent_role=agent_role,
            agent_backstory=agent_backstory,
            agent_skills=agent_skills,
            task_text=pod["task_text"],
            history_spans=history_spans,
            failed_span_id=span_id,
            failed_span_name=failed_span["name"],
            failed_span_type=failed_span["span_type"],
            failed_span_input=failed_span["input"],
            error_message=error_message
        )
        
        # Create an SRE diagnosis span in the database
        sre_span_id = f"sre_{str(uuid.uuid4())[:8]}"
        create_span(
            span_id=sre_span_id,
            trace_id=trace_id,
            parent_span_id=span_id,
            name="SRE Diagnostic Run",
            span_type="SRE_diagnosis",
            input_data={"failed_span_id": span_id, "error": error_message}
        )
        
        messages = [
            {"role": "system", "content": "You are a system SRE Kernel. Output strictly valid JSON without markdown code-fences."},
            {"role": "user", "content": prompt}
        ]
        
        # 3. Call LLM for diagnosis
        try:
            response = self.llm.complete(messages, temperature=0.1)
            content = response.content.strip()
            
            # Clean up markdown fences
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            patch_data = json.loads(content.strip())
            diagnosis = patch_data.get("diagnosis", "Unspecified error diagnosed.")
            patch_type = patch_data.get("patch_type", "memory_append")
            patch_content = patch_data.get("patch_content", "")
            
            update_span(
                span_id=sre_span_id,
                status="success",
                output={"diagnosis": diagnosis, "patch_type": patch_type, "patch_content": patch_content},
                completed_at=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"[SRE Kernel] Failed to generate diagnosis: {e}")
            diagnosis = f"SRE Diagnosis crashed: {e}"
            patch_type = "memory_append"
            patch_content = f"Note: A system error occurred during step execution: {error_message}. Please retry with a safer alternative."
            
            update_span(
                span_id=sre_span_id,
                status="error",
                error=str(e),
                completed_at=datetime.utcnow().isoformat()
            )
            
        # 4. Apply the patch to the active agent runtime
        intervention_id = f"intv_{str(uuid.uuid4())[:8]}"
        applied = False
        
        if active_agent:
            try:
                if patch_type == "memory_append":
                    # Append error context to working memory
                    healing_instruction = (
                        f"\n\n[SRE KERNEL SYSTEM INTERVENTION]\n"
                        f"Your previous action resulted in an error:\n"
                        f"Error: {error_message}\n"
                        f"Diagnosis: {diagnosis}\n"
                        f"Instruction: {patch_content}\n"
                        f"Please incorporate this diagnosis and adjust your strategy. Do NOT repeat the failing command."
                    )
                    active_agent.memory.working.add_message("system", healing_instruction)
                    applied = True
                    logger.info(f"[SRE Kernel] Injected memory patch into Pod {pod_id} working memory.")
                    
                elif patch_type == "param_override":
                    # For param_override, we save the patch content to be handled during execution retry.
                    # We will log it here, and the ReAct loop executor will read this and use it.
                    applied = True
                    logger.info(f"[SRE Kernel] Prepared parameter override patch for Pod {pod_id}.")
                    
            except Exception as patch_err:
                logger.error(f"[SRE Kernel] Failed to apply patch: {patch_err}")
                diagnosis += f"\nPatch application failed: {patch_err}"
        
        # 5. Record intervention and update Pod status
        create_healing_intervention(
            intervention_id=intervention_id,
            pod_id=pod_id,
            span_id=span_id,
            error_message=error_message,
            diagnosis=diagnosis,
            patch_type=patch_type,
            patch_content=str(patch_content)
        )
        
        # Put Pod back to RUNNING after applying patch (or FAILED if patch application completely failed)
        new_status = "running" if applied else "failed"
        update_pod(pod_id, status=new_status)
        
        return {
            "intervention_id": intervention_id,
            "diagnosis": diagnosis,
            "patch_type": patch_type,
            "patch_content": patch_content,
            "applied": applied
        }

# Global SRE Supervisor instance
SRE_SUPERVISOR = SRESupervisor()
