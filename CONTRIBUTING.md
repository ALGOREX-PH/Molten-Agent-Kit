# Contributing to Molten Agents Kit

Thanks for your interest in contributing! Here's how to get started.

## Getting Started

1. Fork the repo on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Molten-Agent-Kit.git
   cd Molten-Agent-Kit
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a branch for your changes:
   ```bash
   git checkout -b feature/my-feature
   ```

## Making Changes

- Keep changes focused — one feature or fix per PR
- Follow the existing code style (Python, 4-space indent)
- Don't modify `agent/moltbook_client.py` unless fixing a bug in the API client itself
- Test your changes with `python run.py once` before submitting

## Submitting a Pull Request

1. Commit your changes with a clear message
2. Push to your fork: `git push origin feature/my-feature`
3. Open a Pull Request against the `main` branch
4. Describe what you changed and why

## Reporting Issues

Open an issue on [GitHub Issues](https://github.com/ALGOREX-PH/Molten-Agent-Kit/issues) with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## Code of Conduct

Be respectful and constructive. We're all here to build cool AI agents.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
