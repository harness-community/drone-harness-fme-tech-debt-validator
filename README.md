

## Harness Feature Management CI Tech Debt Plugin




**This is now managed in the harness_community github repo**
[FME Tech Debt CI Plugin](https://github.com/harness-community/drone-harness-fme-tech-debt-validator#)









A Harness CI plugin that analyzes code changes for feature flag usage during CI and enforces governance policies to prevent problematic feature flags from being deployed.

## Features

- **Multi-Language Support**: JavaScript/TypeScript, Java, Python, C# with intelligent fallback
- **Tag-Based Validation**: Fails builds when flags have specific "remove" tags
- **Flag Count Limits**: Enforces maximum number of flags per project
- **Stale Flag Detection**: Identifies flags that haven't been modified or received traffic
- **100% Flag Detection**: Special handling for flags at 100% traffic allocation
- **Permanent Flag Exemptions**: Flags tagged as "permanent" skip stale detection
- **Robust Error Handling**: Graceful degradation on network issues or API changes

## Usage

### Drone Plugin Configuration

```yaml
steps:
- name: feature-flag-governance
  image: your-registry/feature-flag-governance
  settings:
    harness_api_token:
      from_secret: harness_token
    harness_account_id: your_account_id
    harness_project_id: your_project_id
    production_environment_name: Production
    max_flags_in_project: 50
    flag_last_modified_threshold: "90d"
    flag_last_traffic_threshold: "30d"
    flag_at_100_percent_last_modified_threshold: "30d"
    flag_at_100_percent_last_traffic_threshold: "7d"
    tag_remove_these_flags: "deprecated,remove"
    tag_permanent_flags: "permanent,keep"
```

### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `PLUGIN_HARNESS_API_TOKEN` | Harness API token | `pat.12345...` |
| `HARNESS_ACCOUNT_ID` | Harness account identifier (automatically set when using Harness CI) | `abc123` |
| `HARNESS_PROJECT_ID` | Harness project identifier (automatically set when using Harness CI) | `myproject` |

### Optional Configuration
These can be configured as 'Settings' in Harness CI pipelines without the `PLUGIN_` prefix

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PLUGIN_PRODUCTION_ENVIRONMENT_NAME` | Production environment name | `Production` | `prod` |
| `PLUGIN_MAX_FLAGS_IN_PROJECT` | Maximum allowed flags | `-1` (disabled) | `50` |
| `PLUGIN_FLAG_LAST_MODIFIED_THRESHOLD` | Stale flag threshold | `-1` (disabled) | `90d` |
| `PLUGIN_FLAG_LAST_TRAFFIC_THRESHOLD` | No traffic threshold | `-1` (disabled) | `30d` |
| `PLUGIN_FLAG_AT_100_PERCENT_LAST_MODIFIED_THRESHOLD` | 100% flag modified threshold | `-1` (disabled) | `30d` |
| `PLUGIN_FLAG_AT_100_PERCENT_LAST_TRAFFIC_THRESHOLD` | 100% flag traffic threshold | `-1` (disabled) | `7d` |
| `PLUGIN_TAG_REMOVE_THESE_FLAGS` | Tags that fail builds | `""` | `deprecated,remove` |
| `PLUGIN_TAG_PERMANENT_FLAGS` | Permanent flag tags | `""` | `permanent,keep` |


### Drone Environment Variables in use
These are automatically included by Harness CI

| Variable | Description | Example |
|----------|-------------|---------|
| `DRONE_COMMIT_BEFORE` | Commit hash of the previous build | `abc123` |
| `DRONE_COMMIT_AFTER` | Commit hash of the current build | `def456` |
| `DRONE_REPO_NAME` | Repository name | `my-repo` |

**Time Format**: Supports flexible durations like `90d`, `30d 12h`, `1w 2d 3h 30m`

## How It Works

The plugin analyzes code changes using language-specific parsing to detect feature flag usage:

### Language Support
- **JavaScript/TypeScript**: Full AST parsing with variable resolution
- **Java**: AST parsing using javalang library
- **Python**: Built-in AST parsing support
- **C#**: Lexical parsing with regex fallback
- **Other files**: Regex pattern matching

### What Gets Detected ✅
```javascript
// String literals in any position
getTreatment("my-flag")
getTreatment(userId, "my-flag", attributes)
getTreatments(["flag1", "flag2", "flag3"])

// Simple variable resolution
const FLAG_NAME = "my-flag";
getTreatment(FLAG_NAME);
```

### What Doesn't Get Detected ❌
```javascript
// Dynamic flag names
getTreatment("prefix_" + userId + "_feature")
getTreatment(`flag_${environment}_${feature}`)

// Cross-file imports or runtime values
getTreatment(flags[Math.random()])
getTreatment(someObject.flagName)
```

### Language-Specific Limitations

**C# Lexical Parsing (vs AST in other languages):**
- ❌ **Complex object property access**: `someObject.flagName`, `config.flags.primary`
- ❌ **Method return values**: `getTreatment(GetFlagName())`
- ❌ **String interpolation**: `$"flag_{environment}_{feature}"`
- ❌ **Advanced LINQ expressions**: `flags.Where(f => f.IsActive).Select(f => f.Name)`
- ❌ **Conditional expressions**: `getTreatment(isDev ? "dev-flag" : "prod-flag")`
- ✅ **Simple variable references**: `string flag = "name"; getTreatment(flag)` ✅ Works
- ✅ **List initialization**: `new List<string> {"flag1", "flag2"}` ✅ Works

**All Languages:**
- ❌ **Cross-file imports**: Variables/constants defined in other files
- ❌ **Database/API values**: Flag names from external sources
- ❌ **Reflection/dynamic evaluation**: Runtime-generated flag names

### Smart Filtering
The plugin extracts all string arguments from method calls, then filters them against your actual Harness flags to eliminate false positives like user IDs.

## Validation Checks

The plugin performs these governance checks on flags found in your code:

### 1. **Removal Tag Check**
- Fails if any flag has tags marked for removal (e.g., "deprecated", "remove")
- Configurable via `PLUGIN_TAG_REMOVE_THESE_FLAGS`

### 2. **Flag Count Limit**
- Enforces maximum number of flags per project
- Prevents flag sprawl and technical debt

### 3. **Stale Flag Detection**
- **Last Modified Check**: Flags not updated in X days
- **Traffic Check**: Flags not receiving traffic in X days
- **100% Flag Checks**: Special thresholds for flags at 100% allocation
- **Consolidated Reporting**: All violations reported together with actionable guidance

### 4. **Permanent Flag Exemptions**
- Flags tagged as "permanent" skip stale detection
- Useful for foundational flags that should persist

## Local Development

```bash
# Set up environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
./run_tests.sh

# Run the plugin locally
export PLUGIN_HARNESS_API_TOKEN="your-token"
export HARNESS_ACCOUNT_ID="your-account"
export HARNESS_PROJECT_ID="your-project"
python app/main.py
```

## Troubleshooting

### Common Issues

1. **Plugin exits with "Configuration Error"**: Check required environment variables
2. **"Failed to fetch flags from Harness"**: Verify API token permissions and network connectivity
3. **"Cannot analyze code changes"**: Ensure container has git history access

### Debug Mode
```bash
export PLUGIN_DEBUG=true
python app/main.py
```

## Testing

```bash
# Run all tests
./run_tests.sh

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## License

This project is available under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0.txt).
