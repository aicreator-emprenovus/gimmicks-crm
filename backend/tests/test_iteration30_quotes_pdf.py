"""
Iteration 30: Quotes-v2 and PDF Generation Tests
Focus: _id exclusion, PDF generation, shared MongoDB connection
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestQuotesV2Endpoints:
    """Test quotes-v2 endpoints - _id exclusion and data loading"""
    
    def test_quotes_v2_list_returns_json_without_id(self):
        """GET /api/quotes-v2/ should return JSON array without _id field"""
        response = requests.get(f"{BASE_URL}/api/quotes-v2/", params={"doc_type": "QUOTE"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify no _id field in any quote
        for quote in data[:5]:  # Check first 5
            assert "_id" not in quote, f"Quote {quote.get('id')} contains _id field"
            assert "id" in quote
            assert "doc_type" in quote
    
    def test_quotes_v2_list_po_returns_json_without_id(self):
        """GET /api/quotes-v2/?doc_type=PO should return PO quotes without _id"""
        response = requests.get(f"{BASE_URL}/api/quotes-v2/", params={"doc_type": "PO"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify no _id field and correct doc_type
        for quote in data[:5]:
            assert "_id" not in quote
            assert quote.get("doc_type") == "PO"
    
    def test_quotes_v2_single_quote_no_id(self):
        """GET /api/quotes-v2/{id} should return quote without _id"""
        # First get a quote ID
        list_response = requests.get(f"{BASE_URL}/api/quotes-v2/", params={"doc_type": "QUOTE"})
        quotes = list_response.json()
        if quotes:
            quote_id = quotes[0]["id"]
            response = requests.get(f"{BASE_URL}/api/quotes-v2/{quote_id}")
            assert response.status_code == 200
            data = response.json()
            assert "_id" not in data
            assert data["id"] == quote_id


class TestPDFGeneration:
    """Test PDF generation endpoints with try/except handling"""
    
    def test_generate_pdf_proforma(self):
        """POST /api/quotes-v2/{id}/generate-pdf should return pdf_base64 for PROFORMA"""
        # Get a quote with items
        list_response = requests.get(f"{BASE_URL}/api/quotes-v2/", params={"doc_type": "QUOTE"})
        quotes = list_response.json()
        quote_with_items = next((q for q in quotes if q.get("items")), quotes[0] if quotes else None)
        
        if quote_with_items:
            response = requests.post(
                f"{BASE_URL}/api/quotes-v2/{quote_with_items['id']}/generate-pdf",
                json={},
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "pdf_base64" in data
            assert "filename" in data
            assert data["filename"].startswith("PROFORMA_")
            assert len(data["pdf_base64"]) > 100  # Valid PDF content
    
    def test_generate_pdf_orden_compra(self):
        """POST /api/quotes-v2/{id}/generate-pdf with doc_type=ORDEN_COMPRA should return PO PDF"""
        # Get a PO quote
        list_response = requests.get(f"{BASE_URL}/api/quotes-v2/", params={"doc_type": "PO"})
        quotes = list_response.json()
        
        if quotes:
            response = requests.post(
                f"{BASE_URL}/api/quotes-v2/{quotes[0]['id']}/generate-pdf",
                json={"doc_type": "ORDEN_COMPRA"},
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "pdf_base64" in data
            assert "filename" in data
            assert data["filename"].startswith("ORDEN_COMPRA_")
    
    def test_generate_pdf_with_overrides(self):
        """POST /api/quotes-v2/{id}/generate-pdf with overrides should work"""
        list_response = requests.get(f"{BASE_URL}/api/quotes-v2/", params={"doc_type": "PO"})
        quotes = list_response.json()
        
        if quotes:
            response = requests.post(
                f"{BASE_URL}/api/quotes-v2/{quotes[0]['id']}/generate-pdf",
                json={
                    "doc_type": "ORDEN_COMPRA",
                    "factura": "TEST-FAC-001",
                    "overrides": {
                        "name": "Test Client Override",
                        "address": "Test Address"
                    }
                },
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "pdf_base64" in data
    
    def test_generate_pdf_nonexistent_quote(self):
        """POST /api/quotes-v2/{invalid_id}/generate-pdf should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/quotes-v2/nonexistent-id-12345/generate-pdf",
            json={},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 404


class TestSPACatchAll:
    """Test SPA catch-all protection"""
    
    def test_api_nonexistent_returns_json_404(self):
        """GET /api/nonexistent should return JSON 404, not HTML"""
        response = requests.get(f"{BASE_URL}/api/nonexistent")
        assert response.status_code == 404
        # Should be JSON, not HTML
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type or response.text.startswith("{")
        data = response.json()
        assert "detail" in data


class TestCRUDSectionsLoad:
    """Test that all CRUD sections load data"""
    
    def test_health_endpoint(self):
        """GET /api/health should return healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
    
    def test_inventory_loads(self):
        """GET /api/inventory/ should return products"""
        response = requests.get(f"{BASE_URL}/api/inventory/", params={"limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert "products" in data or isinstance(data, list)
    
    def test_clients_loads(self):
        """GET /api/clients/ should return clients"""
        response = requests.get(f"{BASE_URL}/api/clients/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_leads_loads(self):
        """GET /api/leads should return leads"""
        response = requests.get(f"{BASE_URL}/api/leads")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_conversations_loads(self):
        """GET /api/conversations should return conversations"""
        response = requests.get(f"{BASE_URL}/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestOldQuotesEndpoint:
    """Test old /api/quotes endpoint (bot quotes)"""
    
    def test_old_quotes_requires_auth(self):
        """GET /api/quotes should require authentication"""
        response = requests.get(f"{BASE_URL}/api/quotes")
        # Should require auth
        assert response.status_code in [401, 403] or "Token" in response.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
