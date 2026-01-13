#!/usr/bin/env python3
"""
Industrial Facility Simulator - Main Entry Point

This is the main application entry point that orchestrates the entire simulation platform.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config_parser import ConfigParser
from .orchestrator import SimulationOrchestrator
from .utils.logging_config import setup_logging

# Configure structured logging
logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Industrial Facility Simulator",
    description="Open Source Industrial Protocol & Device Simulation Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


class IndustrialFacilitySimulator:
    """Main application class that manages the entire simulation platform."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize the simulator with optional configuration file."""
        self.config_file = config_file or Path("config/default_config.yml")
        self.config_parser = ConfigParser()
        self.orchestrator: Optional[SimulationOrchestrator] = None
        self.running = False
        
    async def initialize(self) -> bool:
        """Initialize the simulation platform."""
        try:
            logger.info("Initializing Industrial Facility Simulator...")
            
            # Load and validate configuration
            config = await self.config_parser.load_config(self.config_file)
            if not config:
                logger.error("Failed to load configuration")
                return False
                
            # Create orchestrator
            self.orchestrator = SimulationOrchestrator(config)
            
            # Initialize orchestrator
            if not await self.orchestrator.initialize():
                logger.error("Failed to initialize orchestrator")
                return False
                
            logger.info("Industrial Facility Simulator initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize simulator", error=str(e))
            return False
            
    async def start_simulation(self) -> bool:
        """Start the simulation with all configured devices."""
        try:
            if not self.orchestrator:
                logger.error("Orchestrator not initialized")
                return False
                
            logger.info("Starting Industrial Facility Simulation...")
            
            # Start all devices and protocols
            if not await self.orchestrator.start_all_devices():
                logger.error("Failed to start devices")
                return False
                
            self.running = True
            logger.info(
                "Industrial Facility Simulation started successfully",
                device_count=self.orchestrator.get_device_count(),
                protocols=list(self.orchestrator.get_active_protocols())
            )
            return True
            
        except Exception as e:
            logger.error("Failed to start simulation", error=str(e))
            return False
            
    async def stop_simulation(self) -> None:
        """Stop the simulation and cleanup resources."""
        try:
            logger.info("Stopping Industrial Facility Simulation...")
            
            if self.orchestrator:
                await self.orchestrator.stop_all_devices()
                
            self.running = False
            logger.info("Industrial Facility Simulation stopped successfully")
            
        except Exception as e:
            logger.error("Error during simulation shutdown", error=str(e))
            
    def get_status(self) -> dict:
        """Get current simulation status."""
        if not self.orchestrator:
            return {"status": "not_initialized"}
            
        return {
            "status": "running" if self.running else "stopped",
            "device_count": self.orchestrator.get_device_count(),
            "protocols": list(self.orchestrator.get_active_protocols()),
            "health": self.orchestrator.get_health_status()
        }


# Global simulator instance
simulator = IndustrialFacilitySimulator()


@app.on_event("startup")
async def startup_event():
    """FastAPI startup event handler."""
    setup_logging()
    logger.info("Starting Industrial Facility Simulator API...")
    
    # Initialize simulator
    if await simulator.initialize():
        # Start simulation automatically when API starts
        if await simulator.start_simulation():
            logger.info("Simulator API ready and devices started")
        else:
            logger.warning("Simulator API ready but devices failed to start")
    else:
        logger.error("Failed to initialize simulator")
        sys.exit(1)


@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event handler."""
    logger.info("Shutting down Industrial Facility Simulator API...")
    await simulator.stop_simulation()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=/dashboard">
        <title>Redirecting...</title>
    </head>
    <body>
        <p>Redirecting to <a href="/dashboard">dashboard</a>...</p>
    </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the monitoring dashboard."""
    dashboard_path = Path(__file__).parent / "web_interface" / "templates" / "dashboard.html"
    try:
        with open(dashboard_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Dashboard not found</h1><p>Dashboard template is missing.</p>"

@app.get("/data-monitor", response_class=HTMLResponse)
async def data_monitor():
    """Serve the real-time data monitoring page."""
    monitor_path = Path(__file__).parent / "web_interface" / "templates" / "data_monitor.html"
    try:
        with open(monitor_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Data Monitor not found</h1><p>Data monitor template is missing.</p>"

@app.get("/api")
async def api_info():
    """API endpoint with basic information."""
    return {
        "name": "Industrial Facility Simulator",
        "version": "0.1.0",
        "description": "Open Source Industrial Protocol & Device Simulation Platform",
        "status": simulator.get_status(),
        "endpoints": {
            "dashboard": "/dashboard",
            "api_docs": "/docs",
            "status": "/status",
            "devices": "/devices",
            "protocols": "/protocols",
            "metrics": "/metrics",
            "health": "/health"
        }
    }


@app.get("/status")
async def get_status():
    """Get detailed simulation status."""
    return simulator.get_status()


@app.post("/simulation/start")
async def start_simulation():
    """Start the simulation."""
    success = await simulator.start_simulation()
    return {
        "success": success,
        "message": "Simulation started" if success else "Failed to start simulation",
        "status": simulator.get_status()
    }


@app.post("/simulation/stop")
async def stop_simulation():
    """Stop the simulation."""
    await simulator.stop_simulation()
    return {
        "success": True,
        "message": "Simulation stopped",
        "status": simulator.get_status()
    }

@app.get("/devices")
async def list_devices():
    """List all simulated devices with their current status."""
    if not simulator.orchestrator:
        return {"error": "Simulator not initialized"}
    
    devices = simulator.orchestrator.get_all_devices()
    return {
        "total_count": len(devices),
        "devices": devices
    }

@app.get("/devices/{device_id}")
async def get_device_details(device_id: str):
    """Get detailed information about a specific device."""
    if not simulator.orchestrator:
        return {"error": "Simulator not initialized"}
    
    device = simulator.orchestrator.get_device_info(device_id)
    if not device:
        return {"error": f"Device {device_id} not found"}
    
    return device

@app.get("/devices/{device_id}/data")
async def get_device_data(device_id: str):
    """Get current data values from a specific device."""
    if not simulator.orchestrator:
        return {"error": "Simulator not initialized"}
    
    data = simulator.orchestrator.get_device_data(device_id)
    if data is None:
        return {"error": f"Device {device_id} not found or no data available"}
    
    # Return the data directly as it already contains all needed fields
    return data

@app.get("/protocols")
async def list_protocols():
    """List all active protocols and their device counts."""
    if not simulator.orchestrator:
        return {"error": "Simulator not initialized"}
    
    return {
        "active_protocols": simulator.orchestrator.get_protocol_summary()
    }

@app.get("/protocols/{protocol_name}/devices")
async def list_protocol_devices(protocol_name: str):
    """List all devices for a specific protocol."""
    if not simulator.orchestrator:
        return {"error": "Simulator not initialized"}
    
    devices = simulator.orchestrator.get_devices_by_protocol(protocol_name)
    return {
        "protocol": protocol_name,
        "device_count": len(devices),
        "devices": devices
    }

@app.get("/metrics")
async def get_metrics():
    """Get system performance metrics."""
    if not simulator.orchestrator:
        return {"error": "Simulator not initialized"}
    
    return simulator.orchestrator.get_performance_metrics()

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    if not simulator.orchestrator:
        return {"status": "unhealthy", "reason": "Simulator not initialized"}
    
    health = simulator.orchestrator.get_health_status()
    status_code = 200 if health.get("healthy", False) else 503
    
    return health

@app.get("/export/devices")
async def export_devices_data(format: str = "json"):
    """Export all device data in specified format (json, csv)."""
    if not simulator.orchestrator:
        return {"error": "Simulator not initialized"}
    
    data = simulator.orchestrator.export_all_device_data(format)
    return {
        "format": format,
        "device_count": data.get("device_count", 0),
        "timestamp": data.get("timestamp"),
        "data": data.get("data", [])
    }


async def main():
    """Main async function for running the simulator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Industrial Facility Simulator")
    parser.add_argument(
        "--config", 
        type=Path, 
        help="Configuration file path",
        default="config/default_config.yml"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Run only the API server without starting simulation"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API server host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="API server port"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    try:
        # Initialize simulator
        global simulator
        simulator = IndustrialFacilitySimulator(args.config)
        
        if not await simulator.initialize():
            logger.error("Failed to initialize simulator")
            return 1
            
        # Start simulation if not API-only mode
        if not args.api_only:
            if not await simulator.start_simulation():
                logger.error("Failed to start simulation")
                return 1
                
        # Start API server
        logger.info(f"Starting API server on {args.host}:{args.port}")
        config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
        server = uvicorn.Server(config)
        
        # Run server
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await simulator.stop_simulation()
        return 0
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        return 1
    finally:
        await simulator.stop_simulation()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
