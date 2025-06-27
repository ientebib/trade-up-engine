# GitHub Codespaces Setup Guide for Trade-Up Engine

## Overview
This guide explains how to set up your Trade-Up Engine for GitHub's code execution environment without exposing sensitive data or requiring VPN access.

## Understanding the Setup

### What GitHub Code Execution Does
- Creates an isolated Linux container
- Clones your repository
- Runs your setup script
- Allows AI agents to test and modify code safely

### Security Considerations

#### ❌ DON'T DO THIS:
```python
# Never commit real credentials
REDSHIFT_PASSWORD = "my-actual-password"
REDSHIFT_HOST = "production-cluster.redshift.amazonaws.com"
```

#### ✅ DO THIS INSTEAD:
```python
# Use environment variables
REDSHIFT_PASSWORD = os.getenv("REDSHIFT_PASSWORD", "dummy-password")

# Or use mock data mode
if os.getenv("USE_MOCK_DATA", "false") == "true":
    return mock_data_loader.load_mock_data()
```

## Step-by-Step Setup

### 1. Create Test Configuration
```bash
# Create .env.example (this gets committed)
cat > .env.example << 'EOF'
# Redshift Configuration (Test/Mock values)
REDSHIFT_HOST=mock-cluster.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DB=tradeup_test
REDSHIFT_USER=test_user
REDSHIFT_PASSWORD=test_password

# Feature Flags
USE_MOCK_DATA=true
ENVIRONMENT=test
EOF
```

### 2. Modify Your Database Module
Add this to `data/database.py`:

```python
import os
from .mock_data_loader import load_mock_data

def get_all_inventory():
    """Get all inventory - uses mock data in test mode"""
    if os.getenv("USE_MOCK_DATA", "false") == "true":
        logger.info("🧪 Using mock inventory data")
        mock_data = load_mock_data()
        return mock_data['inventory'].to_dict('records')
    
    # Original Redshift code here...
```

### 3. GitHub Secrets (If Using Real Test DB)
If you have a test database without sensitive data:

1. Go to your repo Settings → Secrets → Codespaces
2. Add these secrets:
   - `TEST_REDSHIFT_HOST`
   - `TEST_REDSHIFT_USER`
   - `TEST_REDSHIFT_PASSWORD`

### 4. Setup Script for Codespaces
The setup script (`./run_local.sh setup`) should:
- Install dependencies
- Create .env from .env.example
- Set USE_MOCK_DATA=true
- Initialize test data

## Handling VPN Requirements

### Option 1: Mock Data (Recommended)
- No VPN needed
- Fast and reliable
- Good for testing logic

### Option 2: Public Test Database
- Create a small Redshift cluster
- Load it with anonymized sample data
- Whitelist GitHub's IP ranges

### Option 3: Proxy Solution (Advanced)
```python
# Use a proxy service like ngrok or similar
REDSHIFT_PROXY = os.getenv("REDSHIFT_PROXY_URL")
if REDSHIFT_PROXY:
    # Connect through proxy instead of direct VPN
```

## Sample Mock Implementation

```python
# In data/loader.py
def load_redshift_data():
    if os.getenv("USE_MOCK_DATA") == "true":
        from .mock_data_loader import generate_mock_inventory
        return generate_mock_inventory(num_cars=1000)
    
    # Real Redshift connection...
```

## Testing Your Setup

1. **Local Test**:
   ```bash
   USE_MOCK_DATA=true ./run_local.sh
   ```

2. **Verify Mock Mode**:
   - Check logs for "Using mock data" messages
   - Ensure no real DB connections are attempted

3. **Data Validation**:
   - Mock data should match real data structure
   - All calculations should work the same

## Best Practices

### ✅ DO:
- Use environment variables for all config
- Create realistic mock data
- Test with both mock and real data locally
- Document which features need real data

### ❌ DON'T:
- Commit .env files with real credentials
- Hardcode production endpoints
- Include customer PII in test data
- Assume VPN will work in containers

## Troubleshooting

### "Cannot connect to Redshift"
- Check USE_MOCK_DATA=true is set
- Verify mock data loader is imported

### "Missing test data"
- Ensure mock data generator creates all required fields
- Match the exact structure of real data

### "Tests failing in Codespaces"
- Some tests may expect real DB
- Add test fixtures for mock mode

## Example PR Description
When submitting PRs, mention:
```
This PR includes mock data support for GitHub Codespaces:
- ✅ No real credentials needed
- ✅ Tests run without VPN
- ✅ Mock data matches production structure
```