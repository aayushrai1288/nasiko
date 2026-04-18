# Contributing to Nasiko

Thank you for your interest in contributing to Nasiko! We welcome contributions from the community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/nasiko.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Git

### Local Development

```bash
# Clone the repository
git clone https://github.com/Nasiko-Labs/nasiko.git
cd nasiko

# Install dependencies (using uv)
uv sync

# Or using pip
pip install -e "."

# Start local services
docker compose -f docker-compose.local.yml up -d
```

## Project Structure

```
nasiko/
├── agent-gateway/    # API Gateway service
├── agents/           # Agent definitions and templates
├── app/              # Web application
├── cli/              # Command-line interface
├── docs/             # Documentation
├── models/           # Data models and schemas
├── orchestrator/     # Agent orchestration logic
└── worker/           # Background task workers
```

## Code Style

- **Python**: Follow PEP 8
- **Type hints**: Use type annotations where possible
- **Documentation**: Add docstrings for public APIs

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=nasiko
```

## Submitting Changes

1. **Small, focused PRs**: Keep changes minimal and focused on a single feature or fix
2. **Clear commit messages**: Use conventional commit format
3. **Update documentation**: If applicable, update README.md and docs/
4. **Add tests**: Include tests for new functionality

## Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
- `feat(agent): add support for custom agent cards`
- `fix(gateway): handle empty request body`
- `docs(readme): update installation instructions`

## Questions?

- Open an issue for bugs or feature requests
- Join discussions in GitHub Discussions

---

## 中文指南

### 快速开始

1. Fork 本仓库
2. Clone 你的 fork
3. 创建新分支
4. 提交更改
5. 提交 PR

### 开发环境

- Python 3.12+
- Docker 和 Docker Compose

### 代码规范

- 遵循 PEP 8
- 使用类型注解
- 为公共 API 添加文档字符串

### 提交规范

使用约定式提交格式：
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具
