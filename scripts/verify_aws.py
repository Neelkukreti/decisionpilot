#!/usr/bin/env python3
"""
Verify AWS Bedrock access and Nova model availability
Run: python scripts/verify_aws.py
"""

import boto3
import json
import os
import sys

# Add backend to path
sys.path.insert(0, './backend')

def verify_aws_credentials():
    """Check if AWS credentials are configured"""
    print("=" * 60)
    print("1️⃣  Checking AWS Credentials...")
    print("=" * 60)
    
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"✅ AWS Account: {identity['Account']}")
        print(f"✅ User ARN: {identity['Arn']}")
        print(f"✅ Region: {os.getenv('AWS_REGION', 'us-east-1')}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to verify credentials: {e}")
        print("\n💡 Fix:")
        print("   1. Edit .env file")
        print("   2. Add your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        print("   3. Run this script again")
        return False

def verify_bedrock_access():
    """Check if Bedrock is accessible"""
    print("\n" + "=" * 60)
    print("2️⃣  Checking Bedrock Access...")
    print("=" * 60)
    
    try:
        bedrock = boto3.client('bedrock', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        # List foundation models
        response = bedrock.list_foundation_models()
        
        print(f"✅ Bedrock accessible")
        print(f"✅ Found {len(response['modelSummaries'])} models")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to access Bedrock: {e}")
        print("\n💡 Fix:")
        print("   1. Go to: https://console.aws.amazon.com/bedrock/")
        print("   2. Ensure Bedrock is enabled in your region")
        print("   3. Check IAM permissions")
        return False

def verify_nova_models():
    """Check if Nova models are available"""
    print("\n" + "=" * 60)
    print("3️⃣  Checking Nova Model Access...")
    print("=" * 60)
    
    try:
        bedrock = boto3.client('bedrock', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        response = bedrock.list_foundation_models()
        
        nova_models = [
            'amazon.nova-lite-v1',
            'amazon.nova-act-v1',
            'amazon.nova-embed-multimodal-v1'
        ]
        
        available_models = {m['modelId'] for m in response['modelSummaries']}
        
        for model_id in nova_models:
            if model_id in available_models:
                print(f"✅ {model_id} - Available")
            else:
                print(f"⚠️  {model_id} - Not found (may need access request)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to check models: {e}")
        return False

def test_nova_embedding():
    """Test actual embedding call"""
    print("\n" + "=" * 60)
    print("4️⃣  Testing Nova Embedding (Live Call)...")
    print("=" * 60)
    
    try:
        bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Try to embed a simple test string
        response = bedrock_runtime.invoke_model(
            modelId='amazon.nova-embed-multimodal-v1',
            body=json.dumps({
                "inputText": "This is a test embedding.",
                "embeddingConfig": {
                    "outputEmbeddingLength": 1024
                }
            })
        )
        
        result = json.loads(response['body'].read())
        embedding = result.get('embedding', [])
        
        if len(embedding) == 1024:
            print(f"✅ Nova Embedding working!")
            print(f"✅ Embedding dimension: {len(embedding)}")
            print(f"✅ Sample values: {embedding[:5]}")
            return True
        else:
            print(f"⚠️  Unexpected embedding size: {len(embedding)}")
            return False
            
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        
        if "AccessDeniedException" in str(e):
            print("\n💡 Fix:")
            print("   1. Go to: https://console.aws.amazon.com/bedrock/")
            print("   2. Click 'Model access' in sidebar")
            print("   3. Click 'Manage model access'")
            print("   4. Enable: Amazon Nova models")
            print("   5. Click 'Save changes' and wait for approval")
        
        return False

def main():
    """Run all verification checks"""
    
    # Load .env
    from dotenv import load_dotenv
    load_dotenv()
    
    print("\n🔍 AWS Bedrock Verification Tool")
    print("=" * 60)
    
    results = {
        'credentials': verify_aws_credentials(),
        'bedrock': False,
        'models': False,
        'embedding': False
    }
    
    if results['credentials']:
        results['bedrock'] = verify_bedrock_access()
        
    if results['bedrock']:
        results['models'] = verify_nova_models()
        results['embedding'] = test_nova_embedding()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check.capitalize()}")
    
    if all(results.values()):
        print("\n🎉 All checks passed! You're ready to build!")
        print("\n💡 Next step:")
        print("   python scripts/test_embedding.py")
    else:
        print("\n⚠️  Some checks failed. Fix the issues above and rerun.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
