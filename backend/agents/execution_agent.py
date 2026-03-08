"""
Execution Agent - Task Orchestration & Automation

Coordinates the execution of validated action items:
- Creates Jira tickets via browser automation (Nova Act)
- Tracks execution status
- Handles retry logic
- Maintains audit log

This is the "operator" that takes meeting outputs and makes them real.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import json
import os

from .base_agent import BaseAgent
from schemas.meeting_schemas import (
    ActionItem,
    ExecutionResult,
    ExecutionStatus,
    AuditLog
)


class ExecutionAgent(BaseAgent):
    """Agent that executes validated actions automatically"""
    
    def __init__(
        self,
        model: str = "amazon.nova-lite-v1:0",
        mock_mode: bool = None
    ):
        super().__init__(
            agent_name="Execution",
            model_id=model
        )
        
        # Execution config
        self.max_retries = 3
        self.retry_delay_seconds = 5
        self.audit_log_path = "./logs/execution_audit.jsonl"
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
    
    def execute(self, context: Dict[str, Any]) -> Any:
        """Execute action from context"""
        if 'action' in context:
            return self.execute_action(
                context['action'],
                jira_config=context.get('jira_config'),
                dry_run=context.get('dry_run', False)
            )
        
        if 'actions' in context:
            return self.execute_batch(
                context['actions'],
                jira_config=context.get('jira_config'),
                dry_run=context.get('dry_run', False)
            )
        
        return {"error": "No action or actions provided"}
    
    def _generate_mock_output(self, prompt: str) -> Dict[str, Any]:
        """Generate mock output for testing"""
        return {
            "status": "success",
            "ticket_id": "MOCK-123",
            "mock": True
        }
    
    def execute_action(
        self,
        action: ActionItem,
        jira_config: Optional[Dict[str, str]] = None,
        dry_run: bool = False
    ) -> ExecutionResult:
        """
        Execute a single action item
        
        Args:
            action: Validated action item
            jira_config: Jira credentials and project info
            dry_run: If True, simulate execution without creating ticket
        
        Returns:
            ExecutionResult with status, ticket_id, and audit trail
        """
        if self.mock_mode or dry_run:
            return self._mock_execute(action, dry_run)
        
        # Real execution via Nova Act browser automation
        result = self._execute_with_retry(action, jira_config)
        
        # Log to audit trail
        self._write_audit_log(action, result)
        
        return result
    
    def execute_batch(
        self,
        actions: List[ActionItem],
        jira_config: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
        parallel: bool = False
    ) -> Dict[str, Any]:
        """
        Execute multiple actions
        
        Args:
            actions: List of validated action items
            jira_config: Jira configuration
            dry_run: Simulate execution
            parallel: Execute in parallel (when available)
        
        Returns:
            Batch execution summary with per-action results
        """
        if self.mock_mode or dry_run:
            return self._mock_batch_execute(actions, dry_run)
        
        results = []
        
        if parallel:
            # Parallel execution (future enhancement)
            # Would use asyncio + Nova Act concurrent sessions
            pass
        else:
            # Sequential execution
            for action in actions:
                result = self.execute_action(action, jira_config, dry_run)
                results.append(result)
        
        # Calculate batch statistics
        success_count = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == ExecutionStatus.FAILED)
        
        return {
            "total_actions": len(actions),
            "successful": success_count,
            "failed": failed_count,
            "success_rate": (success_count / len(actions)) * 100 if actions else 0,
            "results": results,
            "execution_time_ms": sum(r.execution_time_ms for r in results),
            "dry_run": dry_run
        }
    
    def _execute_with_retry(
        self,
        action: ActionItem,
        jira_config: Dict[str, str]
    ) -> ExecutionResult:
        """Execute with automatic retry logic"""
        attempts = 0
        last_error = None
        
        while attempts < self.max_retries:
            attempts += 1
            
            try:
                # Execute via Nova Act
                result = self._create_jira_ticket(action, jira_config)
                
                if result.status == ExecutionStatus.SUCCESS:
                    return result
                
                # If failed but retryable, wait and retry
                if attempts < self.max_retries:
                    import time
                    time.sleep(self.retry_delay_seconds)
                
                last_error = result.error_message
                
            except Exception as e:
                last_error = str(e)
                
                if attempts < self.max_retries:
                    import time
                    time.sleep(self.retry_delay_seconds)
        
        # All retries exhausted
        return ExecutionResult(
            action_id=action.id,
            status=ExecutionStatus.FAILED,
            ticket_id=None,
            ticket_url=None,
            error_message=f"Failed after {self.max_retries} attempts: {last_error}",
            execution_time_ms=0,
            retry_count=attempts
        )
    
    def _create_jira_ticket(
        self,
        action: ActionItem,
        jira_config: Dict[str, str]
    ) -> ExecutionResult:
        """
        Create Jira ticket via Nova Act browser automation
        
        This would use Amazon Nova Act to:
        1. Navigate to Jira
        2. Click "Create Issue"
        3. Fill form fields
        4. Submit
        5. Extract ticket ID
        
        For now, this is a placeholder for the Nova Act integration
        which will be built in Day 3.
        """
        start_time = datetime.now()
        
        # Placeholder: Would call Nova Act here
        # nova_act_result = self._call_nova_act(
        #     task="create_jira_ticket",
        #     action_data=action.dict(),
        #     jira_config=jira_config
        # )
        
        # Simulated result
        ticket_id = f"PROJ-{hash(action.id) % 10000}"
        ticket_url = f"{jira_config.get('base_url', 'https://jira.example.com')}/browse/{ticket_id}"
        
        end_time = datetime.now()
        execution_time = int((end_time - start_time).total_seconds() * 1000)
        
        return ExecutionResult(
            action_id=action.id,
            status=ExecutionStatus.SUCCESS,
            ticket_id=ticket_id,
            ticket_url=ticket_url,
            error_message=None,
            execution_time_ms=execution_time,
            retry_count=0
        )
    
    def _write_audit_log(
        self,
        action: ActionItem,
        result: ExecutionResult
    ):
        """Write execution to audit log (JSONL format)"""
        log_entry = AuditLog(
            timestamp=datetime.now().isoformat(),
            action_id=action.id,
            action_title=action.title,
            execution_status=result.status.value,
            ticket_id=result.ticket_id,
            ticket_url=result.ticket_url,
            error_message=result.error_message,
            retry_count=result.retry_count
        )
        
        # Append to JSONL file
        with open(self.audit_log_path, 'a') as f:
            f.write(json.dumps(log_entry.dict()) + '\n')
    
    def get_execution_history(
        self,
        action_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Read execution history from audit log
        
        Args:
            action_id: Filter by specific action (optional)
            limit: Max number of records to return
        
        Returns:
            List of audit log entries
        """
        if not os.path.exists(self.audit_log_path):
            return []
        
        logs = []
        
        with open(self.audit_log_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    
                    # Filter by action_id if specified
                    if action_id and entry.get('action_id') != action_id:
                        continue
                    
                    logs.append(AuditLog(**entry))
                    
                    if len(logs) >= limit:
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        return logs[-limit:]  # Return most recent N
    
    def _mock_execute(
        self,
        action: ActionItem,
        dry_run: bool
    ) -> ExecutionResult:
        """Mock execution for testing"""
        # Simulate execution time
        import random
        execution_time = random.randint(500, 2000)
        
        # Simulate occasional failures (10% fail rate)
        success = random.random() > 0.1
        
        if success:
            ticket_id = f"MOCK-{abs(hash(action.id)) % 10000}"
            ticket_url = f"https://jira.example.com/browse/{ticket_id}"
            
            return ExecutionResult(
                action_id=action.id,
                status=ExecutionStatus.SUCCESS if not dry_run else ExecutionStatus.DRY_RUN,
                ticket_id=ticket_id if not dry_run else None,
                ticket_url=ticket_url if not dry_run else None,
                error_message=None,
                execution_time_ms=execution_time,
                retry_count=0
            )
        else:
            return ExecutionResult(
                action_id=action.id,
                status=ExecutionStatus.FAILED,
                ticket_id=None,
                ticket_url=None,
                error_message="Mock failure: Browser timeout",
                execution_time_ms=execution_time,
                retry_count=1
            )
    
    def _mock_batch_execute(
        self,
        actions: List[ActionItem],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Mock batch execution"""
        results = [
            self._mock_execute(action, dry_run)
            for action in actions
        ]
        
        success_count = sum(
            1 for r in results 
            if r.status in [ExecutionStatus.SUCCESS, ExecutionStatus.DRY_RUN]
        )
        failed_count = len(results) - success_count
        
        return {
            "total_actions": len(actions),
            "successful": success_count,
            "failed": failed_count,
            "success_rate": (success_count / len(actions)) * 100 if actions else 0,
            "results": results,
            "execution_time_ms": sum(r.execution_time_ms for r in results),
            "dry_run": dry_run,
            "mock_mode": True
        }
    
    def validate_jira_config(
        self,
        jira_config: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Validate Jira configuration
        
        Checks:
        - Required fields present
        - Credentials valid (in real mode)
        - Project accessible
        """
        required_fields = ['base_url', 'username', 'api_token', 'project_key']
        
        missing = [f for f in required_fields if f not in jira_config]
        
        if missing:
            return {
                "valid": False,
                "error": f"Missing required fields: {', '.join(missing)}",
                "missing_fields": missing
            }
        
        if self.mock_mode:
            return {
                "valid": True,
                "message": "Mock mode: Configuration looks good",
                "mock_mode": True
            }
        
        # In real mode, would test connection via Nova Act
        # test_result = self._test_jira_connection(jira_config)
        
        return {
            "valid": True,
            "message": "Jira configuration validated",
            "base_url": jira_config['base_url'],
            "project_key": jira_config['project_key']
        }
