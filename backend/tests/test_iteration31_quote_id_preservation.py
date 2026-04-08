"""
Iteration 31: Quote ID Preservation Tests
=========================================
CRITICAL BUG FIX VERIFICATION:
- Quote.model_dump() generates a NEW UUID for 'id' field every time
- On PUT (update), the $set operation was overwriting the original document ID
- All subsequent operations (GET, PDF, email) using the original ID would return 'Quote not found'
- FIX: quote_dict['id'] = existing.get('id', id) preserves the original ID

Tests:
1. Create quote with 15+ items → Edit → Verify ID is PRESERVED
2. After editing, GET /api/quotes-v2/{id} still works with original ID
3. After editing, POST /api/quotes-v2/{id}/generate-pdf still works with original ID
4. Create quote → Edit 3 times → Each time verify ID stays same → Then generate PDF
5. List quotes: GET /api/quotes-v2/ returns JSON array without errors
6. Convert to PO: POST /api/quotes-v2/{id}/convert-to-po preserves document
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@gimmicks.com",
        "password": "admin123456"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")

@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestQuoteIDPreservation:
    """CRITICAL: Tests that quote IDs are preserved after PUT updates"""
    
    def test_list_quotes_returns_json_array(self, api_client):
        """GET /api/quotes-v2/ returns JSON array without errors"""
        response = api_client.get(f"{BASE_URL}/api/quotes-v2/?doc_type=QUOTE")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/quotes-v2/ returned {len(data)} quotes")
    
    def test_create_quote_with_15_items_and_edit_preserves_id(self, authenticated_client):
        """CRITICAL: Create quote with 15+ items → Edit → Verify ID is PRESERVED"""
        # Create 15 items
        items = []
        for i in range(15):
            items.append({
                "item_id": f"TEST_ITEM_{i}",
                "product_id": f"PROD_{i}",
                "code": f"CODE_{i:03d}",
                "name": f"Test Product {i}",
                "description": f"Description for product {i}",
                "quantity": i + 1,
                "unit_price": 10.0 * (i + 1),
                "total_price": 10.0 * (i + 1) * (i + 1),
                "image_url": "",
                "categories": [],
                "selected_characteristics": [],
                "discount_amount": 0,
                "discount_type": "$",
                "additional_amount": 0,
                "additional_type": "$",
                "otros": ""
            })
        
        # Create quote
        quote_data = {
            "doc_type": "QUOTE",
            "client_id": "TEST_CLIENT_ID",
            "client_name": "TEST Client for ID Preservation",
            "client_contact": "Test Contact",
            "client_email": "test@test.com",
            "items": items,
            "subtotal": 1000.0,
            "tax": 150.0,
            "total": 1150.0,
            "status": "draft",
            "payment_terms": "50% anticipo",
            "validity": "8 días",
            "delivery_time": "Por confirmar"
        }
        
        # POST - Create quote
        create_response = authenticated_client.post(f"{BASE_URL}/api/quotes-v2/", json=quote_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        created_quote = create_response.json()
        original_id = created_quote.get("id")
        quote_number = created_quote.get("quote_number")
        
        assert original_id, "Quote should have an ID"
        print(f"✓ Created quote with ID: {original_id}, number: {quote_number}, items: {len(items)}")
        
        # GET - Verify quote exists
        get_response = authenticated_client.get(f"{BASE_URL}/api/quotes-v2/{original_id}")
        assert get_response.status_code == 200, f"GET failed: {get_response.text}"
        fetched_quote = get_response.json()
        assert fetched_quote.get("id") == original_id, "Fetched ID should match original"
        print(f"✓ GET /api/quotes-v2/{original_id} returned quote successfully")
        
        # PUT - Edit the quote (add one more item)
        items.append({
            "item_id": "TEST_ITEM_15",
            "product_id": "PROD_15",
            "code": "CODE_015",
            "name": "Test Product 15 (Added)",
            "description": "Added during edit",
            "quantity": 5,
            "unit_price": 100.0,
            "total_price": 500.0,
            "image_url": "",
            "categories": [],
            "selected_characteristics": [],
            "discount_amount": 0,
            "discount_type": "$",
            "additional_amount": 0,
            "additional_type": "$",
            "otros": ""
        })
        
        quote_data["items"] = items
        quote_data["subtotal"] = 1500.0
        quote_data["tax"] = 225.0
        quote_data["total"] = 1725.0
        quote_data["client_name"] = "TEST Client EDITED"
        
        put_response = authenticated_client.put(f"{BASE_URL}/api/quotes-v2/{original_id}", json=quote_data)
        assert put_response.status_code == 200, f"PUT failed: {put_response.text}"
        updated_quote = put_response.json()
        updated_id = updated_quote.get("id")
        
        # CRITICAL ASSERTION: ID must be preserved
        assert updated_id == original_id, f"CRITICAL BUG: ID changed from {original_id} to {updated_id}"
        print(f"✓ PUT preserved ID: {updated_id} == {original_id}")
        
        # GET again - Verify quote still accessible with original ID
        get_after_edit = authenticated_client.get(f"{BASE_URL}/api/quotes-v2/{original_id}")
        assert get_after_edit.status_code == 200, f"GET after edit failed: {get_after_edit.text}"
        fetched_after_edit = get_after_edit.json()
        assert fetched_after_edit.get("id") == original_id, "ID should still match after edit"
        assert fetched_after_edit.get("client_name") == "TEST Client EDITED", "Edit should be persisted"
        assert len(fetched_after_edit.get("items", [])) == 16, "Should have 16 items now"
        print(f"✓ GET after edit returned quote with preserved ID and updated data")
        
        # Store for cleanup
        self.__class__.test_quote_id = original_id
    
    def test_generate_pdf_after_edit_works_with_original_id(self, authenticated_client):
        """CRITICAL: After editing, POST /api/quotes-v2/{id}/generate-pdf still works"""
        quote_id = getattr(self.__class__, 'test_quote_id', None)
        if not quote_id:
            pytest.skip("No test quote created")
        
        pdf_response = authenticated_client.post(
            f"{BASE_URL}/api/quotes-v2/{quote_id}/generate-pdf",
            json={"doc_type": "PROFORMA"}
        )
        assert pdf_response.status_code == 200, f"PDF generation failed: {pdf_response.text}"
        pdf_data = pdf_response.json()
        assert "pdf_base64" in pdf_data, "Response should contain pdf_base64"
        assert "filename" in pdf_data, "Response should contain filename"
        print(f"✓ PDF generated successfully for quote {quote_id}: {pdf_data.get('filename')}")
    
    def test_edit_quote_3_times_id_stays_same(self, authenticated_client):
        """Create quote → Edit 3 times → Each time verify ID stays same → Then generate PDF"""
        # Create a new quote with 15 items
        items = []
        for i in range(15):
            items.append({
                "item_id": f"MULTI_EDIT_ITEM_{i}",
                "product_id": f"PROD_ME_{i}",
                "code": f"ME_{i:03d}",
                "name": f"Multi-Edit Product {i}",
                "description": f"Description {i}",
                "quantity": 1,
                "unit_price": 50.0,
                "total_price": 50.0,
                "image_url": "",
                "categories": [],
                "selected_characteristics": [],
                "discount_amount": 0,
                "discount_type": "$",
                "additional_amount": 0,
                "additional_type": "$",
                "otros": ""
            })
        
        quote_data = {
            "doc_type": "QUOTE",
            "client_id": "TEST_MULTI_EDIT_CLIENT",
            "client_name": "Multi-Edit Test Client",
            "client_contact": "Contact",
            "client_email": "multi@test.com",
            "items": items,
            "subtotal": 750.0,
            "tax": 112.5,
            "total": 862.5,
            "status": "draft",
            "payment_terms": "50% anticipo",
            "validity": "8 días",
            "delivery_time": "Por confirmar"
        }
        
        # Create
        create_response = authenticated_client.post(f"{BASE_URL}/api/quotes-v2/", json=quote_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        original_id = create_response.json().get("id")
        print(f"✓ Created quote with ID: {original_id}")
        
        # Edit 3 times
        for edit_num in range(1, 4):
            quote_data["client_name"] = f"Multi-Edit Test Client - Edit #{edit_num}"
            quote_data["subtotal"] = 750.0 + (edit_num * 100)
            
            put_response = authenticated_client.put(f"{BASE_URL}/api/quotes-v2/{original_id}", json=quote_data)
            assert put_response.status_code == 200, f"Edit #{edit_num} failed: {put_response.text}"
            updated_id = put_response.json().get("id")
            
            # CRITICAL: ID must stay the same
            assert updated_id == original_id, f"Edit #{edit_num}: ID changed from {original_id} to {updated_id}"
            print(f"✓ Edit #{edit_num}: ID preserved ({updated_id})")
            
            # Verify with GET
            get_response = authenticated_client.get(f"{BASE_URL}/api/quotes-v2/{original_id}")
            assert get_response.status_code == 200, f"GET after edit #{edit_num} failed"
            assert get_response.json().get("id") == original_id
        
        # Generate PDF after 3 edits
        pdf_response = authenticated_client.post(
            f"{BASE_URL}/api/quotes-v2/{original_id}/generate-pdf",
            json={"doc_type": "PROFORMA"}
        )
        assert pdf_response.status_code == 200, f"PDF after 3 edits failed: {pdf_response.text}"
        print(f"✓ PDF generated successfully after 3 edits")
        
        # Store for cleanup
        self.__class__.multi_edit_quote_id = original_id
    
    def test_convert_to_po_preserves_document(self, authenticated_client):
        """Convert to PO: POST /api/quotes-v2/{id}/convert-to-po preserves document"""
        quote_id = getattr(self.__class__, 'multi_edit_quote_id', None)
        if not quote_id:
            pytest.skip("No multi-edit quote created")
        
        # Convert to PO
        convert_response = authenticated_client.post(f"{BASE_URL}/api/quotes-v2/{quote_id}/convert-to-po")
        assert convert_response.status_code == 200, f"Convert to PO failed: {convert_response.text}"
        convert_data = convert_response.json()
        po_id = convert_data.get("po_id")
        assert po_id, "Should return new PO ID"
        print(f"✓ Converted quote {quote_id} to PO {po_id}")
        
        # Verify original quote still exists
        original_response = authenticated_client.get(f"{BASE_URL}/api/quotes-v2/{quote_id}")
        assert original_response.status_code == 200, "Original quote should still exist"
        print(f"✓ Original quote {quote_id} still accessible")
        
        # Verify PO exists
        po_response = authenticated_client.get(f"{BASE_URL}/api/quotes-v2/{po_id}")
        assert po_response.status_code == 200, f"PO not found: {po_response.text}"
        po_data = po_response.json()
        assert po_data.get("doc_type") == "PO", "Should be a PO"
        print(f"✓ PO {po_id} created with doc_type=PO")
        
        # Store for cleanup
        self.__class__.po_id = po_id


class TestQuoteWith20Items:
    """Test with 20 items to ensure large quotes work correctly"""
    
    def test_create_and_edit_quote_with_20_items(self, authenticated_client):
        """Create quote with 20 items, edit it, verify ID preserved"""
        items = []
        for i in range(20):
            items.append({
                "item_id": f"LARGE_ITEM_{i}",
                "product_id": f"PROD_L_{i}",
                "code": f"L{i:03d}",
                "name": f"Large Quote Product {i}",
                "description": f"Product {i} for large quote test",
                "quantity": 2,
                "unit_price": 25.0,
                "total_price": 50.0,
                "image_url": "",
                "categories": [],
                "selected_characteristics": [],
                "discount_amount": 0,
                "discount_type": "$",
                "additional_amount": 0,
                "additional_type": "$",
                "otros": ""
            })
        
        quote_data = {
            "doc_type": "QUOTE",
            "client_id": "TEST_LARGE_QUOTE_CLIENT",
            "client_name": "Large Quote Test Client",
            "client_contact": "Contact",
            "client_email": "large@test.com",
            "items": items,
            "subtotal": 1000.0,
            "tax": 150.0,
            "total": 1150.0,
            "status": "draft",
            "payment_terms": "50% anticipo",
            "validity": "8 días",
            "delivery_time": "Por confirmar"
        }
        
        # Create
        create_response = authenticated_client.post(f"{BASE_URL}/api/quotes-v2/", json=quote_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        original_id = create_response.json().get("id")
        print(f"✓ Created 20-item quote with ID: {original_id}")
        
        # Edit
        quote_data["client_name"] = "Large Quote Test Client - EDITED"
        put_response = authenticated_client.put(f"{BASE_URL}/api/quotes-v2/{original_id}", json=quote_data)
        assert put_response.status_code == 200, f"Edit failed: {put_response.text}"
        updated_id = put_response.json().get("id")
        
        assert updated_id == original_id, f"ID changed from {original_id} to {updated_id}"
        print(f"✓ 20-item quote edit preserved ID: {updated_id}")
        
        # Generate PDF
        pdf_response = authenticated_client.post(
            f"{BASE_URL}/api/quotes-v2/{original_id}/generate-pdf",
            json={"doc_type": "PROFORMA"}
        )
        assert pdf_response.status_code == 200, f"PDF failed: {pdf_response.text}"
        print(f"✓ PDF generated for 20-item quote")
        
        self.__class__.large_quote_id = original_id


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_quotes(self, authenticated_client):
        """Delete test quotes created during testing"""
        test_ids = []
        
        # Collect IDs from other test classes
        for cls in [TestQuoteIDPreservation, TestQuoteWith20Items]:
            for attr in ['test_quote_id', 'multi_edit_quote_id', 'po_id', 'large_quote_id']:
                quote_id = getattr(cls, attr, None)
                if quote_id:
                    test_ids.append(quote_id)
        
        deleted = 0
        for quote_id in test_ids:
            try:
                response = authenticated_client.delete(f"{BASE_URL}/api/quotes-v2/{quote_id}?permanent=true")
                if response.status_code in [200, 404]:
                    deleted += 1
            except Exception:
                pass
        
        print(f"✓ Cleanup: Deleted {deleted} test quotes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
