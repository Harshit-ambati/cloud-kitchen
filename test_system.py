#!/usr/bin/env python3
"""
Test script to verify Cloud Kitchen system is working correctly
"""
import subprocess
import time
import sys
import requests
import json

def check_backend():
    """Check if backend is running"""
    print("\n📡 Checking Backend Server...")
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            print("✅ Backend is running!")
            return True
    except requests.ConnectionError:
        print("❌ Backend is not running. Start it with: python -m uvicorn app.main:app --reload")
        return False

def check_mongodb():
    """Check MongoDB connection"""
    print("\n🗄️  Checking MongoDB...")
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
        client.server_info()
        print("✅ MongoDB is connected!")
        return True
    except Exception as e:
        print(f"❌ MongoDB error: {e}")
        print("   Make sure MongoDB is running: mongod")
        return False

def test_api():
    """Test API endpoints"""
    print("\n🧪 Testing API Endpoints...")
    
    base_url = "http://localhost:8000/api"
    
    # Test Orders API
    print("\n  Testing Orders API...")
    try:
        order_data = {
            "user_lat": 28.6292,
            "user_lng": 77.2197,
            "kitchen_lat": 28.6139,
            "kitchen_lng": 77.209,
            "order_type": "regular"
        }
        
        response = requests.post(f"{base_url}/orders/create", json=order_data)
        if response.status_code == 200:
            print("    ✅ Order creation works!")
            order_id = response.json().get("id")
            
            # Test get orders
            response = requests.get(f"{base_url}/orders/")
            if response.status_code == 200:
                print(f"    ✅ Retrieved {response.json().get('count', 0)} orders")
        else:
            print(f"    ❌ Order creation failed: {response.text}")
    except Exception as e:
        print(f"    ❌ Orders API error: {e}")
    
    # Test Agents API
    print("\n  Testing Agents API...")
    try:
        agent_data = {
            "name": "Test Agent",
            "lat": 28.6139,
            "lng": 77.209
        }
        
        response = requests.post(f"{base_url}/agents/create", json=agent_data)
        if response.status_code == 200:
            print("    ✅ Agent creation works!")
            
            # Test get agents
            response = requests.get(f"{base_url}/agents/")
            if response.status_code == 200:
                print(f"    ✅ Retrieved {len(response.json().get('agents', []))} agents")
        else:
            print(f"    ❌ Agent creation failed: {response.text}")
    except Exception as e:
        print(f"    ❌ Agents API error: {e}")

def check_ml_model():
    """Check if ML model is trained"""
    print("\n🤖 Checking ML Model...")
    import os
    
    if os.path.exists("ml/model.pkl"):
        print("✅ ML model exists!")
        
        try:
            from ml.predict_eta import predict_eta
            eta = predict_eta(5.0)
            print(f"✅ ML prediction works! (ETA for 5km: {eta} min)")
            return True
        except Exception as e:
            print(f"❌ ML prediction error: {e}")
            return False
    else:
        print("❌ ML model not found. Train it with: python setup_ml.py")
        return False

def main():
    print("=" * 50)
    print("🚀 Cloud Kitchen System Verification")
    print("=" * 50)
    
    checks = {
        "MongoDB": check_mongodb(),
        "ML Model": check_ml_model(),
        "Backend": check_backend(),
    }
    
    if checks.get("Backend"):
        test_api()
    
    print("\n" + "=" * 50)
    print("📊 Verification Summary")
    print("=" * 50)
    
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
    
    all_passed = all(checks.values())
    
    if all_passed:
        print("\n✨ All systems ready!")
        print("\n🎉 Your Cloud Kitchen is ready to use!")
        print("   Open http://localhost:5173 in your browser")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
