#!/usr/bin/env python3
"""
Comprehensive test suite for DecisionPilot
Tests all components without requiring AWS credentials
"""

import sys
import os

# Add backend to path
sys.path.insert(0, './backend')

def test_imports():
    """Test that all modules can be imported"""
    print("=" * 60)
    print("1️⃣  Testing Imports...")
    print("=" * 60)
    
    try:
        import config
        print("✅ config")
        
        from services.embedding_service import NovaEmbeddingService
        print("✅ embedding_service")
        
        from agents.base_agent import BaseAgent
        print("✅ base_agent")
        
        from agents.planner_agent import PlannerAgent
        print("✅ planner_agent")
        
        from agents.extractor_agent import ExtractorAgent
        print("✅ extractor_agent")
        
        from schemas.meeting_schemas import MeetingAnalysis, ActionItem
        print("✅ meeting_schemas")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_embedding_service():
    """Test embedding service in mock mode"""
    print("\n" + "=" * 60)
    print("2️⃣  Testing Embedding Service (Mock Mode)...")
    print("=" * 60)
    
    try:
        from services.embedding_service import NovaEmbeddingService
        
        service = NovaEmbeddingService()
        
        chunk = service.embed_transcript_chunk(
            text="We need to deploy the authentication service by Friday.",
            timestamp=34.5,
            speaker="Sarah",
            meeting_id="test-001"
        )
        
        print(f"✅ Chunk ID: {chunk.chunk_id}")
        print(f"✅ Topic: {chunk.topic_cluster}")
        print(f"✅ Embedding dims: {len(chunk.embedding)}")
        print(f"✅ Content hash: {chunk.content_hash[:16]}...")
        
        if sum(chunk.embedding) == 0:
            print("⚠️  Using mock embeddings (all zeros)")
            print("   This is expected without AWS credentials")
        else:
            print("✅ Real embeddings detected!")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_planner_agent():
    """Test planner agent"""
    print("\n" + "=" * 60)
    print("3️⃣  Testing Planner Agent...")
    print("=" * 60)
    
    try:
        from agents.planner_agent import PlannerAgent
        
        agent = PlannerAgent()
        
        result = agent.execute({
            'meeting_summary': 'Team discussed API design and deployment',
            'user_goal': 'Extract and execute action items'
        })
        
        print(f"✅ Agent: {result.agent_name}")
        print(f"✅ Success: {result.success}")
        print(f"✅ Execution time: {result.execution_time_ms:.0f}ms")
        print(f"✅ Plan steps: {len(result.output.get('plan_steps', []))}")
        
        if result.output.get('plan_steps'):
            print("\n📋 Generated Plan:")
            for step in result.output['plan_steps']:
                print(f"   {step['step_id']}. {step['action']}: {step['query'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Planner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_extractor_agent():
    """Test extractor agent"""
    print("\n" + "=" * 60)
    print("4️⃣  Testing Extractor Agent...")
    print("=" * 60)
    
    try:
        from agents.extractor_agent import ExtractorAgent
        
        agent = ExtractorAgent()
        
        result = agent.execute({
            'evidence_chunks': [
                {
                    'citation_id': '[1]',
                    'content': 'Sarah: We need to deploy Auth0 by Friday',
                    'source': 'transcript',
                    'speaker': 'Sarah'
                },
                {
                    'citation_id': '[2]',
                    'content': 'Mike: I can handle the deployment',
                    'source': 'transcript',
                    'speaker': 'Mike'
                }
            ]
        })
        
        print(f"✅ Agent: {result.agent_name}")
        print(f"✅ Success: {result.success}")
        print(f"✅ Decisions: {len(result.output.get('decisions', []))}")
        print(f"✅ Actions: {len(result.output.get('action_items', []))}")
        print(f"✅ Risks: {len(result.output.get('risks', []))}")
        
        if result.output.get('action_items'):
            print("\n📝 Extracted Actions:")
            for action in result.output['action_items']:
                print(f"   • {action.get('description', 'N/A')}")
                print(f"     Owner: {action.get('owner', 'Unknown')}")
                print(f"     Citations: {', '.join(action.get('citations', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Extractor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schemas():
    """Test pydantic schemas"""
    print("\n" + "=" * 60)
    print("5️⃣  Testing Pydantic Schemas...")
    print("=" * 60)
    
    try:
        from schemas.meeting_schemas import ActionItem, Decision
        from datetime import date
        
        # Test ActionItem
        action = ActionItem(
            action_id="ACT-001",
            description="Deploy authentication service to production",
            owner="Mike",
            deadline=date(2026, 3, 5),
            priority="high",
            context="Required for security audit",
            citations=["[1]", "[2]"],
            clarity_score=0.85,
            evidence_score=0.75,
            execution_risk="medium",
            confidence=0.90
        )
        
        print("✅ ActionItem schema validated")
        print(f"   {action.action_id}: {action.description[:50]}...")
        
        # Test Decision
        decision = Decision(
            decision_id="DEC-001",
            description="Use Auth0 for OAuth implementation",
            decision_maker="Sarah",
            rationale="Provides enterprise features",
            citations=["[1]"],
            confidence=0.95
        )
        
        print("✅ Decision schema validated")
        print(f"   {decision.decision_id}: {decision.description[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    
    print("\n🔍 DecisionPilot Test Suite")
    print("Running in MOCK MODE (no AWS required)\n")
    
    results = {
        'imports': test_imports(),
        'embedding': test_embedding_service(),
        'planner': test_planner_agent(),
        'extractor': test_extractor_agent(),
        'schemas': test_schemas()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed!")
        print("\n💡 Next steps:")
        print("   1. Get AWS credentials (or keep using mock mode)")
        print("   2. Start backend: cd backend && source venv/bin/activate && python main.py")
        print("   3. Start frontend: cd frontend && npm install && npm run dev")
        print("   4. Open: http://localhost:3000")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
    
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
