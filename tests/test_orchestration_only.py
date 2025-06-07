#!/usr/bin/env python3
"""
Test just the orchestration team AGNO-native changes.
Isolated test to avoid import chain issues.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

from i2c.bootstrap import initialize_environment
initialize_environment()


def test_orchestration_team_bloat():
    """Test orchestration team instruction bloat directly"""
    
    print("🧪 Testing orchestration team AGNO-native approach")
    print("=" * 60)
    
    try:
        # Import only what we need
        from i2c.workflow.orchestration_team import build_orchestration_team
        
        # Mock knowledge base that would cause bloat in old system
        class MockKnowledgeBase:
            def retrieve_knowledge(self, query, limit=5):
                # Simulate large content that would cause bloat
                large_content = """
                def authentication_example():
                    # This is a comprehensive example of user authentication
                    # with password hashing, session management, and security
                    import bcrypt
                    import jwt
                    from datetime import datetime, timedelta
                    
                    def hash_password(password):
                        salt = bcrypt.gensalt()
                        return bcrypt.hashpw(password.encode('utf-8'), salt)
                    
                    def verify_password(password, hashed):
                        return bcrypt.checkpw(password.encode('utf-8'), hashed)
                    
                    def create_jwt_token(user_id):
                        payload = {
                            'user_id': user_id,
                            'exp': datetime.utcnow() + timedelta(hours=24)
                        }
                        return jwt.encode(payload, 'secret_key', algorithm='HS256')
                    
                    # More authentication code would go here...
                """ * 5  # Multiply to make it really large
                
                return [
                    {"source": "auth_best_practices.md", "content": large_content},
                    {"source": "security_patterns.md", "content": large_content},
                    {"source": "web_security.md", "content": large_content}
                ] * limit  # This would create massive bloat in old system
        
        # Test session state with knowledge base
        session_state = {
            "objective": {
                "task": "Create a secure user authentication system",
                "architectural_context": {
                    "system_type": "fullstack_web_app",
                    "architecture_pattern": "clean_architecture"
                }
            },
            "knowledge_base": MockKnowledgeBase(),
            "project_path": "/tmp/test"
        }
        
        print("🏗️  Building orchestration team with knowledge base...")
        print(f"📊 Knowledge base will return {len(MockKnowledgeBase().retrieve_knowledge('test', 5))} chunks")
        
        # Build team - this should use AGNO-native approach after our changes
        team = build_orchestration_team(session_state=session_state)
        
        # Analyze the results
        instructions_text = "\n".join(team.instructions)
        instruction_size = len(instructions_text)
        
        print(f"✅ Team created successfully")
        print(f"📏 Total instruction size: {instruction_size:,} characters")
        print(f"🔧 Team has knowledge access: {team.knowledge is not None}")
        print(f"🔧 Agentic context enabled: {team.enable_agentic_context}")
        
        # Check for bloat indicators from old system
        has_content_chunks = "[Knowledge " in instructions_text
        has_large_content = any(len(line) > 1000 for line in team.instructions)
        
        # Check for our AGNO-native approach
        has_agno_guidance = "knowledge base through the Team" in instructions_text
        has_knowledge_access_section = "=== KNOWLEDGE ACCESS ===" in instructions_text
        
        print(f"\n🔍 BLOAT ANALYSIS:")
        print(f"   Embedded content chunks: {has_content_chunks} {'❌ (old bloat pattern)' if has_content_chunks else '✅'}")
        print(f"   Large content lines: {has_large_content} {'❌ (bloat detected)' if has_large_content else '✅'}")
        print(f"   AGNO-native guidance: {has_agno_guidance} {'✅' if has_agno_guidance else '❌'}")
        print(f"   Knowledge access section: {has_knowledge_access_section} {'✅' if has_knowledge_access_section else '❌'}")
        
        # Size comparison
        if instruction_size < 5000:
            size_status = "✅ Reasonable"
        elif instruction_size < 15000:
            size_status = "⚠️  Large"
        else:
            size_status = "❌ Bloated"
        
        print(f"   Instruction size: {size_status}")
        
        # Show sample of instructions
        print(f"\n📋 INSTRUCTION SAMPLE:")
        print("=" * 40)
        sample_text = instructions_text[:800] + "..." if len(instructions_text) > 800 else instructions_text
        print(sample_text)
        print("=" * 40)
        
        # Evaluate success
        success_indicators = [
            not has_content_chunks,     # No embedded content
            not has_large_content,      # No bloated lines  
            has_agno_guidance,          # Has AGNO guidance
            instruction_size < 10000,   # Reasonable size
            team.knowledge is not None, # Knowledge access available
            team.enable_agentic_context # Agentic context enabled
        ]
        
        success = all(success_indicators)
        
        print(f"\n🏁 RESULT:")
        if success:
            print("🎉 SUCCESS: AGNO-native approach working perfectly!")
            print("   ✅ No content bloat from knowledge chunks")
            print("   ✅ Uses Team knowledge parameter instead")
            print("   ✅ Reasonable instruction size") 
            print("   ✅ Agentic context enabled")
            print("   ✅ Knowledge base accessible")
        else:
            print("⚠️  PARTIAL SUCCESS: Some issues remain")
            for i, (desc, result) in enumerate([
                ("No content chunks", not has_content_chunks),
                ("No large content", not has_large_content), 
                ("AGNO guidance", has_agno_guidance),
                ("Reasonable size", instruction_size < 10000),
                ("Knowledge access", team.knowledge is not None),
                ("Agentic context", team.enable_agentic_context)
            ]):
                status = "✅" if result else "❌"
                print(f"   {status} {desc}")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 AGNO-Native Orchestration Team Test")
    print("Testing the core architectural change from content consumption to dynamic access")
    print("=" * 80)
    
    success = test_orchestration_team_bloat()
    
    print("\n" + "=" * 80)
    print("🏁 FINAL ASSESSMENT:")
    
    if success:
        print("🎉 AGNO-NATIVE APPROACH WORKING!")
        print("✅ Successfully eliminated content consumption bloat")
        print("✅ Teams now use dynamic knowledge access")
        print("✅ Should significantly improve performance")
        print("✅ Should reduce agent confusion from prompt bloat")
    else:
        print("⚠️  NEEDS REFINEMENT:")
        print("Some aspects of the AGNO-native approach are working,")
        print("but additional optimization may be needed.")
    
    print("=" * 80)