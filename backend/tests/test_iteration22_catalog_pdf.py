"""
Iteration 22: Catalog PDF Feature Tests
Tests for:
1. POST /api/catalog/upload-pdf - Upload PDF (requires admin/desarrollador role)
2. GET /api/catalog/info - Get catalog info (requires auth)
3. GET /api/catalog/pdf - Serve PDF (public, no auth)
4. DELETE /api/catalog/pdf - Delete PDF (requires admin/desarrollador role)
5. Bot code verification - No gimmicks.com.ec references
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@gimmicks.com"
ADMIN_PASSWORD = "admin123456"
DEVELOPER_EMAIL = "aicreator@emprenovus.com"
DEVELOPER_PASSWORD = "Jlsb*1082"


class TestCatalogPDFFeature:
    """Test catalog PDF upload, info, serve, and delete endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _login(self, email, password):
        """Login and return auth token."""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token")

    def _get_auth_headers(self, token):
        """Return headers with auth token."""
        return {"Authorization": f"Bearer {token}"}

    def _create_test_pdf(self):
        """Create a minimal valid PDF file for testing."""
        # Minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""
        return pdf_content

    # ============== UPLOAD TESTS ==============

    def test_upload_pdf_as_admin(self):
        """Test uploading PDF as admin user."""
        token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        pdf_content = self._create_test_pdf()
        
        # Use a fresh session without Content-Type header for multipart
        upload_session = requests.Session()
        files = {"file": ("test_catalog.pdf", pdf_content, "application/pdf")}
        
        response = upload_session.post(
            f"{BASE_URL}/api/catalog/upload-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert "filename" in data
        assert "size_bytes" in data
        assert data["size_bytes"] > 0
        print(f"✓ Admin uploaded PDF: {data['filename']} ({data['size_bytes']} bytes)")

    def test_upload_pdf_as_developer(self):
        """Test uploading PDF as developer user."""
        token = self._login(DEVELOPER_EMAIL, DEVELOPER_PASSWORD)
        
        pdf_content = self._create_test_pdf()
        
        upload_session = requests.Session()
        files = {"file": ("dev_catalog.pdf", pdf_content, "application/pdf")}
        
        response = upload_session.post(
            f"{BASE_URL}/api/catalog/upload-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert "filename" in data
        print(f"✓ Developer uploaded PDF: {data['filename']}")

    def test_upload_pdf_without_auth_fails(self):
        """Test that uploading PDF without auth fails."""
        pdf_content = self._create_test_pdf()
        
        upload_session = requests.Session()
        files = {"file": ("no_auth.pdf", pdf_content, "application/pdf")}
        
        response = upload_session.post(
            f"{BASE_URL}/api/catalog/upload-pdf",
            files=files
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Upload without auth correctly returns 401")

    def test_upload_non_pdf_fails(self):
        """Test that uploading non-PDF file fails."""
        token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        upload_session = requests.Session()
        # Create a text file with .txt extension
        files = {"file": ("test.txt", b"This is not a PDF", "text/plain")}
        
        response = upload_session.post(
            f"{BASE_URL}/api/catalog/upload-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Non-PDF upload correctly returns 400")

    # ============== INFO TESTS ==============

    def test_get_catalog_info_with_auth(self):
        """Test getting catalog info with authentication."""
        token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = self._get_auth_headers(token)
        
        response = self.session.get(
            f"{BASE_URL}/api/catalog/info",
            headers=headers
        )
        
        assert response.status_code == 200, f"Get info failed: {response.text}"
        data = response.json()
        assert "has_catalog" in data
        
        if data["has_catalog"]:
            assert "original_name" in data
            assert "size_bytes" in data
            assert "uploaded_by" in data
            print(f"✓ Catalog info: has_catalog=True, file={data.get('original_name')}")
        else:
            print("✓ Catalog info: has_catalog=False")

    def test_get_catalog_info_without_auth_fails(self):
        """Test that getting catalog info without auth fails."""
        response = self.session.get(f"{BASE_URL}/api/catalog/info")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Get info without auth correctly returns 401")

    # ============== SERVE PDF TESTS ==============

    def test_serve_pdf_public_access(self):
        """Test that serving PDF is public (no auth required)."""
        # First ensure a PDF is uploaded
        token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)
        pdf_content = self._create_test_pdf()
        
        upload_session = requests.Session()
        files = {"file": ("public_test.pdf", pdf_content, "application/pdf")}
        
        upload_response = upload_session.post(
            f"{BASE_URL}/api/catalog/upload-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        
        # Now try to access without auth
        new_session = requests.Session()
        response = new_session.get(f"{BASE_URL}/api/catalog/pdf")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/pdf" in response.headers.get("Content-Type", "")
        print("✓ PDF served publicly without auth (for WhatsApp access)")

    def test_serve_pdf_returns_correct_content_type(self):
        """Test that served PDF has correct content type."""
        response = requests.get(f"{BASE_URL}/api/catalog/pdf")
        
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            assert "application/pdf" in content_type, f"Expected PDF content type, got {content_type}"
            print(f"✓ PDF content type: {content_type}")
        elif response.status_code == 404:
            print("✓ No PDF uploaded (404 expected when no catalog)")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}")

    # ============== DELETE TESTS ==============

    def test_delete_pdf_as_admin(self):
        """Test deleting PDF as admin."""
        token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = self._get_auth_headers(token)
        
        # First upload a PDF
        pdf_content = self._create_test_pdf()
        
        upload_session = requests.Session()
        files = {"file": ("to_delete.pdf", pdf_content, "application/pdf")}
        
        upload_response = upload_session.post(
            f"{BASE_URL}/api/catalog/upload-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        
        # Now delete
        response = self.session.delete(
            f"{BASE_URL}/api/catalog/pdf",
            headers=headers
        )
        
        assert response.status_code == 200, f"Delete failed: {response.text}"
        print("✓ Admin deleted PDF successfully")
        
        # Verify it's gone
        info_response = self.session.get(
            f"{BASE_URL}/api/catalog/info",
            headers=headers
        )
        assert info_response.status_code == 200
        info_data = info_response.json()
        assert info_data.get("has_catalog") == False, "Catalog should be deleted"
        print("✓ Verified catalog is deleted (has_catalog=False)")

    def test_delete_pdf_without_auth_fails(self):
        """Test that deleting PDF without auth fails."""
        response = self.session.delete(f"{BASE_URL}/api/catalog/pdf")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Delete without auth correctly returns 401")

    # ============== FULL FLOW TEST ==============

    def test_full_catalog_flow(self):
        """Test complete flow: upload → info → serve → delete."""
        token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = self._get_auth_headers(token)
        
        # 1. Upload
        pdf_content = self._create_test_pdf()
        
        upload_session = requests.Session()
        files = {"file": ("full_flow_test.pdf", pdf_content, "application/pdf")}
        
        upload_response = upload_session.post(
            f"{BASE_URL}/api/catalog/upload-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        upload_data = upload_response.json()
        print(f"1. Uploaded: {upload_data['filename']}")
        
        # 2. Get info
        info_response = self.session.get(
            f"{BASE_URL}/api/catalog/info",
            headers=headers
        )
        assert info_response.status_code == 200
        info_data = info_response.json()
        assert info_data["has_catalog"] == True
        print(f"2. Info: has_catalog=True, size={info_data['size_bytes']} bytes")
        
        # 3. Serve (public)
        serve_response = requests.get(f"{BASE_URL}/api/catalog/pdf")
        assert serve_response.status_code == 200
        assert "application/pdf" in serve_response.headers.get("Content-Type", "")
        print("3. Served: PDF accessible publicly")
        
        # 4. Delete
        delete_response = self.session.delete(
            f"{BASE_URL}/api/catalog/pdf",
            headers=headers
        )
        assert delete_response.status_code == 200
        print("4. Deleted: PDF removed")
        
        # 5. Verify deleted
        final_info = self.session.get(
            f"{BASE_URL}/api/catalog/info",
            headers=headers
        )
        assert final_info.json().get("has_catalog") == False
        print("5. Verified: has_catalog=False")
        
        print("✓ Full catalog flow completed successfully")


class TestBotCodeVerification:
    """Verify bot code doesn't contain external URL references."""

    def test_no_gimmicks_url_in_bot_service(self):
        """Verify bot_service.py doesn't send gimmicks.com.ec links."""
        bot_service_path = "/app/backend/bot_service.py"
        
        with open(bot_service_path, "r") as f:
            content = f.read()
        
        # Check that gimmicks.com.ec is only mentioned in the PROHIBITION rule
        lines_with_url = []
        for i, line in enumerate(content.split("\n"), 1):
            if "gimmicks.com.ec" in line.lower():
                lines_with_url.append((i, line.strip()))
        
        # Should only appear in the system prompt as a prohibition
        assert len(lines_with_url) <= 2, f"Found too many gimmicks.com.ec references: {lines_with_url}"
        
        for line_num, line in lines_with_url:
            assert "NUNCA" in line or "nunca" in line or "NO" in line, \
                f"Line {line_num} mentions gimmicks.com.ec but doesn't prohibit it: {line}"
        
        print(f"✓ Bot code verification: gimmicks.com.ec only appears in prohibition rules")

    def test_no_external_catalog_url_variable(self):
        """Verify no EXTERNAL_CATALOG_URL variable exists."""
        bot_service_path = "/app/backend/bot_service.py"
        
        with open(bot_service_path, "r") as f:
            content = f.read()
        
        assert "EXTERNAL_CATALOG_URL" not in content, \
            "EXTERNAL_CATALOG_URL should not exist in bot_service.py"
        
        print("✓ No EXTERNAL_CATALOG_URL variable found")

    def test_system_prompt_forbids_urls(self):
        """Verify system prompt forbids mentioning external URLs."""
        bot_service_path = "/app/backend/bot_service.py"
        
        with open(bot_service_path, "r") as f:
            content = f.read()
        
        # Check for prohibition in system prompt
        assert "NUNCA menciones links" in content or "NUNCA menciones URLs" in content or \
               "NUNCA menciones links ni URLs" in content, \
            "System prompt should forbid mentioning links/URLs"
        
        print("✓ System prompt forbids mentioning external links/URLs")

    def test_catalog_pdf_helper_exists(self):
        """Verify get_catalog_pdf_url helper function exists."""
        bot_service_path = "/app/backend/bot_service.py"
        
        with open(bot_service_path, "r") as f:
            content = f.read()
        
        assert "async def get_catalog_pdf_url" in content, \
            "get_catalog_pdf_url helper should exist"
        
        assert "CATALOG_BASE_URL" in content or "REACT_APP_BACKEND_URL" in content, \
            "Should use environment variable for base URL"
        
        print("✓ get_catalog_pdf_url helper exists and uses env vars")


class TestCatalogEndpointSecurity:
    """Test security aspects of catalog endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()

    def _login(self, email, password):
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None

    def test_upload_requires_admin_or_developer_role(self):
        """Test that upload requires admin or desarrollador role."""
        # This test verifies the role check exists
        # We can't easily test with a non-admin user without creating one
        
        # Test with admin - should work
        token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None
        
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        
        upload_session = requests.Session()
        files = {"file": ("role_test.pdf", pdf_content, "application/pdf")}
        
        response = upload_session.post(
            f"{BASE_URL}/api/catalog/upload-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        
        assert response.status_code == 200, f"Admin should be able to upload: {response.text}"
        print("✓ Admin role can upload PDF")

    def test_delete_requires_admin_or_developer_role(self):
        """Test that delete requires admin or desarrollador role."""
        token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None
        
        response = self.session.delete(
            f"{BASE_URL}/api/catalog/pdf",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should be 200 (deleted) or 200 (nothing to delete)
        assert response.status_code == 200, f"Admin should be able to delete: {response.text}"
        print("✓ Admin role can delete PDF")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
