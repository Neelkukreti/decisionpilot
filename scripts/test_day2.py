#!/usr/bin/env python3
"""
DecisionPilot Day 2 Test Suite

Tests:
- Critic Agent (quality validation)
- Execution Agent (task orchestration)
- Retrieval Service (semantic search)
- Memory Store (persistent storage)
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import numpy as np
from datetime import datetime, date

from agents.critic_agent import CriticAgent
from agents.execution_agent import ExecutionAgent
from services.retrieval_service import RetrievalService
from services.memory_store import MeetingMemoryStore
from schemas.meeting_schemas import (
    ActionItem,
    Decision,
    MeetingAnalysis,
    Risk,
    OpenQuestion,
    Evidence,
    ExecutionStatus
)


def test_critic_agent():
    """Test Critic Agent validation"""
    print("\n" + "="*60)
    print("🔍 Testing Critic Agent...")
    print("="*60)
    
    critic = CriticAgent(mock_mode=True)
    
    # Test action validation
    action = ActionItem(
        id="ACT-001",
        title="Deploy authentication service",
        description="Deploy the new Auth0 integration to production",
        owner="Mike",
        deadline=date(2026, 3, 10),
        priority="high",
        citations=["[1]", "[2]"],
        confidence=0.9
    )
    
    validation = critic.validate_action_item(action)
    
    print(f"✅ Action validated: {action.id}")
    print(f"   Quality Score: {validation.quality_score.overall:.1f}/100")
    print(f"   Clarity: {validation.quality_score.clarity:.1f}")
    print(f"   Evidence: {validation.quality_score.evidence_quality:.1f}")
    
    if validation.issues:
        print(f"   Issues: {len(validation.issues)}")
        for issue in validation.issues:
            print(f"      ⚠️  {issue}")
    
    if validation.suggestions:
        print(f"   Suggestions: {len(validation.suggestions)}")
        for suggestion in validation.suggestions[:2]:
            print(f"      💡 {suggestion}")
    
    # Test decision validation
    decision = Decision(
        id="DEC-001",
        title="Use Auth0 for OAuth",
        description="We decided to use Auth0 instead of building custom OAuth",
        owner="Sarah",
        rationale="Auth0 provides better security and reduces development time",
        citations=["[1]", "[3]"],
        confidence=0.95
    )
    
    decision_validation = critic.validate_decision(decision)
    
    print(f"\n✅ Decision validated: {decision.id}")
    print(f"   Quality Score: {decision_validation.quality_score.overall:.1f}/100")
    
    # Test meeting analysis scoring
    analysis = MeetingAnalysis(
        meeting_id="test-meeting-001",
        summary="Team discussed authentication implementation and decided on Auth0",
        decisions=[decision],
        action_items=[action],
        risks=[],
        open_questions=[],
        extraction_timestamp=datetime.now(),
        evidence_references=[]
    )
    
    scores = critic.score_meeting_analysis(analysis)
    
    print(f"\n📊 Meeting Health Score: {scores['health_score']:.1f}/100")
    print(f"   Action Quality: {scores['action_quality']:.1f}")
    print(f"   Decision Quality: {scores['decision_quality']:.1f}")
    print(f"   Execution Ready: {'✅ Yes' if scores['execution_ready'] else '❌ No'}")
    
    if scores['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in scores['recommendations']:
            print(f"   {rec}")
    
    return True


def test_execution_agent():
    """Test Execution Agent"""
    print("\n" + "="*60)
    print("🚀 Testing Execution Agent...")
    print("="*60)
    
    executor = ExecutionAgent(mock_mode=True)
    
    # Test single action execution
    action = ActionItem(
        id="ACT-002",
        title="Update API documentation",
        description="Add Auth0 integration docs to API reference",
        owner="Sarah",
        deadline=date(2026, 3, 15),
        priority="medium",
        citations=["[3]"],
        confidence=0.85
    )
    
    print("\n🔨 Executing action (dry run)...")
    result = executor.execute_action(action, dry_run=True)
    
    print(f"✅ Execution complete: {result.action_id}")
    print(f"   Status: {result.status.value}")
    print(f"   Ticket: {result.ticket_id or 'N/A (dry run)'}")
    print(f"   Execution Time: {result.execution_time_ms}ms")
    print(f"   Retries: {result.retry_count}")
    
    # Test batch execution
    actions = [
        ActionItem(
            id=f"ACT-{100+i}",
            title=f"Test Action {i+1}",
            description=f"This is test action number {i+1}",
            owner="Test User",
            priority="low",
            citations=["[1]"],
            confidence=0.8
        )
        for i in range(3)
    ]
    
    print("\n🔨 Executing batch (3 actions, mock mode)...")
    batch_result = executor.execute_batch(actions, dry_run=False)
    
    print(f"✅ Batch complete:")
    print(f"   Total: {batch_result['total_actions']}")
    print(f"   Successful: {batch_result['successful']}")
    print(f"   Failed: {batch_result['failed']}")
    print(f"   Success Rate: {batch_result['success_rate']:.1f}%")
    print(f"   Total Time: {batch_result['execution_time_ms']}ms")
    
    # Test Jira config validation
    jira_config = {
        "base_url": "https://jira.example.com",
        "username": "test@example.com",
        "api_token": "test_token_123",
        "project_key": "PROJ"
    }
    
    config_validation = executor.validate_jira_config(jira_config)
    
    print(f"\n🔧 Jira Config Validation:")
    print(f"   Valid: {'✅ Yes' if config_validation['valid'] else '❌ No'}")
    print(f"   Message: {config_validation.get('message', 'N/A')}")
    
    return True


def test_retrieval_service():
    """Test Retrieval Service"""
    print("\n" + "="*60)
    print("🔍 Testing Retrieval Service...")
    print("="*60)
    
    retrieval = RetrievalService(mock_mode=True)
    
    # Test indexing
    meeting_id = "test-meeting-002"
    
    chunks = [
        {
            "id": "chunk_001",
            "embedding": np.random.rand(1024).tolist(),
            "content": "The team discussed using Auth0 for authentication",
            "metadata": {
                "timestamp": 120.5,
                "speaker": "Sarah",
                "source_type": "transcript"
            }
        },
        {
            "id": "chunk_002",
            "embedding": np.random.rand(1024).tolist(),
            "content": "Mike raised concerns about the deployment timeline",
            "metadata": {
                "timestamp": 180.3,
                "speaker": "Mike",
                "source_type": "transcript"
            }
        },
        {
            "id": "chunk_003",
            "embedding": np.random.rand(1024).tolist(),
            "content": "Action item: Deploy to production by March 10th",
            "metadata": {
                "timestamp": 240.7,
                "speaker": "Sarah",
                "source_type": "transcript"
            }
        }
    ]
    
    print(f"\n📥 Indexing {len(chunks)} chunks...")
    index_result = retrieval.index_meeting_content(meeting_id, chunks)
    
    print(f"✅ Indexed successfully:")
    print(f"   Meeting: {index_result['meeting_id']}")
    print(f"   Chunks: {index_result['chunks_indexed']}")
    print(f"   Total in Store: {index_result.get('total_indexed', 'N/A')}")
    
    # Test retrieval
    query = "authentication implementation"
    query_embedding = np.random.rand(1024)
    
    print(f"\n🔎 Searching for: '{query}'...")
    results = retrieval.retrieve(
        query,
        query_embedding,
        meeting_id=meeting_id,
        top_k=3
    )
    
    print(f"✅ Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n   {i}. Score: {result['score']:.3f}")
        print(f"      {result['content'][:80]}...")
        if result.get('metadata'):
            print(f"      Speaker: {result['metadata'].get('speaker', 'Unknown')}")
            print(f"      Time: {result['metadata'].get('timestamp', 0):.1f}s")
    
    # Test hybrid search
    print(f"\n🔎 Hybrid search (semantic + keyword)...")
    hybrid_results = retrieval.hybrid_search(
        query,
        query_embedding,
        meeting_id=meeting_id,
        top_k=2
    )
    
    print(f"✅ Hybrid results: {len(hybrid_results)}")
    for result in hybrid_results:
        print(f"   Combined Score: {result.get('combined_score', 0):.3f}")
        print(f"   {result['content'][:60]}...")
    
    return True


def test_memory_store():
    """Test Meeting Memory Store"""
    print("\n" + "="*60)
    print("💾 Testing Memory Store...")
    print("="*60)
    
    store = MeetingMemoryStore(mock_mode=True)
    
    # Create test analysis
    meeting_id = "test-meeting-003"
    
    analysis = MeetingAnalysis(
        meeting_id=meeting_id,
        summary="Team meeting about authentication implementation with Auth0",
        decisions=[
            Decision(
                id="DEC-001",
                title="Use Auth0",
                description="Decided to use Auth0 for OAuth implementation",
                owner="Sarah",
                rationale="Better security, faster implementation",
                citations=["[1]", "[2]"],
                confidence=0.95
            )
        ],
        action_items=[
            ActionItem(
                id="ACT-001",
                title="Deploy Auth0",
                description="Deploy Auth0 integration to production",
                owner="Mike",
                deadline=date(2026, 3, 10),
                priority="high",
                citations=["[2]", "[3]"],
                confidence=0.9
            )
        ],
        risks=[
            Risk(
                risk_id="RISK-001",
                description="Deployment timeline may be tight",
                severity="medium",
                mitigation="Add buffer days to schedule",
                owner="Mike",
                citations=["[4]"],
                confidence=0.7
            )
        ],
        open_questions=[],
        extraction_timestamp=datetime.now(),
        evidence_references=[]
    )
    
    metadata = {
        "title": "Auth Implementation Planning",
        "date": datetime.now(),
        "participants": ["Sarah", "Mike", "John"]
    }
    
    print(f"\n💾 Storing meeting analysis...")
    store_result = store.store_meeting(meeting_id, analysis, metadata)
    
    print(f"✅ Meeting stored:")
    print(f"   ID: {store_result['meeting_id']}")
    print(f"   Decisions: {store_result['decisions_count']}")
    print(f"   Actions: {store_result['actions_count']}")
    print(f"   Risks: {store_result['risks_count']}")
    
    # Test retrieval
    print(f"\n📖 Retrieving meeting...")
    retrieved = store.get_meeting(meeting_id)
    
    if retrieved:
        print(f"✅ Meeting retrieved:")
        print(f"   Title: {retrieved['title']}")
        print(f"   Summary: {retrieved['summary'][:80]}...")
        print(f"   Decisions: {len(retrieved['decisions'])}")
        print(f"   Actions: {len(retrieved['action_items'])}")
    
    # Test execution storage
    from schemas.meeting_schemas import ExecutionResult
    
    exec_result = ExecutionResult(
        action_id="ACT-001",
        status=ExecutionStatus.SUCCESS,
        ticket_id="PROJ-123",
        ticket_url="https://jira.example.com/browse/PROJ-123",
        execution_time_ms=1250,
        retry_count=0
    )
    
    print(f"\n💾 Storing execution result...")
    exec_store = store.store_execution(meeting_id, "ACT-001", exec_result)
    
    print(f"✅ Execution stored:")
    print(f"   Ticket: {exec_store['ticket_id']}")
    
    # Test execution history
    print(f"\n📜 Retrieving execution history...")
    history = store.get_executions(meeting_id=meeting_id)
    
    print(f"✅ Found {len(history)} execution(s):")
    for exec in history:
        print(f"   {exec['action_id']} → {exec['ticket_id']} ({exec['status']})")
    
    return True


def main():
    """Run all Day 2 tests"""
    print("\n" + "="*60)
    print("🧪 DecisionPilot Day 2 Test Suite")
    print("="*60)
    
    tests = [
        ("Critic Agent", test_critic_agent),
        ("Execution Agent", test_execution_agent),
        ("Retrieval Service", test_retrieval_service),
        ("Memory Store", test_memory_store),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results[test_name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            print(f"\n❌ {test_name} failed with error:")
            print(f"   {type(e).__name__}: {e}")
            results[test_name] = "❌ FAIL"
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        print(f"{result} - {test_name}")
    
    passed = sum(1 for r in results.values() if "PASS" in r)
    total = len(results)
    
    print("\n" + "="*60)
    
    if passed == total:
        print("🎉 All Day 2 tests passed!")
        print("\n💡 Next steps:")
        print("   1. Day 2 multi-agent system complete")
        print("   2. Ready for Day 3: Nova Act browser automation")
        print("   3. Test with: python scripts/test_day2.py")
    else:
        print(f"⚠️  {total - passed}/{total} tests failed")
    
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
