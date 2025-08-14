# Git Hooks for OneMinuta

Automated quality gates to ensure code quality and prevent broken commits/pushes.

## Quick Setup

```bash
# Install hooks
./install-hooks.sh

# Test hooks work
git commit -m "test commit" --allow-empty
```

## What the Hooks Do

### 🔒 pre-commit Hook

Runs **before** every `git commit` to catch issues early:

1. **🧪 Quick Tests** - Runs minimal tests (no external APIs)
   - Import validation
   - Session manager tests  
   - Language detection tests
   - CLI integration tests

2. **🐍 Python Syntax Check** - Validates Python syntax in all `.py` files

3. **🖨️ Debug Statement Warning** - Warns about `print()` statements in production code

4. **🔑 Secret Detection** - Blocks commits with hardcoded API keys/tokens

**Runtime**: ~5-10 seconds

### 🚀 pre-push Hook

Runs **before** every `git push` with different rules based on branch:

#### Main/Master Branch (Full Protection)
- **🧪 Comprehensive Tests** - All tests if OpenAI API key available
- **📊 Test Coverage** - Shows coverage report (if pytest-cov installed)
- **📝 Code Quality Checks** - TODO/FIXME comment count
- **🗂️ Uncommitted Changes Warning**

#### Feature Branches (Quick Protection)
- **🧪 Quick Tests Only** - Fast validation for feature development

**Runtime**: 
- Quick tests: ~5-10 seconds
- Full tests: ~30-60 seconds (with OpenAI API)

## Hook Installation

### Automatic Installation
```bash
./install-hooks.sh
```

### Manual Installation
```bash
# Copy hooks
cp .githooks/pre-commit .git/hooks/pre-commit
cp .githooks/pre-push .git/hooks/pre-push

# Make executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

## Bypassing Hooks

⚠️ **Not recommended**, especially for main branch:

```bash
# Bypass pre-commit
git commit --no-verify -m "message"

# Bypass pre-push  
git push --no-verify
```

## Hook Results

### ✅ Success Examples

```bash
$ git commit -m "Add new feature"
🔍 Running pre-commit tests...
✅ All pre-commit checks passed!
[main abc1234] Add new feature
```

```bash
$ git push
🚀 Running pre-push tests...
Pushing to protected branch: main
Running comprehensive tests...
✅ All pre-push checks passed!
```

### ❌ Failure Examples

```bash
$ git commit -m "Broken code"
🔍 Running pre-commit tests...
❌ Pre-commit tests FAILED!
Tests must pass before committing.
```

```bash
$ git commit -m "Add API key"
🔍 Running pre-commit tests...
❌ Found potential hardcoded secrets!
services/example.py:5:    API_KEY = "sk-real-key-here"
```

## Hook Configuration

### Environment Variables

Hooks automatically load from `.env` file:
```env
OPENAI_API_KEY=your_key_here  # Enables full NLP tests
TELEGRAM_API_ID=your_id       # For integration tests  
```

### Customizing Hooks

Edit `.githooks/pre-commit` or `.githooks/pre-push`:

```bash
# Change test categories
python tests/run_all_tests.py --category unit  # Instead of quick

# Add new checks
echo "Running custom validation..."
./my-custom-check.sh
```

Then reinstall:
```bash
./install-hooks.sh
```

## Hook Features

### Smart Test Selection

| Scenario | Tests Run | Reason |
|----------|-----------|---------|
| Feature branch commit | Quick tests | Fast feedback during development |
| Main branch commit | Quick tests | Prevent broken commits |
| Feature branch push | Quick tests | Allow quick feature pushes |
| Main branch push | Full tests | Protect production branch |
| No OpenAI key | Quick tests only | Work without API access |
| With OpenAI key | NLP + all tests | Full validation |

### Security Features

1. **Secret Detection** - Prevents accidental key commits
2. **Syntax Validation** - Catches basic Python errors
3. **Import Validation** - Ensures all modules load correctly
4. **Test Coverage** - Shows which code is tested

### Performance Optimized

- **Quick tests** run in 5-10 seconds
- **Parallel execution** where possible
- **Smart test selection** based on branch/context
- **Cached test results** for repeated runs

## Troubleshooting

### Hook Not Running
```bash
# Check hook exists and is executable
ls -la .git/hooks/pre-commit
ls -la .git/hooks/pre-push

# Reinstall if needed
./install-hooks.sh
```

### Tests Failing in Hook but Not Locally
```bash
# Run tests exactly as hook does
cd $(git rev-parse --show-toplevel)
python tests/run_all_tests.py --category quick
```

### Python Import Errors
```bash
# Check Python path
which python
python --version

# Check project structure
python -c "import sys; print('\n'.join(sys.path))"
```

### API Key Issues
```bash
# Check .env loading
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API key loaded' if os.getenv('OPENAI_API_KEY') else 'No API key')"
```

## Continuous Integration

Use same hooks in CI/CD:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pre-commit checks
        run: .git/hooks/pre-commit
      - name: Run pre-push checks  
        run: .git/hooks/pre-push
```

## Benefits

1. **🔒 Quality Gates** - Prevent broken code from entering repository
2. **⚡ Fast Feedback** - Catch issues before they reach CI/CD
3. **🔑 Security** - Block accidental secret commits
4. **📊 Consistency** - Same checks for all developers
5. **🚀 Confidence** - Know your code works before pushing
6. **🎯 Branch Protection** - Stricter rules for main branch

## Hook Maintenance

### Updating Hooks
```bash
# Modify .githooks/pre-commit or .githooks/pre-push
vim .githooks/pre-commit

# Reinstall to apply changes
./install-hooks.sh
```

### Adding New Tests
```bash
# Add to tests/run_all_tests.py
# Or create new test file in tests/

# Hooks will automatically pick up new tests
```

### Team Guidelines

1. **Never bypass hooks on main branch**
2. **Fix failing tests, don't bypass**
3. **Update hooks when adding new features**
4. **Run `./install-hooks.sh` after pulling hook changes**
5. **Report hook issues to team**