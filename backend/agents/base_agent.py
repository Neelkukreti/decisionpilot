"""
Base agent class for multi-agent orchestration
All specialized agents inherit from this
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import time
import os


@dataclass
class AgentResponse:
    """Standardized agent response"""
    agent_name: str
    output: Dict[str, Any]
    reasoning: str
    execution_time_ms: float
    token_usage: Dict[str, int]
    citations: List[str]
    success: bool = True
    error: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all Nova-powered agents"""
    
    def __init__(self, agent_name: str, model_id: str = 'amazon.nova-lite-v1:0'):
        self.agent_name = agent_name
        self.model_id = model_id
        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        
        if self.mock_mode:
            print(f"⚠️  {agent_name} running in MOCK MODE (no AWS calls)")
        else:
            # Only import boto3 if not in mock mode
            try:
                import boto3
                self.bedrock = boto3.client(
                    'bedrock-runtime',
                    region_name=os.getenv('AWS_REGION', 'us-east-1')
                )
            except Exception as e:
                print(f"⚠️  {agent_name}: AWS not configured, falling back to mock mode")
                self.mock_mode = True
    
    def invoke(
        self, 
        prompt: str, 
        system_prompt: str = None, 
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> AgentResponse:
        """
        Invoke Nova model with structured response tracking
        Falls back to mock mode if AWS not available
        """
        start_time = time.time()
        
        if self.mock_mode:
            return self._mock_invoke(prompt, system_prompt)
        
        try:
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            
            body = {
                "messages": messages,
                "inferenceConfig": {
                    "temperature": temperature,
                    "maxTokens": max_tokens,
                    "topP": 0.9
                }
            }
            
            if system_prompt:
                body["system"] = [{"text": system_prompt}]
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            result = json.loads(response['body'].read())
            output_text = result['output']['message']['content'][0]['text']
            
            execution_time = (time.time() - start_time) * 1000
            
            return AgentResponse(
                agent_name=self.agent_name,
                output=self._parse_output(output_text),
                reasoning=output_text,
                execution_time_ms=execution_time,
                token_usage={
                    'input': result.get('usage', {}).get('inputTokens', 0),
                    'output': result.get('usage', {}).get('outputTokens', 0)
                },
                citations=self._extract_citations(output_text),
                success=True
            )
            
        except Exception as e:
            print(f"❌ {self.agent_name} invocation failed: {e}")
            # Fall back to mock
            return self._mock_invoke(prompt, system_prompt, error=str(e))

    def invoke_with_images(
        self,
        prompt: str,
        images: list,
        system_prompt: str = None,
        temperature: float = 0.0,
        max_tokens: int = 2000
    ) -> 'AgentResponse':
        """
        Invoke Nova Lite with multimodal content (images + text).
        images: [{"format": "jpeg"|"png"|"webp", "data": <base64_bytes>}, ...]
        Falls back to mock if AWS not available or images list is empty.
        """
        start_time = time.time()

        if self.mock_mode or not images:
            return self._mock_invoke(prompt, system_prompt)

        try:
            content = []
            for img in images:
                content.append({
                    "image": {
                        "format": img["format"],
                        "source": {"bytes": img["data"]}
                    }
                })
            content.append({"text": prompt})

            body = {
                "messages": [{"role": "user", "content": content}],
                "inferenceConfig": {
                    "temperature": temperature,
                    "maxTokens": max_tokens,
                    "topP": 0.9
                }
            }
            if system_prompt:
                body["system"] = [{"text": system_prompt}]

            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )

            result = json.loads(response['body'].read())
            output_text = result['output']['message']['content'][0]['text']
            execution_time = (time.time() - start_time) * 1000

            return AgentResponse(
                agent_name=self.agent_name,
                output=self._parse_output(output_text),
                reasoning=output_text,
                execution_time_ms=execution_time,
                token_usage={
                    'input':  result.get('usage', {}).get('inputTokens', 0),
                    'output': result.get('usage', {}).get('outputTokens', 0)
                },
                citations=self._extract_citations(output_text),
                success=True
            )

        except Exception as e:
            print(f"❌ {self.agent_name} multimodal invocation failed: {e}")
            return self._mock_invoke(prompt, system_prompt, error=str(e))
    
    def _mock_invoke(
        self, 
        prompt: str, 
        system_prompt: str = None,
        error: str = None
    ) -> AgentResponse:
        """Mock implementation for testing without AWS"""
        
        time.sleep(0.1)  # Simulate network latency
        
        mock_output = self._generate_mock_output(prompt)
        
        return AgentResponse(
            agent_name=self.agent_name,
            output=mock_output,
            reasoning=f"MOCK: Generated response for {self.agent_name}",
            execution_time_ms=100.0,
            token_usage={'input': 100, 'output': 50},
            citations=['[1]', '[2]'],
            success=True,
            error=error
        )
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Each agent must implement its execution logic
        
        Args:
            context: Input data specific to the agent
            
        Returns:
            AgentResponse with results
        """
        pass
    
    @abstractmethod
    def _generate_mock_output(self, prompt: str) -> Dict[str, Any]:
        """
        Generate mock output for testing
        Each agent implements its own mock logic
        """
        pass
    
    def _parse_output(self, text: str) -> Dict:
        """Extract JSON from LLM response"""
        try:
            # Find JSON block
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
            return {"raw_text": text}
        except:
            return {"raw_text": text}
    
    def _extract_citations(self, text: str) -> List[str]:
        """Extract [1], [2] style citations"""
        import re
        return re.findall(r'\[(\d+)\]', text)
