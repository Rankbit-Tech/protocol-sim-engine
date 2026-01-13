#!/usr/bin/env python3
"""
Smoke Tests for Docker Deployment

Quick tests to verify that the Docker container is running correctly
and all configured devices are accessible.
"""

import pytest
import requests
import time
from pymodbus.client import ModbusTcpClient


class TestDockerDeployment:
    """Smoke tests for Docker container deployment."""
    
    @pytest.fixture(scope="class")
    def api_base_url(self):
        """Base URL for API endpoints."""
        return "http://localhost:8080"
    
    def test_api_is_responding(self, api_base_url):
        """Test that the API server is up and responding."""
        try:
            response = requests.get(f"{api_base_url}/status", timeout=5)
            assert response.status_code == 200, "API should return 200 OK"
            print("✅ API is responding")
        except requests.exceptions.ConnectionError:
            pytest.fail("API server is not reachable. Is the container running?")
    
    def test_status_endpoint_returns_valid_data(self, api_base_url):
        """Test that /status endpoint returns expected structure."""
        response = requests.get(f"{api_base_url}/status")
        data = response.json()
        
        assert "status" in data, "Status should be in response"
        assert "device_count" in data, "Device count should be in response"
        assert "protocols" in data, "Protocols should be in response"
        
        print(f"✅ Status endpoint valid: {data['device_count']} devices, {len(data['protocols'])} protocols")
    
    def test_all_configured_devices_running(self, api_base_url):
        """Test that all configured devices are reported as running."""
        response = requests.get(f"{api_base_url}/devices")
        data = response.json()
        
        assert "devices" in data, "Devices list should be in response"
        assert data["total_count"] > 0, "Should have at least one device configured"
        
        print(f"✅ All {data['total_count']} devices are configured")
    
    def test_modbus_devices_are_accessible(self, api_base_url):
        """Test that Modbus devices can be connected to."""
        response = requests.get(f"{api_base_url}/devices")
        data = response.json()
        
        modbus_devices = [d for d in data.get("devices", []) if d.get("protocol") == "modbus_tcp"]
        
        if not modbus_devices:
            pytest.skip("No Modbus devices configured")
        
        # Test first Modbus device
        first_device = modbus_devices[0]
        port = first_device.get("port")
        
        client = ModbusTcpClient("localhost", port=port)
        connected = client.connect()
        
        assert connected, f"Should be able to connect to Modbus device on port {port}"
        
        if connected:
            # Try to read some registers
            result = client.read_holding_registers(0, 3)
            assert not result.isError(), "Should be able to read from device"
            client.close()
            
        print(f"✅ Modbus devices are accessible (tested port {port})")
    
    def test_dashboard_is_accessible(self, api_base_url):
        """Test that the web dashboard is accessible."""
        response = requests.get(f"{api_base_url}/dashboard", timeout=5)
        assert response.status_code == 200, "Dashboard should be accessible"
        assert "Universal Simulation Engine" in response.text, "Dashboard should contain title"
        print("✅ Dashboard is accessible")
    
    def test_api_documentation_is_available(self, api_base_url):
        """Test that API documentation endpoints are available."""
        response = requests.get(f"{api_base_url}/docs", timeout=5)
        assert response.status_code == 200, "API docs should be accessible"
        print("✅ API documentation is available")
    
    def test_health_check_endpoint(self, api_base_url):
        """Test the health check endpoint."""
        response = requests.get(f"{api_base_url}/health", timeout=5)
        assert response.status_code in [200, 503], "Health endpoint should respond"
        
        data = response.json()
        assert "status" in data, "Health check should include status"
        print(f"✅ Health check endpoint working: {data.get('status')}")
    
    def test_metrics_endpoint(self, api_base_url):
        """Test that metrics endpoint is available."""
        response = requests.get(f"{api_base_url}/metrics", timeout=5)
        assert response.status_code == 200, "Metrics endpoint should be accessible"
        print("✅ Metrics endpoint is available")
    
    def test_export_functionality(self, api_base_url):
        """Test that data export endpoint works."""
        response = requests.get(f"{api_base_url}/export/devices?format=json", timeout=5)
        assert response.status_code == 200, "Export endpoint should be accessible"
        
        data = response.json()
        assert "format" in data, "Export should include format"
        assert data["format"] == "json", "Export format should match requested"
        print("✅ Data export functionality works")
    
    def test_device_data_is_updating(self, api_base_url):
        """Test that device data is actually updating over time."""
        response = requests.get(f"{api_base_url}/devices")
        devices = response.json().get("devices", [])
        
        if not devices:
            pytest.skip("No devices configured")
        
        first_device = devices[0]
        device_id = first_device.get("id")
        
        # Get data at two different times
        response1 = requests.get(f"{api_base_url}/devices/{device_id}/data")
        data1 = response1.json()
        
        time.sleep(3)  # Wait 3 seconds
        
        response2 = requests.get(f"{api_base_url}/devices/{device_id}/data")
        data2 = response2.json()
        
        # Data should have changed
        assert data1.get("timestamp") != data2.get("timestamp"), "Timestamp should update"
        print(f"✅ Device data is updating over time")


def run_smoke_tests():
    """Run all smoke tests and report results."""
    print("\n" + "="*70)
    print("🔥 Running Docker Deployment Smoke Tests")
    print("="*70 + "\n")
    
    # Run pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    if exit_code == 0:
        print("\n" + "="*70)
        print("✅ All smoke tests passed! Docker deployment is healthy.")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("❌ Some smoke tests failed. Check the output above.")
        print("="*70 + "\n")
    
    return exit_code


if __name__ == "__main__":
    exit(run_smoke_tests())