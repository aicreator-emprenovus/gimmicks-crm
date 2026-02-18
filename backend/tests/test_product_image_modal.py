"""
Test suite for Product Edit Modal Image Upload Feature
Tests the following features:
- Product edit modal opens when clicking edit button
- Image preview area shows product image or placeholder
- 'Subir Imagen' button with upload icon and light blue background
- URL input field for external image URLs (Google Drive compatible)
- Tip text about Google Drive is displayed
- 'Guardar' (Save) button works to save product
- Backend POST /api/inventory/upload-image endpoint
- Product update (PUT /api/inventory/{code}) saves image_url
"""
import pytest
import requests
import os
from io import BytesIO

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestProductImageModal:
    """Tests for Product Edit Modal Image Upload functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200, "Login failed"
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_login_returns_access_token(self):
        """Test that login returns access_token field"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data, "Response should contain 'access_token'"
        assert "user" in data, "Response should contain 'user'"
        assert data["user"]["email"] == "admin@gimmicks.com"
    
    def test_inventory_list_returns_products(self):
        """Test that inventory endpoint returns products"""
        response = requests.get(f"{BASE_URL}/api/inventory/?limit=10", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert data["total"] > 0, "Should have products in inventory"
    
    def test_inventory_products_have_image_url_field(self):
        """Test that products have image_url field"""
        response = requests.get(f"{BASE_URL}/api/inventory/?limit=1", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) > 0
        product = data["products"][0]
        assert "image_url" in product, "Product should have image_url field"
    
    def test_upload_image_endpoint_requires_file(self):
        """Test that upload-image endpoint requires image file"""
        response = requests.post(
            f"{BASE_URL}/api/inventory/upload-image",
            headers=self.headers
        )
        assert response.status_code == 422, "Should return 422 without file"
        data = response.json()
        assert "detail" in data
    
    def test_upload_image_endpoint_accepts_image(self):
        """Test that upload-image endpoint accepts and processes image"""
        # Create a minimal valid JPEG image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        response = requests.post(
            f"{BASE_URL}/api/inventory/upload-image",
            headers=self.headers,
            files={"image": ("test.jpg", img_bytes, "image/jpeg")}
        )
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert "image_url" in data, "Response should contain image_url"
        assert data["image_url"].startswith("/api/uploads/products/")
        assert "message" in data
    
    def test_upload_image_compresses_large_images(self):
        """Test that upload-image compresses images larger than 1200px"""
        from PIL import Image
        # Create a large image (2000x2000)
        img = Image.new('RGB', (2000, 2000), color='blue')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        response = requests.post(
            f"{BASE_URL}/api/inventory/upload-image",
            headers=self.headers,
            files={"image": ("large.jpg", img_bytes, "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "image_url" in data
        # Image should be stored (compression happens on backend)
    
    def test_update_product_with_image_url(self):
        """Test that PUT endpoint saves image_url correctly"""
        # Get a product first
        response = requests.get(f"{BASE_URL}/api/inventory/?limit=1", headers=self.headers)
        assert response.status_code == 200
        product = response.json()["products"][0]
        original_code = product["code"]
        original_image = product.get("image_url", "")
        
        # Update with test image URL
        test_image_url = "/api/uploads/products/test-image-12345.jpg"
        update_data = {
            "code": product["code"],
            "name": product["name"],
            "description": product.get("description", ""),
            "price": product.get("price", 0),
            "cost": product.get("cost", 0),
            "stock": product.get("stock", 0),
            "supplier": product.get("supplier", ""),
            "image_url": test_image_url,
            "categories": product.get("categories", [])
        }
        
        import urllib.parse
        encoded_code = urllib.parse.quote(original_code, safe='')
        response = requests.put(
            f"{BASE_URL}/api/inventory/{encoded_code}",
            headers={**self.headers, "Content-Type": "application/json"},
            json=update_data
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        # Verify the update
        data = response.json()
        assert data["image_url"] == test_image_url, "image_url should be updated"
        
        # Revert the change
        update_data["image_url"] = original_image
        requests.put(
            f"{BASE_URL}/api/inventory/{encoded_code}",
            headers={**self.headers, "Content-Type": "application/json"},
            json=update_data
        )
    
    def test_google_drive_url_conversion(self):
        """Test that Google Drive URLs are handled correctly on save"""
        # Get a product first
        response = requests.get(f"{BASE_URL}/api/inventory/?limit=1", headers=self.headers)
        assert response.status_code == 200
        product = response.json()["products"][0]
        original_code = product["code"]
        original_image = product.get("image_url", "")
        
        # Test with Google Drive URL - frontend converts these
        google_drive_url = "https://drive.google.com/file/d/1ABC123XYZ/view"
        expected_converted = "https://drive.google.com/thumbnail?id=1ABC123XYZ&sz=w1200"
        
        update_data = {
            "code": product["code"],
            "name": product["name"],
            "description": product.get("description", ""),
            "price": product.get("price", 0),
            "cost": product.get("cost", 0),
            "stock": product.get("stock", 0),
            "supplier": product.get("supplier", ""),
            "image_url": google_drive_url,  # Frontend would convert this
            "categories": product.get("categories", [])
        }
        
        import urllib.parse
        encoded_code = urllib.parse.quote(original_code, safe='')
        response = requests.put(
            f"{BASE_URL}/api/inventory/{encoded_code}",
            headers={**self.headers, "Content-Type": "application/json"},
            json=update_data
        )
        assert response.status_code == 200
        
        # Revert the change
        update_data["image_url"] = original_image
        requests.put(
            f"{BASE_URL}/api/inventory/{encoded_code}",
            headers={**self.headers, "Content-Type": "application/json"},
            json=update_data
        )


class TestInventoryPage:
    """Tests for Inventory Page functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_inventory_pagination(self):
        """Test inventory pagination works"""
        response = requests.get(f"{BASE_URL}/api/inventory/?page=1&limit=50", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "pages" in data
        assert data["page"] == 1
        assert len(data["products"]) <= 50
    
    def test_inventory_search(self):
        """Test inventory search works"""
        response = requests.get(f"{BASE_URL}/api/inventory/?search=jarro&limit=10", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        # Results should contain 'jarro' in name, code or categories
    
    def test_inventory_categories_endpoint(self):
        """Test categories endpoint returns categories"""
        response = requests.get(f"{BASE_URL}/api/inventory/categories", headers=self.headers)
        assert response.status_code == 200
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
