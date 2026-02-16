# Development Guide for Internal Team

**Internal documentation for protocol-sim-engine maintainers and core developers.**

## 🎯 Purpose

This guide covers:

- Release management
- Version tagging
- Docker Hub deployment
- Branching strategy
- Upgrade procedures
- Internal best practices

## 🌳 Git Workflow & Branch Strategy

### Branch Structure

```
main (production)
├── develop (integration)
│   ├── feature/add-mqtt-protocol
│   ├── feature/web-dashboard
│   └── fix/modbus-memory-leak
└── hotfix/critical-security-patch
```

### Branch Types

#### `main` - Production Branch

- **Always production-ready**
- Protected - requires PR + reviews
- Tagged with version numbers
- Auto-deploys to Docker Hub
- Never commit directly

#### `develop` - Integration Branch

- Latest development changes
- Feature integration point
- Pre-release testing
- Merges to `main` for releases

#### `feature/*` - Feature Branches

```bash
# Create from develop
git checkout develop
git pull origin develop
git checkout -b feature/add-opcua-support

# Work on feature...

# Merge back to develop
git checkout develop
git merge feature/add-opcua-support --no-ff
```

#### `fix/*` - Bug Fix Branches

```bash
# Create from develop for regular bugs
git checkout -b fix/modbus-connection-leak

# Create from main for hotfixes
git checkout main
git checkout -b hotfix/critical-security-issue
```

#### `release/*` - Release Preparation

```bash
# Create from develop when ready for release
git checkout develop
git checkout -b release/0.2.0

# Version bump, changelog, final testing
# Then merge to both main AND develop
```

### Workflow Example

```bash
# 1. New Feature
git checkout develop
git checkout -b feature/mqtt-support
# ... develop feature ...
git push origin feature/mqtt-support
# Open PR: feature/mqtt-support → develop

# 2. Prepare Release
git checkout develop
git checkout -b release/0.2.0
# Update version, changelog, docs
git push origin release/0.2.0
# Open PR: release/0.2.0 → main
# Open PR: release/0.2.0 → develop

# 3. Hotfix
git checkout main
git checkout -b hotfix/security-patch
# Fix critical issue
git push origin hotfix/security-patch
# Open PR: hotfix/security-patch → main
# Open PR: hotfix/security-patch → develop
```

## 🏷️ Version Management

### Semantic Versioning

We follow [SemVer](https://semver.org/): `MAJOR.MINOR.PATCH`

```
0.1.0 → Initial release
  ↓
0.1.1 → Bug fix (backward compatible)
  ↓
0.2.0 → New feature (backward compatible)
  ↓
1.0.0 → First stable release
  ↓
2.0.0 → Breaking change
```

### Version Bumping Rules

| Change Type                       | Version Bump | Example       |
| --------------------------------- | ------------ | ------------- |
| Bug fix                           | PATCH        | 0.1.0 → 0.1.1 |
| New feature (backward compatible) | MINOR        | 0.1.1 → 0.2.0 |
| Breaking change                   | MAJOR        | 0.2.0 → 1.0.0 |
| Pre-1.0 breaking change           | MINOR        | 0.2.0 → 0.3.0 |

### Files to Update

When bumping version, update:

1. **`pyproject.toml`**

```toml
[tool.poetry]
name = "protocol-sim-engine"
version = "0.2.0"  # ← Update here
```

2. **`README.md`**

```markdown
**Version**: 0.2.0 # ← Update here
**Last Updated**: January 2026
```

3. **`CHANGELOG.md`** (create if doesn't exist)

```markdown
## [0.2.0] - 2026-01-15

### Added

- MQTT protocol support
- Web dashboard UI

### Fixed

- Modbus connection leak (#45)
```

4. **Docker Tags** (handled by release script)

## 🚀 Release Process

### 1. Pre-Release Checklist

Before starting a release:

- [ ] All features merged to `develop`
- [ ] All tests passing on `develop`
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No known critical bugs
- [ ] Performance tested
- [ ] Security scan clean

### 2. Create Release Branch

```bash
# From develop
git checkout develop
git pull origin develop

# Create release branch
git checkout -b release/0.2.0

# Version bump
# Edit: pyproject.toml, README.md, CHANGELOG.md
sed -i '' 's/version = "0.1.0"/version = "0.2.0"/' pyproject.toml

# Commit version bump
git add .
git commit -m "chore: bump version to 0.2.0"

# Push
git push origin release/0.2.0
```

### 3. Final Testing

```bash
# Build and test locally
docker build -t protocol-sim-engine:0.2.0 .

# Run comprehensive tests
./run_all_tests.sh

# Manual smoke testing
docker run -p 8080:8080 -p 15000-15002:15000-15002 protocol-sim-engine:0.2.0
curl http://localhost:8080/health

# Load testing (if applicable)
```

### 4. Merge to Main

```bash
# Create PR: release/0.2.0 → main
# Get approvals (minimum 2 reviewers)
# Merge with "Create a merge commit" (NOT squash)

# After merge, tag the release
git checkout main
git pull origin main
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

### 5. Merge Back to Develop

```bash
# Keep develop in sync
git checkout develop
git pull origin develop
git merge main
git push origin develop
```

### 6. Docker Hub Release

```bash
# Build production image
docker build -t developeryashsolanki/protocol-sim-engine:0.2.0 .

# Tag variants
docker tag developeryashsolanki/protocol-sim-engine:0.2.0 \
  developeryashsolanki/protocol-sim-engine:0.2

docker tag developeryashsolanki/protocol-sim-engine:0.2.0 \
  developeryashsolanki/protocol-sim-engine:latest

# Push all tags
docker push developeryashsolanki/protocol-sim-engine:0.2.0
docker push developeryashsolanki/protocol-sim-engine:0.2
docker push developeryashsolanki/protocol-sim-engine:latest

# Verify
docker pull developeryashsolanki/protocol-sim-engine:latest
```

### 7. GitHub Release

1. Go to: https://github.com/Rankbit-Tech/protocol-sim-engine/releases/new
2. Tag: `v0.2.0`
3. Title: `v0.2.0 - MQTT Support & Dashboard`
4. Description:

````markdown
## 🎉 What's New

### Features

- ✨ Added MQTT protocol support
- 🎨 New web dashboard UI
- 🔧 Configurable QoS levels

### Improvements

- ⚡ 30% faster data generation
- 📝 Improved API documentation

### Bug Fixes

- 🐛 Fixed Modbus connection leak (#45)
- 🔒 Security patch for dependency

### Docker

```bash
docker pull developeryashsolanki/protocol-sim-engine:0.2.0
```
````

**Full Changelog**: https://github.com/Rankbit-Tech/protocol-sim-engine/compare/v0.1.0...v0.2.0

````

## 🔥 Hotfix Process

For critical production issues:

### 1. Create Hotfix Branch

```bash
# From main
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-patch

# Fix the issue
# ... code changes ...

# Bump patch version
sed -i '' 's/version = "0.2.0"/version = "0.2.1"/' pyproject.toml

# Commit
git add .
git commit -m "fix: critical security vulnerability in auth"
````

### 2. Fast-Track Testing

```bash
# Quick validation
./run_all_tests.sh

# Security scan
docker scan protocol-sim-engine:0.2.1
```

### 3. Merge to Main and Develop

```bash
# PR to main (expedited review)
# Merge immediately after 1 approval

# Tag
git tag -a v0.2.1 -m "Hotfix: Security patch"
git push origin v0.2.1

# Merge to develop
git checkout develop
git merge hotfix/critical-security-patch
git push origin develop
```

### 4. Emergency Docker Release

```bash
# Build and push immediately
docker build -t developeryashsolanki/protocol-sim-engine:0.2.1 .
docker push developeryashsolanki/protocol-sim-engine:0.2.1

# Update latest tag
docker tag developeryashsolanki/protocol-sim-engine:0.2.1 \
  developeryashsolanki/protocol-sim-engine:latest
docker push developeryashsolanki/protocol-sim-engine:latest

# Notify users via GitHub Security Advisory
```

## 📦 Docker Release Management

### Tag Strategy

```
Version 0.2.1:
├── 0.2.1     (exact version - immutable)
├── 0.2       (latest patch in 0.2.x)
└── latest    (latest stable release)
```

### Tagging Rules

```bash
# For version 0.2.1

# 1. Exact version (never changes)
docker tag developeryashsolanki/protocol-sim-engine:0.2.1

# 2. Minor version (updated with patches)
docker tag developeryashsolanki/protocol-sim-engine:0.2

# 3. Latest (updated with every release)
docker tag developeryashsolanki/protocol-sim-engine:latest
```

### Multi-Architecture Builds

```bash
# Build for multiple platforms
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t developeryashsolanki/protocol-sim-engine:0.2.0 \
  --push .
```

### Image Verification

```bash
# After push, verify
docker pull developeryashsolanki/protocol-sim-engine:0.2.0
docker run --rm developeryashsolanki/protocol-sim-engine:0.2.0 --version

# Check digest
docker inspect developeryashsolanki/protocol-sim-engine:0.2.0 | \
  jq '.[0].RepoDigests'
```

## 🔄 Upgrade Procedures

### Minor Version Upgrade (0.1.0 → 0.2.0)

**Preparation:**

```bash
# 1. Review changes
git log v0.1.0..v0.2.0

# 2. Test upgrade path
docker pull developeryashsolanki/protocol-sim-engine:0.1.0
docker pull developeryashsolanki/protocol-sim-engine:0.2.0

# 3. Check config compatibility
diff config/default_config_v0.1.yml config/default_config_v0.2.yml
```

**Deployment:**

```bash
# Rolling update (zero downtime)
docker-compose pull
docker-compose up -d

# Or manual
docker stop protocol-sim-old
docker run -d --name protocol-sim-new \
  -v $(pwd)/config.yml:/config/factory.yml \
  -p 8080:8080 \
  developeryashsolanki/protocol-sim-engine:0.2.0

# Verify
curl http://localhost:8080/health

# Cleanup
docker rm protocol-sim-old
```

### Major Version Upgrade (0.x → 1.0)

**Breaking changes checklist:**

- [ ] Read CHANGELOG.md thoroughly
- [ ] Review migration guide
- [ ] Backup current configuration
- [ ] Test in staging environment
- [ ] Update client code if needed
- [ ] Schedule maintenance window

**Migration:**

```bash
# 1. Backup
docker exec protocol-sim tar czf /backup/data.tar.gz /app/data
docker cp protocol-sim:/backup/data.tar.gz ./backup/

# 2. Stop old version
docker stop protocol-sim

# 3. Run migration script (if provided)
docker run --rm \
  -v $(pwd)/data:/data \
  developeryashsolanki/protocol-sim-engine:1.0.0 \
  python migrate.py --from 0.9.0

# 4. Start new version
docker run -d --name protocol-sim \
  -v $(pwd)/config.yml:/config/factory.yml \
  -p 8080:8080 \
  developeryashsolanki/protocol-sim-engine:1.0.0

# 5. Verify
curl http://localhost:8080/health
```

## 🧪 Testing Strategy

### Pre-Commit

```bash
# Run before every commit
poetry run pytest tests/unit/
poetry run ruff check src/
poetry run mypy src/
```

### Pre-PR

```bash
# Run before opening PR
./run_all_tests.sh
poetry run pytest --cov=src --cov-report=html
```

### Pre-Release

```bash
# Comprehensive testing
./run_all_tests.sh
docker build -t protocol-sim-engine:test .

# Load testing
docker run -d --name load-test protocol-sim-engine:test
# Run load tests...

# Security scanning
docker scan protocol-sim-engine:test
```

## 📊 Monitoring & Rollback

### Health Checks

```bash
# Container health
docker ps --filter "name=protocol-sim" --format "{{.Status}}"

# API health
curl http://localhost:8080/health | jq '.status'

# Metrics
curl http://localhost:8080/metrics
```

### Rollback Procedure

```bash
# Quick rollback
docker stop protocol-sim-new
docker start protocol-sim-old

# Or pull previous version
docker pull developeryashsolanki/protocol-sim-engine:0.1.0
docker run -d --name protocol-sim-rollback \
  developeryashsolanki/protocol-sim-engine:0.1.0

# Notify team
```

## 🔐 Security Practices

### Dependency Updates

```bash
# Monthly dependency audit
poetry update
poetry run safety check

# Update Docker base image
docker pull python:3.12-slim
docker build -t protocol-sim-engine:latest .
```

### Secret Management

**Never commit:**

- API keys
- Passwords
- Private keys
- Tokens

**Use:**

- Environment variables
- Docker secrets
- External secret managers

```bash
# Good
docker run -e API_KEY=$API_KEY protocol-sim-engine:latest

# Bad
docker run -e API_KEY="hardcoded-key-123" protocol-sim-engine:latest
```

## 📝 Documentation Maintenance

### Keep Updated

- [ ] README.md - Quick start, features
- [ ] API documentation - OpenAPI specs
- [ ] CHANGELOG.md - All changes
- [ ] Migration guides - Breaking changes
- [ ] Architecture docs - System design

### Review Cycle

- **Monthly**: Review and update docs
- **Per release**: Update all version references
- **Per breaking change**: Write migration guide

## 🎓 Internal Resources

### Team Knowledge Base

- **Architecture decisions**: `/docs/architecture/`
- **Protocol specs**: `/docs/protocols/`
- **Performance benchmarks**: `/docs/performance/`
- **Security guidelines**: `/docs/security/`

### Tools

- **Linting**: `ruff`
- **Type checking**: `mypy`
- **Testing**: `pytest`
- **Coverage**: `pytest-cov`
- **Docker**: `docker`, `docker-compose`

## 🚦 Release Checklist

Copy this for every release:

```markdown
## Release 0.x.0 Checklist

### Pre-Release

- [ ] All features merged to develop
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in all files
- [ ] Release branch created

### Testing

- [ ] Unit tests pass (100%)
- [ ] Integration tests pass
- [ ] Smoke tests pass
- [ ] Load testing done
- [ ] Security scan clean
- [ ] Manual testing complete

### Release

- [ ] PR to main created
- [ ] 2+ approvals received
- [ ] Merged to main
- [ ] Tagged (vX.Y.Z)
- [ ] Merged back to develop

### Docker

- [ ] Image built (X.Y.Z)
- [ ] Tags created (X.Y, latest)
- [ ] Pushed to Docker Hub
- [ ] Pull test successful
- [ ] Run test successful

### Post-Release

- [ ] GitHub release created
- [ ] Announcement posted
- [ ] Documentation site updated
- [ ] Team notified
- [ ] Monitoring verified

### Rollback Plan

- [ ] Previous version tagged
- [ ] Rollback procedure documented
- [ ] Team knows rollback steps
```

## 🎯 Performance Targets

| Metric       | Target  | Action if Exceeded    |
| ------------ | ------- | --------------------- |
| Image size   | < 1GB   | Optimize dependencies |
| Startup time | < 10s   | Profile and optimize  |
| Memory usage | < 512MB | Investigate leaks     |
| API response | < 100ms | Add caching           |
| Device spawn | < 1s    | Parallelize           |

## 📞 Emergency Contacts

**For production incidents:**

1. **Check status**: `curl http://api/health`
2. **View logs**: `docker logs protocol-sim`
3. **Quick rollback**: `docker start protocol-sim-old`
4. **Notify team**: Slack #incidents channel

---

**This is a living document. Update it as processes evolve.** 🚀

Last Updated: February 2026 | Version: 1.1
