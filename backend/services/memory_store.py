"""
Meeting Memory Store - Persistent Storage

Stores:
- Meeting metadata (title, date, participants)
- Extraction results (decisions, actions, risks)
- Execution history (Jira tickets created)
- Audit logs (all operations)

Mock mode: Uses in-memory dict for testing without PostgreSQL
Real mode: PostgreSQL with full ACID guarantees
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

from schemas.meeting_schemas import (
    MeetingAnalysis,
    ExecutionResult,
    ActionItem,
    Decision
)
from config import get_config


class MeetingMemoryStore:
    """Persistent storage for meeting data"""
    
    def __init__(self, mock_mode: bool = None):
        config = get_config()
        
        self.mock_mode = mock_mode if mock_mode is not None else config.MOCK_MODE
        
        if self.mock_mode:
            # In-memory storage
            self.meetings = {}
            self.executions = {}
            self.audit_log = []
        else:
            # Real PostgreSQL connection
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            self.conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                cursor_factory=RealDictCursor
            )
            
            self._init_schema()
    
    def store_meeting(
        self,
        meeting_id: str,
        analysis: MeetingAnalysis,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store meeting analysis results
        
        Args:
            meeting_id: Unique meeting identifier
            analysis: Complete meeting analysis
            metadata: Additional metadata (title, date, participants)
        
        Returns:
            Storage confirmation
        """
        if self.mock_mode:
            return self._mock_store_meeting(meeting_id, analysis, metadata)
        
        # Real PostgreSQL storage
        with self.conn.cursor() as cur:
            # Insert meeting record
            cur.execute("""
                INSERT INTO meetings (
                    meeting_id, title, meeting_date, summary, 
                    extraction_timestamp, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (meeting_id) DO UPDATE
                SET summary = EXCLUDED.summary,
                    extraction_timestamp = EXCLUDED.extraction_timestamp
            """, (
                meeting_id,
                metadata.get('title', 'Untitled Meeting'),
                metadata.get('date', datetime.now()),
                analysis.summary,
                analysis.extraction_timestamp,
                json.dumps(metadata or {})
            ))
            
            # Insert decisions
            for decision in analysis.decisions:
                cur.execute("""
                    INSERT INTO decisions (
                        meeting_id, decision_id, description,
                        decision_maker, rationale, citations, confidence
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    meeting_id,
                    decision.id,
                    decision.description,
                    decision.owner,
                    decision.rationale,
                    json.dumps(decision.citations),
                    decision.confidence
                ))
            
            # Insert action items
            for action in analysis.action_items:
                cur.execute("""
                    INSERT INTO action_items (
                        meeting_id, action_id, description, owner,
                        deadline, priority, citations, clarity_score,
                        evidence_score, execution_risk
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    meeting_id,
                    action.id,
                    action.description,
                    action.owner,
                    action.deadline,
                    action.priority,
                    json.dumps(action.citations),
                    action.clarity_score,
                    action.evidence_score,
                    action.execution_risk
                ))
            
            # Insert risks
            for risk in analysis.risks:
                cur.execute("""
                    INSERT INTO risks (
                        meeting_id, risk_id, description,
                        severity, mitigation, owner, citations
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    meeting_id,
                    risk.risk_id,
                    risk.description,
                    risk.severity,
                    risk.mitigation,
                    risk.owner,
                    json.dumps(risk.citations)
                ))
            
            self.conn.commit()
        
        return {
            "meeting_id": meeting_id,
            "stored_at": datetime.now().isoformat(),
            "decisions_count": len(analysis.decisions),
            "actions_count": len(analysis.action_items),
            "risks_count": len(analysis.risks)
        }
    
    def store_execution(
        self,
        meeting_id: str,
        action_id: str,
        result: ExecutionResult
    ) -> Dict[str, Any]:
        """
        Store execution result
        
        Links Jira ticket to action item
        """
        if self.mock_mode:
            return self._mock_store_execution(meeting_id, action_id, result)
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO executions (
                    meeting_id, action_id, ticket_id, ticket_url,
                    status, execution_time_ms, retry_count, error_message,
                    executed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                meeting_id,
                action_id,
                result.ticket_id,
                result.ticket_url,
                result.status.value,
                result.execution_time_ms,
                result.retry_count,
                result.error_message,
                datetime.now()
            ))
            
            self.conn.commit()
        
        return {
            "meeting_id": meeting_id,
            "action_id": action_id,
            "ticket_id": result.ticket_id,
            "stored_at": datetime.now().isoformat()
        }
    
    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve meeting analysis by ID"""
        if self.mock_mode:
            return self.meetings.get(meeting_id)
        
        with self.conn.cursor() as cur:
            # Get meeting
            cur.execute("""
                SELECT * FROM meetings WHERE meeting_id = %s
            """, (meeting_id,))
            
            meeting = cur.fetchone()
            
            if not meeting:
                return None
            
            # Get related data
            cur.execute("SELECT * FROM decisions WHERE meeting_id = %s", (meeting_id,))
            decisions = cur.fetchall()
            
            cur.execute("SELECT * FROM action_items WHERE meeting_id = %s", (meeting_id,))
            actions = cur.fetchall()
            
            cur.execute("SELECT * FROM risks WHERE meeting_id = %s", (meeting_id,))
            risks = cur.fetchall()
            
            return {
                **meeting,
                "decisions": decisions,
                "action_items": actions,
                "risks": risks
            }
    
    def get_executions(
        self,
        meeting_id: Optional[str] = None,
        action_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get execution history"""
        if self.mock_mode:
            results = list(self.executions.values())
            
            if meeting_id:
                results = [r for r in results if r['meeting_id'] == meeting_id]
            
            if action_id:
                results = [r for r in results if r['action_id'] == action_id]
            
            return results
        
        with self.conn.cursor() as cur:
            query = "SELECT * FROM executions WHERE 1=1"
            params = []
            
            if meeting_id:
                query += " AND meeting_id = %s"
                params.append(meeting_id)
            
            if action_id:
                query += " AND action_id = %s"
                params.append(action_id)
            
            query += " ORDER BY executed_at DESC"
            
            cur.execute(query, params)
            return cur.fetchall()
    
    def search_meetings(
        self,
        query: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search meetings by text or date range"""
        if self.mock_mode:
            results = list(self.meetings.values())
            
            if query:
                query_lower = query.lower()
                results = [
                    m for m in results
                    if query_lower in m.get('summary', '').lower()
                    or query_lower in m.get('title', '').lower()
                ]
            
            return results[:limit]
        
        with self.conn.cursor() as cur:
            sql = "SELECT * FROM meetings WHERE 1=1"
            params = []
            
            if query:
                sql += " AND (summary ILIKE %s OR title ILIKE %s)"
                params.extend([f"%{query}%", f"%{query}%"])
            
            if start_date:
                sql += " AND meeting_date >= %s"
                params.append(start_date)
            
            if end_date:
                sql += " AND meeting_date <= %s"
                params.append(end_date)
            
            sql += " ORDER BY meeting_date DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(sql, params)
            return cur.fetchall()
    
    def _init_schema(self):
        """Initialize PostgreSQL schema"""
        with self.conn.cursor() as cur:
            # Meetings table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    meeting_id VARCHAR(255) PRIMARY KEY,
                    title TEXT,
                    meeting_date TIMESTAMP,
                    summary TEXT,
                    extraction_timestamp TIMESTAMP,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Decisions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id SERIAL PRIMARY KEY,
                    meeting_id VARCHAR(255) REFERENCES meetings(meeting_id),
                    decision_id VARCHAR(255),
                    description TEXT,
                    decision_maker VARCHAR(255),
                    rationale TEXT,
                    citations JSONB,
                    confidence FLOAT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Action items table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS action_items (
                    id SERIAL PRIMARY KEY,
                    meeting_id VARCHAR(255) REFERENCES meetings(meeting_id),
                    action_id VARCHAR(255),
                    description TEXT,
                    owner VARCHAR(255),
                    deadline DATE,
                    priority VARCHAR(50),
                    citations JSONB,
                    clarity_score FLOAT,
                    evidence_score FLOAT,
                    execution_risk VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Risks table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS risks (
                    id SERIAL PRIMARY KEY,
                    meeting_id VARCHAR(255) REFERENCES meetings(meeting_id),
                    risk_id VARCHAR(255),
                    description TEXT,
                    severity VARCHAR(50),
                    mitigation TEXT,
                    owner VARCHAR(255),
                    citations JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Executions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id SERIAL PRIMARY KEY,
                    meeting_id VARCHAR(255) REFERENCES meetings(meeting_id),
                    action_id VARCHAR(255),
                    ticket_id VARCHAR(255),
                    ticket_url TEXT,
                    status VARCHAR(50),
                    execution_time_ms INTEGER,
                    retry_count INTEGER,
                    error_message TEXT,
                    executed_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            self.conn.commit()
    
    # Mock mode implementations
    
    def _mock_store_meeting(
        self,
        meeting_id: str,
        analysis: MeetingAnalysis,
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Store meeting in memory"""
        self.meetings[meeting_id] = {
            "meeting_id": meeting_id,
            "title": metadata.get('title', 'Untitled Meeting') if metadata else 'Untitled',
            "meeting_date": metadata.get('date', datetime.now()).isoformat() if metadata else datetime.now().isoformat(),
            "summary": analysis.summary,
            "decisions": [d.dict() for d in analysis.decisions],
            "action_items": [a.dict() for a in analysis.action_items],
            "risks": [r.dict() for r in analysis.risks],
            "extraction_timestamp": analysis.extraction_timestamp.isoformat(),
            "metadata": metadata or {},
            "stored_at": datetime.now().isoformat()
        }
        
        return {
            "meeting_id": meeting_id,
            "stored_at": datetime.now().isoformat(),
            "decisions_count": len(analysis.decisions),
            "actions_count": len(analysis.action_items),
            "risks_count": len(analysis.risks),
            "mock_mode": True
        }
    
    def _mock_store_execution(
        self,
        meeting_id: str,
        action_id: str,
        result: ExecutionResult
    ) -> Dict[str, Any]:
        """Store execution in memory"""
        exec_id = f"{meeting_id}_{action_id}_{len(self.executions)}"
        
        self.executions[exec_id] = {
            "id": exec_id,
            "meeting_id": meeting_id,
            "action_id": action_id,
            "ticket_id": result.ticket_id,
            "ticket_url": result.ticket_url,
            "status": result.status.value,
            "execution_time_ms": result.execution_time_ms,
            "retry_count": result.retry_count,
            "error_message": result.error_message,
            "executed_at": datetime.now().isoformat()
        }
        
        return {
            "meeting_id": meeting_id,
            "action_id": action_id,
            "ticket_id": result.ticket_id,
            "stored_at": datetime.now().isoformat(),
            "mock_mode": True
        }
    
    def __del__(self):
        """Close database connection"""
        if not self.mock_mode and hasattr(self, 'conn'):
            self.conn.close()
