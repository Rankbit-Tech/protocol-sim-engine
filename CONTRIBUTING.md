# Contributing to Protocol Sim Engine

Thanks for considering contributing! We love your input! 🎉

## 🚀 Quick Start for Contributors

```bash
# Fork the repo first on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/protocol-sim-engine.git
cd protocol-sim-engine

# Set up development environment
poetry install

# Create a branch
git checkout -b feature/your-amazing-feature

# Make your changes and test
poetry run pytest

# Commit and push
git commit -m "feat: add amazing feature"
git push origin feature/your-amazing-feature

# Open a Pull Request
```

## 🎯 Ways to Contribute

### 🐛 Report Bugs

Found a bug? [Open an issue](https://github.com/Rankbit-Tech/protocol-sim-engine/issues/new) with:

- Clear title (e.g., "Modbus device crashes on invalid register")
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, Docker version)
- Logs if available

### 💡 Suggest Features

Have an idea? We'd love to hear it!

- [Open a feature request](https://github.com/Rankbit-Tech/protocol-sim-engine/issues/new)
- Describe the use case
- Explain why it's valuable
- Propose a solution (optional)

### 📝 Improve Documentation

- Fix typos
- Add examples
- Clarify confusing sections
- Translate documentation

### 🔧 Submit Code

- Fix bugs
- Implement features
- Add tests
- Improve performance

## 🌿 Branch Naming Convention

We use a clear, descriptive branch naming system:

```bash
# Feature branches
feature/add-mqtt-protocol
feature/web-dashboard
feature/opcua-simulator

# Bug fixes
fix/modbus-connection-leak
fix/port-allocation-race
fix/docker-healthcheck

# Documentation
docs/add-mqtt-examples
docs/update-api-guide
docs/fix-typos

# Performance improvements
perf/optimize-data-generation
perf/reduce-memory-usage

# Refactoring
refactor/split-orchestrator
refactor/simplify-config-parser

# Chores (dependencies, build, CI)
chore/update-dependencies
chore/add-ci-workflow
chore/improve-dockerfile
```

**Pattern:** `type/short-kebab-case-description`

## 💻 Development Setup

### Prerequisites

- Python 3.12+
- Poetry 1.5+
- Docker 24+
- Git

### Installation

```bash
# Clone your fork (replace YOUR_USERNAME with your GitHub username)
git clone https://github.com/YOUR_USERNAME/protocol-sim-engine.git
cd protocol-sim-engine

# Add upstream remote
git remote add upstream https://github.com/Rankbit-Tech/protocol-sim-engine.git

# Install dependencies
poetry install

# Verify setup
poetry run pytest
```

### Run Locally (Without Docker)

```bash
# Start the simulator
poetry run python src/main.py

# In another terminal - test it
curl http://localhost:8080/health
```

### Run with Docker

```bash
# Build
docker build -t protocol-sim-engine:dev .

# Run
docker run -p 8080:8080 -p 15000-15002:15000-15002 protocol-sim-engine:dev
```

## 📋 Coding Standards

### Python Style Guide

We follow **PEP 8** with some preferences:

```python
# ✅ Good
def simulate_temperature_sensor(
    device_id: str,
    min_temp: float = 20.0,
    max_temp: float = 35.0
) -> dict[str, Any]:
    """
    Simulate a temperature sensor with realistic noise.

    Args:
        device_id: Unique identifier for the device
        min_temp: Minimum temperature in Celsius
        max_temp: Maximum temperature in Celsius

    Returns:
        Dictionary with temperature, humidity, and timestamp
    """
    temperature = random.uniform(min_temp, max_temp)
    return {
        "device_id": device_id,
        "temperature": round(temperature, 2),
        "timestamp": time.time()
    }


# ❌ Bad - no type hints, no docstring, unclear names
def sim(d, a, b):
    t = random.uniform(a, b)
    return {"d": d, "t": round(t, 2), "ts": time.time()}
```

### Key Principles

#### 1. **Type Hints Everywhere**

```python
# ✅ Good
def create_device(config: dict[str, Any]) -> ModbusDevice:
    pass

# ❌ Bad
def create_device(config):
    pass
```

#### 2. **Descriptive Names**

```python
# ✅ Good
temperature_reading = sensor.get_current_temperature()
is_device_healthy = device.health_check()

# ❌ Bad
temp = sensor.get()
flag = device.check()
```

#### 3. **Small Functions**

```python
# ✅ Good - Single responsibility
def validate_port_range(port: int) -> bool:
    """Check if port is in valid range."""
    return 1024 <= port <= 65535

def allocate_port(protocol: str) -> int:
    """Allocate next available port for protocol."""
    port = get_next_port(protocol)
    if not validate_port_range(port):
        raise PortAllocationError(f"Invalid port: {port}")
    return port

# ❌ Bad - Does too much
def allocate_and_validate_and_register_port(protocol, device, manager):
    # 50 lines of mixed concerns
    pass
```

#### 4. **Clear Error Handling**

```python
# ✅ Good
try:
    device = create_modbus_device(config)
except ConfigurationError as e:
    logger.error(f"Invalid device config: {e}")
    raise
except Exception as e:
    logger.exception(f"Unexpected error creating device: {e}")
    raise DeviceCreationError(f"Failed to create device") from e

# ❌ Bad
try:
    device = create_modbus_device(config)
except:
    pass  # Silent failure
```

#### 5. **Comprehensive Docstrings**

```python
def simulate_pressure_sensor(
    device_id: str,
    pressure_range: tuple[float, float],
    noise_level: float = 0.1
) -> dict[str, float]:
    """
    Simulate industrial pressure sensor with realistic noise.

    Generates pressure readings with:
    - Random walk simulation
    - Gaussian noise
    - Occasional spikes (simulating disturbances)

    Args:
        device_id: Unique device identifier (e.g., "pressure_001")
        pressure_range: Min and max pressure in PSI (e.g., (100, 200))
        noise_level: Noise as fraction of range (default: 0.1 = 10%)

    Returns:
        Dictionary with 'pressure', 'timestamp', and 'status' keys

    Example:
        >>> sensor = simulate_pressure_sensor("P001", (100, 150))
        >>> print(sensor["pressure"])
        123.45
    """
    pass
```

### Code Organization

```
src/
├── protocols/           # Protocol implementations
│   ├── __init__.py
│   └── industrial/
│       ├── modbus/
│       │   ├── __init__.py
│       │   └── modbus_simulator.py
│       ├── mqtt/
│       │   ├── __init__.py
│       │   ├── mqtt_simulator.py
│       │   └── mqtt_broker.py
│       └── opcua/
│           ├── __init__.py
│           └── opcua_simulator.py
├── data_patterns/       # Data generation
├── utils/              # Utilities
└── main.py            # Entry point
```

## 🧪 Testing

### Write Tests for Everything

```python
# tests/unit/test_temperature_sensor.py
import pytest
from src.protocols.industrial.modbus.temperature_sensor import TemperatureSensor


def test_temperature_within_range():
    """Temperature should stay within configured range."""
    sensor = TemperatureSensor(temp_range=(20.0, 30.0))

    # Test 100 readings
    for _ in range(100):
        temp = sensor.read_temperature()
        assert 20.0 <= temp <= 30.0


def test_temperature_sensor_noise():
    """Temperature should vary (not constant)."""
    sensor = TemperatureSensor(temp_range=(20.0, 30.0))

    readings = [sensor.read_temperature() for _ in range(10)]

    # Should have variation
    assert len(set(readings)) > 1


def test_invalid_temperature_range():
    """Should reject invalid temperature ranges."""
    with pytest.raises(ValueError):
        TemperatureSensor(temp_range=(30.0, 20.0))  # Max < Min
```

### Test Coverage

Aim for **80%+ coverage**:

```bash
# Run tests with coverage
poetry run pytest --cov=src --cov-report=html

# View report
open htmlcov/index.html
```

### Test Types

1. **Unit Tests** - Test individual functions/classes
2. **Integration Tests** - Test component interactions
3. **Smoke Tests** - Test critical paths end-to-end

```bash
# Run specific test types
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/smoke/
```

## 📝 Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format
<type>(<scope>): <description>

# Types
feat:     New feature
fix:      Bug fix
docs:     Documentation only
style:    Formatting, missing semicolons, etc.
refactor: Code restructuring (no behavior change)
perf:     Performance improvements
test:     Adding or updating tests
chore:    Build process, dependencies, etc.
```

### Examples

```bash
# ✅ Good commits
feat(modbus): add support for coil registers
fix(port-manager): prevent port collision race condition
docs(api): add examples for /devices endpoint
perf(data-gen): optimize temperature simulation algorithm
test(modbus): add integration tests for device lifecycle

# ❌ Bad commits
"Fixed stuff"
"Update"
"WIP"
"Final fix (for real this time)"
```

### Commit Message Guidelines

```bash
# ✅ Good - Clear, specific, explains why
feat(mqtt): add QoS level configuration

Adds support for configuring MQTT QoS levels per device.
This allows users to balance reliability vs performance
for different device types.

Closes #123

# ❌ Bad - Vague, no context
"Add feature"
```

## 🔍 Pull Request Process

### Before Opening a PR

- ✅ Tests pass: `poetry run pytest`
- ✅ Code is formatted: `poetry run ruff format src/`
- ✅ Linter is happy: `poetry run ruff check src/`
- ✅ Type checking passes: `poetry run mypy src/`
- ✅ Documentation updated (if needed)
- ✅ Commit messages follow conventions

### PR Template

```markdown
## Description

Brief description of what this PR does.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

How did you test this?

## Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] All tests pass
```

### PR Review Process

1. **Open PR** - Against `main` branch
2. **Automated checks** - CI runs tests, linting, etc.
3. **Code review** - Maintainers review (usually within 2 days)
4. **Address feedback** - Make requested changes
5. **Approval** - Maintainer approves
6. **Merge** - Squash and merge to main

## 🎨 Code Review Guidelines

### As a Reviewer

**Be kind and constructive:**

```markdown
# ✅ Good

"Consider extracting this into a separate function for better testability.
What do you think about moving it to utils/validation.py?"

# ❌ Bad

"This is terrible code. Rewrite it."
```

**Focus on:**

- Correctness
- Test coverage
- Code clarity
- Performance implications
- Security concerns

### As a Contributor

**Respond to feedback:**

- Ask questions if unclear
- Explain your reasoning
- Be open to suggestions
- Update code promptly

## 🏗️ Adding New Protocols

Want to add MQTT, OPC-UA, or another protocol? Here's the structure:

```python
# src/protocols/industrial/mqtt/mqtt_simulator.py
from abc import ABC, abstractmethod

class MQTTDevice(ABC):
    """Base class for MQTT devices."""

    def __init__(self, device_id: str, config: dict):
        self.device_id = device_id
        self.config = config

    @abstractmethod
    def generate_data(self) -> dict:
        """Generate device data."""
        pass

    @abstractmethod
    def publish_data(self) -> None:
        """Publish data to MQTT broker."""
        pass
```

**Steps:**

1. Create protocol directory in `src/protocols/industrial/`
2. Implement base device class
3. Add device templates in `config/device_templates/`
4. Write comprehensive tests
5. Update documentation
6. Open PR with examples

## 🐳 Docker Best Practices

### Multi-Stage Builds

Keep images small and secure:

```dockerfile
# Use builder pattern
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --only=main

FROM python:3.12-slim
COPY --from=builder /app /app
# ... rest of Dockerfile
```

### Security

- Don't run as root
- Use specific versions
- Scan for vulnerabilities

## 📚 Documentation

### README Updates

- Keep Quick Start simple
- Add examples for new features
- Update API endpoints list

### Inline Documentation

```python
# ✅ Good - Explains WHY, not just WHAT
# We use a lock here to prevent port allocation race conditions
# between multiple threads creating devices simultaneously
with self._allocation_lock:
    port = self._get_next_available_port()
```

### API Documentation

Update OpenAPI specs when adding endpoints

## ⚡ Performance Guidelines

### Async Where Possible

```python
# ✅ Good - Non-blocking I/O
async def fetch_device_data(device_id: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"/devices/{device_id}") as response:
            return await response.json()
```

### Profile Before Optimizing

```python
import cProfile

# Profile your code
cProfile.run('expensive_function()')
```

### Memory Management

```python
# ✅ Good - Use generators for large datasets
def get_all_readings():
    for device in devices:
        yield device.get_reading()

# ❌ Bad - Loads everything into memory
def get_all_readings():
    return [device.get_reading() for device in devices]
```

## 🎯 First-Time Contributors

Looking for something easy to start with? Check issues labeled:

- `good first issue` - Perfect for beginners
- `help wanted` - We'd appreciate help
- `documentation` - Improve docs

## 💬 Communication

- **GitHub Issues** - Bug reports, feature requests
- **Pull Requests** - Code review discussions
- **Discussions** - General questions, ideas

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort! 🎉

**Questions?** Open an issue or reach out to the maintainers.

---

**Happy Coding!** 🚀
