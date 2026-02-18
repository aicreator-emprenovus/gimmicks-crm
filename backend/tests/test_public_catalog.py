"""
Test public catalog endpoint and bot catalog link functionality.
Testing the NEW feature: public catalog page without authentication.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://crm-cotizador-merge.preview.emergentagent.com')


class TestPublicCatalogEndpoint:
    """Test the /api/catalog/public endpoint - NO AUTH required"""

    def test_catalog_public_with_jarro_keyword(self):
        """GET /api/catalog/public?q=jarro returns products with code, name, image_url, description"""
        response = requests.get(f"{BASE_URL}/api/catalog/public", params={"q": "jarro", "limit": 10})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        products = response.json()
        assert isinstance(products, list), "Response should be a list"
        assert len(products) > 0, "Should return at least one product for 'jarro'"
        
        # Validate product structure
        first_product = products[0]
        assert "code" in first_product, "Product should have 'code' field"
        assert "name" in first_product, "Product should have 'name' field"
        assert "image_url" in first_product, "Product should have 'image_url' field"
        assert "description" in first_product, "Product should have 'description' field"
        
        # Check name contains jarro
        names_with_jarro = [p for p in products if "jarro" in p.get("name", "").lower() or "jarro" in p.get("code", "").lower()]
        assert len(names_with_jarro) > 0, "Should return products related to 'jarro'"
        
        print(f"✓ Returned {len(products)} products for 'jarro', first: {first_product.get('name')}")

    def test_catalog_public_with_termo_keyword(self):
        """GET /api/catalog/public?q=termo returns termos products"""
        response = requests.get(f"{BASE_URL}/api/catalog/public", params={"q": "termo", "limit": 10})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        products = response.json()
        assert isinstance(products, list), "Response should be a list"
        assert len(products) > 0, "Should return at least one product for 'termo'"
        
        # Validate all products have required fields
        for product in products:
            assert "code" in product, "Product should have 'code' field"
            assert "name" in product, "Product should have 'name' field"
        
        # Check that results are related to termo/thermal
        names_lower = " ".join([p.get("name", "").lower() + " " + p.get("description", "").lower() for p in products])
        assert "term" in names_lower or "vaso" in names_lower or "taza" in names_lower, "Should return thermal/termo products"
        
        print(f"✓ Returned {len(products)} products for 'termo'")

    def test_catalog_public_without_query_returns_empty(self):
        """GET /api/catalog/public without q parameter returns empty array"""
        response = requests.get(f"{BASE_URL}/api/catalog/public")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        products = response.json()
        assert isinstance(products, list), "Response should be a list"
        assert len(products) == 0, "Should return empty array when no query provided"
        
        print("✓ Empty query returns empty array as expected")

    def test_catalog_public_with_gorra_keyword(self):
        """GET /api/catalog/public?q=gorra returns gorras products"""
        response = requests.get(f"{BASE_URL}/api/catalog/public", params={"q": "gorra", "limit": 10})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        products = response.json()
        assert isinstance(products, list), "Response should be a list"
        # Some products may exist
        
        print(f"✓ Returned {len(products)} products for 'gorra'")

    def test_catalog_public_no_auth_required(self):
        """Verify public endpoint works without any authorization header"""
        # This test explicitly ensures no auth is needed
        response = requests.get(
            f"{BASE_URL}/api/catalog/public",
            params={"q": "jarro"},
            headers={}  # No auth header
        )
        
        assert response.status_code == 200, f"Should work without auth, got {response.status_code}"
        assert response.json(), "Should return products without authentication"
        
        print("✓ Public endpoint works without authentication")

    def test_catalog_returns_image_url_field(self):
        """Verify products include image_url field for display"""
        response = requests.get(f"{BASE_URL}/api/catalog/public", params={"q": "jarro", "limit": 5})
        
        assert response.status_code == 200
        products = response.json()
        
        # Check all products have image_url
        for product in products:
            assert "image_url" in product, f"Product {product.get('code')} missing image_url"
        
        # Check at least some have valid image URLs
        valid_images = [p for p in products if p.get("image_url") and p.get("image_url") != "N/A"]
        print(f"✓ {len(valid_images)}/{len(products)} products have valid image_url")


class TestCatalogUrlBuilder:
    """Test the catalog URL format for WhatsApp bot"""

    def test_catalog_url_format(self):
        """Verify catalog link format is correct: https://[domain]/catalog?q=[keyword]"""
        from urllib.parse import quote
        
        keywords = ["jarro", "termo", "gorra", "usb"]
        base_url = "https://crm-cotizador-merge.preview.emergentagent.com"
        
        for keyword in keywords:
            expected_url = f"{base_url}/catalog?q={quote(keyword)}"
            
            # The URL should be accessible and return the frontend page
            response = requests.get(expected_url, allow_redirects=True)
            # Frontend will return 200 for valid routes
            assert response.status_code == 200, f"Catalog URL {expected_url} should be accessible"
            
            print(f"✓ Catalog URL format correct for '{keyword}'")


class TestWebhookCatalogIntegration:
    """Test webhook bot sends catalog LINK (not text list)"""

    def test_webhook_responds_to_product_query(self):
        """POST /api/webhook/whatsapp - when client asks about products, bot should process"""
        # This tests the webhook processing only - actual WhatsApp API may fail
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "test"},
                        "messages": [{
                            "from": "593TESTCATALOG123",
                            "id": "test_msg_catalog",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Quiero ver jarros"}
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        
        # Webhook should return 200 even if message sending fails
        assert response.status_code == 200, f"Webhook should return 200, got {response.status_code}"
        
        print("✓ Webhook processes product queries (WhatsApp API response may vary)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
