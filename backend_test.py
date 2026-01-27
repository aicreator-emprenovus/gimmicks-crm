import requests
import sys
import json
from datetime import datetime
import time

class CRMAPITester:
    def __init__(self, base_url="https://whatscrm-13.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_resources = {
            'leads': [],
            'products': [],
            'conversations': [],
            'automation_rules': []
        }

    def log_result(self, test_name, success, details="", error=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name} - PASSED")
        else:
            print(f"❌ {test_name} - FAILED: {error}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "error": error
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json() if response.content else {}
                    self.log_result(name, True, f"Status: {response.status_code}")
                    return True, response_data
                except:
                    self.log_result(name, True, f"Status: {response.status_code}")
                    return True, {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_detail = response.json().get('detail', '')
                    if error_detail:
                        error_msg += f" - {error_detail}"
                except:
                    pass
                self.log_result(name, False, error=error_msg)
                return False, {}

        except requests.exceptions.Timeout:
            self.log_result(name, False, error="Request timeout (30s)")
            return False, {}
        except Exception as e:
            self.log_result(name, False, error=str(e))
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_register_user(self):
        """Test user registration"""
        user_data = {
            "email": "test@gimmicks.com",
            "password": "test123456",
            "name": "Usuario Test"
        }
        success, response = self.run_test("User Registration", "POST", "auth/register", 200, user_data)
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Token obtained: {self.token[:20]}...")
        return success

    def test_login_user(self):
        """Test user login"""
        login_data = {
            "email": "test@gimmicks.com",
            "password": "test123456"
        }
        success, response = self.run_test("User Login", "POST", "auth/login", 200, login_data)
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Token updated: {self.token[:20]}...")
        return success

    def test_get_current_user(self):
        """Test get current user info"""
        return self.run_test("Get Current User", "GET", "auth/me", 200)

    def test_dashboard_metrics(self):
        """Test dashboard metrics"""
        return self.run_test("Dashboard Metrics", "GET", "dashboard/metrics", 200)

    def test_seed_demo_data(self):
        """Test seeding demo data"""
        return self.run_test("Seed Demo Data", "POST", "seed-demo-data", 200, {})

    def test_create_lead(self):
        """Test creating a lead"""
        lead_data = {
            "phone_number": "+593999888777",
            "name": "Test Lead",
            "source": "whatsapp",
            "notes": "Test lead for API testing"
        }
        success, response = self.run_test("Create Lead", "POST", "leads", 200, lead_data)
        if success and 'id' in response:
            self.created_resources['leads'].append(response['id'])
        return success

    def test_get_leads(self):
        """Test getting leads list"""
        return self.run_test("Get Leads", "GET", "leads", 200)

    def test_filter_leads_by_stage(self):
        """Test filtering leads by stage"""
        return self.run_test("Filter Leads by Stage", "GET", "leads?stage=lead", 200)

    def test_filter_leads_by_classification(self):
        """Test filtering leads by classification"""
        return self.run_test("Filter Leads by Classification", "GET", "leads?classification=frio", 200)

    def test_update_lead(self):
        """Test updating a lead"""
        if not self.created_resources['leads']:
            self.log_result("Update Lead", False, error="No leads created to update")
            return False
        
        lead_id = self.created_resources['leads'][0]
        update_data = {
            "name": "Updated Test Lead",
            "funnel_stage": "pedido",
            "classification": "tibio",
            "notes": "Updated notes"
        }
        return self.run_test("Update Lead", "PATCH", f"leads/{lead_id}", 200, update_data)

    def test_get_single_lead(self):
        """Test getting a single lead"""
        if not self.created_resources['leads']:
            self.log_result("Get Single Lead", False, error="No leads created to get")
            return False
        
        lead_id = self.created_resources['leads'][0]
        return self.run_test("Get Single Lead", "GET", f"leads/{lead_id}", 200)

    def test_get_conversations(self):
        """Test getting conversations"""
        return self.run_test("Get Conversations", "GET", "conversations", 200)

    def test_get_conversation_messages(self):
        """Test getting conversation messages"""
        # First get conversations to find one
        success, conversations = self.run_test("Get Conversations for Messages", "GET", "conversations", 200)
        if success and conversations and len(conversations) > 0:
            conv_id = conversations[0]['id']
            return self.run_test("Get Conversation Messages", "GET", f"conversations/{conv_id}/messages", 200)
        else:
            self.log_result("Get Conversation Messages", False, error="No conversations available")
            return False

    def test_send_message(self):
        """Test sending a message"""
        # First get conversations to find one
        success, conversations = self.run_test("Get Conversations for Send", "GET", "conversations", 200)
        if success and conversations and len(conversations) > 0:
            conv_id = conversations[0]['id']
            message_data = {
                "conversation_id": conv_id,
                "content": "Test message from API",
                "message_type": "text"
            }
            return self.run_test("Send Message", "POST", f"conversations/{conv_id}/messages", 200, message_data)
        else:
            self.log_result("Send Message", False, error="No conversations available")
            return False

    def test_create_product(self):
        """Test creating a product"""
        product_data = {
            "code": "TEST-001",
            "name": "Test Product",
            "description": "Test product for API testing",
            "category_1": "Test Category",
            "price": 19.99,
            "stock": 100
        }
        success, response = self.run_test("Create Product", "POST", "products", 200, product_data)
        if success and 'id' in response:
            self.created_resources['products'].append(response['id'])
        return success

    def test_get_products(self):
        """Test getting products"""
        return self.run_test("Get Products", "GET", "products", 200)

    def test_search_products(self):
        """Test searching products"""
        return self.run_test("Search Products", "GET", "products?search=test", 200)

    def test_create_automation_rule(self):
        """Test creating automation rule"""
        rule_data = {
            "name": "Test Welcome Rule",
            "trigger_type": "new_lead",
            "action_type": "send_message",
            "action_value": "Welcome to Gimmicks! How can we help you?",
            "is_active": True
        }
        success, response = self.run_test("Create Automation Rule", "POST", "automation-rules", 200, rule_data)
        if success and 'id' in response:
            self.created_resources['automation_rules'].append(response['id'])
        return success

    def test_get_automation_rules(self):
        """Test getting automation rules"""
        return self.run_test("Get Automation Rules", "GET", "automation-rules", 200)

    def test_update_automation_rule(self):
        """Test updating automation rule"""
        if not self.created_resources['automation_rules']:
            self.log_result("Update Automation Rule", False, error="No rules created to update")
            return False
        
        rule_id = self.created_resources['automation_rules'][0]
        return self.run_test("Update Automation Rule", "PATCH", f"automation-rules/{rule_id}?is_active=false", 200)

    def test_ai_analyze_message(self):
        """Test AI message analysis"""
        params = "?message=Hola, necesito cotización para tazas personalizadas&conversation_id=test"
        success, response = self.run_test("AI Analyze Message", "POST", f"ai/analyze-message{params}", 200)
        
        # Give AI some time to process
        if success:
            time.sleep(2)
        
        return success

    def test_ai_recommend_products(self):
        """Test AI product recommendations"""
        recommend_data = {
            "query": "necesito tazas personalizadas para evento corporativo",
            "limit": 5
        }
        success, response = self.run_test("AI Product Recommendations", "POST", "ai/recommend-products", 200, recommend_data)
        
        # Give AI some time to process
        if success:
            time.sleep(2)
            
        return success

    def cleanup_resources(self):
        """Clean up created test resources"""
        print("\n🧹 Cleaning up test resources...")
        
        # Delete created leads
        for lead_id in self.created_resources['leads']:
            self.run_test(f"Cleanup Lead {lead_id}", "DELETE", f"leads/{lead_id}", 200)
        
        # Delete created products
        for product_id in self.created_resources['products']:
            self.run_test(f"Cleanup Product {product_id}", "DELETE", f"products/{product_id}", 200)
        
        # Delete created automation rules
        for rule_id in self.created_resources['automation_rules']:
            self.run_test(f"Cleanup Rule {rule_id}", "DELETE", f"automation-rules/{rule_id}", 200)

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting CRM API Tests")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)

        # Health check first
        self.test_health_check()

        # Authentication tests
        print("\n📋 AUTHENTICATION TESTS")
        self.test_register_user()
        self.test_login_user()
        self.test_get_current_user()

        # Dashboard tests
        print("\n📊 DASHBOARD TESTS")
        self.test_dashboard_metrics()
        self.test_seed_demo_data()

        # Lead management tests
        print("\n👥 LEAD MANAGEMENT TESTS")
        self.test_create_lead()
        self.test_get_leads()
        self.test_filter_leads_by_stage()
        self.test_filter_leads_by_classification()
        self.test_update_lead()
        self.test_get_single_lead()

        # Conversation tests
        print("\n💬 CONVERSATION TESTS")
        self.test_get_conversations()
        self.test_get_conversation_messages()
        self.test_send_message()

        # Product/Inventory tests
        print("\n📦 PRODUCT/INVENTORY TESTS")
        self.test_create_product()
        self.test_get_products()
        self.test_search_products()

        # Automation tests
        print("\n⚡ AUTOMATION TESTS")
        self.test_create_automation_rule()
        self.test_get_automation_rules()
        self.test_update_automation_rule()

        # AI tests
        print("\n🤖 AI INTEGRATION TESTS")
        self.test_ai_analyze_message()
        self.test_ai_recommend_products()

        # Cleanup
        self.cleanup_resources()

        # Print final results
        print("\n" + "=" * 60)
        print(f"📊 FINAL RESULTS")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            print("\nFailed tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['error']}")
            return 1

def main():
    tester = CRMAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())