"""
Intelligent Port Management System

This module manages port allocation across all protocols to prevent conflicts
and optimize resource usage.
"""

import asyncio
from typing import Dict, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger(__name__)

class PortPool:
    """Manages a pool of available ports for a specific protocol."""
    
    def __init__(self, start_port: int, end_port: int, protocol: str):
        """
        Initialize a port pool.
        
        Args:
            start_port: First port in the range
            end_port: Last port in the range
            protocol: Protocol name for this pool
        """
        self.start_port = start_port
        self.end_port = end_port
        self.protocol = protocol
        self.allocated_ports: Set[int] = set()
        self.available_ports = set(range(start_port, end_port + 1))
        
    def allocate(self, count: int, preferred_start: Optional[int] = None) -> Optional[List[int]]:
        """
        Allocate a contiguous block of ports.
        
        Args:
            count: Number of ports needed
            preferred_start: Preferred starting port (optional)
            
        Returns:
            List of allocated ports or None if not available
        """
        if count <= 0:
            return []
            
        # Check if we have enough available ports
        if len(self.available_ports) < count:
            logger.warning(
                f"Not enough ports available in {self.protocol} pool",
                requested=count,
                available=len(self.available_ports)
            )
            return None
            
        allocated = []
        
        # Try preferred start if specified
        if preferred_start and self._can_allocate_from(preferred_start, count):
            allocated = list(range(preferred_start, preferred_start + count))
        else:
            # Find best contiguous block
            allocated = self._find_contiguous_block(count)
            
        if allocated:
            for port in allocated:
                self.allocated_ports.add(port)
                self.available_ports.discard(port)
                
            logger.info(
                f"Allocated ports for {self.protocol}",
                ports=allocated,
                remaining=len(self.available_ports)
            )
            
        return allocated
    
    def _can_allocate_from(self, start_port: int, count: int) -> bool:
        """Check if we can allocate 'count' ports starting from start_port."""
        required_ports = set(range(start_port, start_port + count))
        return required_ports.issubset(self.available_ports)
    
    def _find_contiguous_block(self, count: int) -> Optional[List[int]]:
        """Find the best contiguous block of ports."""
        available_sorted = sorted(self.available_ports)
        
        for i in range(len(available_sorted) - count + 1):
            start_port = available_sorted[i]
            required_ports = list(range(start_port, start_port + count))
            
            # Check if this contiguous block is available
            if all(port in self.available_ports for port in required_ports):
                return required_ports
                
        return None
    
    def deallocate(self, ports: List[int]) -> None:
        """Deallocate previously allocated ports."""
        for port in ports:
            if port in self.allocated_ports:
                self.allocated_ports.remove(port)
                self.available_ports.add(port)
                
        logger.info(f"Deallocated {len(ports)} ports for {self.protocol}")
    
    def available_count(self) -> int:
        """Get number of available ports."""
        return len(self.available_ports)
    
    def is_port_available(self, port: int) -> bool:
        """Check if a specific port is available."""
        return port in self.available_ports

class IntelligentPortManager:
    """
    Intelligent port management system that prevents conflicts and optimizes allocation.
    """
    
    def __init__(self):
        """Initialize the port manager."""
        self.port_pools: Dict[str, PortPool] = {}
        self.device_port_mappings: Dict[str, List[int]] = {}
        
    def initialize_pools(self, port_ranges: Dict[str, List[int]]) -> None:
        """
        Initialize port pools for different protocols.
        
        Args:
            port_ranges: Dictionary mapping protocol names to [start, end] ranges
        """
        for protocol, port_range in port_ranges.items():
            if len(port_range) != 2:
                logger.warning(f"Invalid port range for {protocol}: {port_range}")
                continue
                
            start_port, end_port = port_range
            self.port_pools[protocol] = PortPool(start_port, end_port, protocol)
            
        logger.info(
            "Port pools initialized",
            pools=list(self.port_pools.keys()),
            total_ports=sum(pool.available_count() for pool in self.port_pools.values())
        )
    
    def allocate_ports(self, protocol: str, device_id: str, count: int, 
                      preferred_start: Optional[int] = None) -> Optional[List[int]]:
        """
        Allocate ports for a specific device.
        
        Args:
            protocol: Protocol name
            device_id: Unique device identifier
            count: Number of ports needed
            preferred_start: Preferred starting port
            
        Returns:
            List of allocated ports or None if allocation failed
        """
        if protocol not in self.port_pools:
            logger.error(f"No port pool configured for protocol: {protocol}")
            return None
            
        if device_id in self.device_port_mappings:
            logger.warning(f"Device {device_id} already has allocated ports")
            return self.device_port_mappings[device_id]
            
        pool = self.port_pools[protocol]
        allocated_ports = pool.allocate(count, preferred_start)
        
        if allocated_ports:
            self.device_port_mappings[device_id] = allocated_ports
            logger.info(
                "Ports allocated successfully",
                device_id=device_id,
                protocol=protocol,
                ports=allocated_ports
            )
        else:
            logger.error(
                "Port allocation failed",
                device_id=device_id,
                protocol=protocol,
                requested=count
            )
            
        return allocated_ports
    
    def deallocate_device_ports(self, device_id: str) -> bool:
        """
        Deallocate all ports for a specific device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if deallocation was successful
        """
        if device_id not in self.device_port_mappings:
            logger.warning(f"No ports allocated for device: {device_id}")
            return False
            
        ports = self.device_port_mappings[device_id]
        
        # Find which protocol this device belongs to
        for protocol, pool in self.port_pools.items():
            if ports[0] >= pool.start_port and ports[0] <= pool.end_port:
                pool.deallocate(ports)
                break
                
        del self.device_port_mappings[device_id]
        logger.info(f"Deallocated ports for device {device_id}", ports=ports)
        return True
    
    def get_device_ports(self, device_id: str) -> Optional[List[int]]:
        """Get ports allocated to a specific device."""
        return self.device_port_mappings.get(device_id)
    
    def get_port_utilization(self) -> Dict[str, Dict[str, int]]:
        """Get port utilization statistics for all protocols."""
        utilization = {}
        
        for protocol, pool in self.port_pools.items():
            total_ports = pool.end_port - pool.start_port + 1
            used_ports = len(pool.allocated_ports)
            available_ports = len(pool.available_ports)
            
            utilization[protocol] = {
                "total": total_ports,
                "used": used_ports,
                "available": available_ports,
                "utilization_percent": round((used_ports / total_ports) * 100, 2)
            }
            
        return utilization
    
    def validate_allocation_plan(self, allocation_plan: Dict[str, Tuple[str, int]]) -> bool:
        """
        Validate a complete allocation plan before execution.
        
        Args:
            allocation_plan: Dict mapping device_id to (protocol, count)
            
        Returns:
            True if the entire plan can be executed
        """
        # Create temporary pools to simulate allocation
        temp_pools = {}
        for protocol, pool in self.port_pools.items():
            temp_pools[protocol] = PortPool(pool.start_port, pool.end_port, protocol)
            # Copy current allocations
            for port in pool.allocated_ports:
                temp_pools[protocol].allocated_ports.add(port)
                temp_pools[protocol].available_ports.discard(port)
        
        # Try to allocate all devices
        for device_id, (protocol, count) in allocation_plan.items():
            if protocol not in temp_pools:
                logger.error(f"Unknown protocol in allocation plan: {protocol}")
                return False
                
            allocated = temp_pools[protocol].allocate(count)
            if not allocated:
                logger.error(
                    "Allocation plan validation failed",
                    device_id=device_id,
                    protocol=protocol,
                    requested=count
                )
                return False
                
        logger.info("Allocation plan validation successful")
        return True
    
    def generate_allocation_report(self) -> Dict[str, any]:
        """Generate comprehensive allocation report."""
        report = {
            "total_devices": len(self.device_port_mappings),
            "protocols": {},
            "devices": {},
            "utilization": self.get_port_utilization()
        }
        
        # Protocol summary
        for protocol, pool in self.port_pools.items():
            report["protocols"][protocol] = {
                "total_ports": pool.end_port - pool.start_port + 1,
                "allocated_ports": len(pool.allocated_ports),
                "available_ports": len(pool.available_ports)
            }
        
        # Device mappings
        for device_id, ports in self.device_port_mappings.items():
            report["devices"][device_id] = {
                "ports": ports,
                "count": len(ports)
            }
            
        return report
    
    async def monitor_port_health(self) -> Dict[str, bool]:
        """Monitor the health of allocated ports."""
        # This could be extended to actually check if ports are responding
        health_status = {}
        
        for device_id, ports in self.device_port_mappings.items():
            # For now, assume all allocated ports are healthy
            # In a real implementation, you could ping the ports or check service status
            health_status[device_id] = True
            
        return health_status