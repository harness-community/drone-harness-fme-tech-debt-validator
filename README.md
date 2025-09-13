# Feature Flag CI Plugin

A Drone CI plugin that analyzes code changes for feature flag usage and enforces governance policies to prevent problematic feature flags from being deployed.

## Overview

This plugin performs static analysis on git diffs to detect feature flag usage in your code and validates them against your Harness Feature Flags configuration. It helps enforce feature flag governance by failing CI builds when certain conditions are met.

## Features

- **Static Code Analysis**: Scans changed files for feature flag patterns using AST parsing
- **Multi-Language Support**: JavaScript/TypeScript, Java, Python, C# with intelligent fallback
- **Feature Flag Tag Validation**: Fails builds when flags have specific "remove" tags
- **Flag Count Limits**: Enforces maximum number of flags per project
- **Stale Flag Detection**: Identifies flags that haven't been modified or received traffic
- **100% Flag Detection**: Special handling for flags at 100% traffic allocation
- **Production Environment Focus**: Only analyzes flags from production environments
- **Robust Error Handling**: Graceful degradation on network issues or API changes
- **Safe API Access**: Handles Harness API format changes without crashing
- **Harness Integration**: Connects to Harness Feature Flags API for metadata

## Usage

### As a Drone Plugin

```yaml
steps:
- name: fme-feature-flag-techdebt-check
  image: your-registry/fme-feature-flag-techdebt-check
  settings:
    harness_api_token:
      from_secret: harness_token
    harness_account_id: your_account_id
    harness_org_id: your_org_id  
    harness_project_id: your_project_id
    production_environment_name: Production
    max_flags_in_project: 50
    flag_last_modified_threshold: "90d"
    flag_last_traffic_threshold: "30d"
    tag_remove_these_flags: "deprecated,remove"
    tag_permanent_flags: "permanent,keep"
```

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PLUGIN_HARNESS_API_TOKEN` | Harness API token | `none` | `pat.12345...` |
| `HARNESS_ACCOUNT_ID` | Harness account identifier | `none` | `abc123` |
| `HARNESS_ORG_ID` | Harness organization identifier | `none` | `myorg` |
| `HARNESS_PROJECT_ID` | Harness project identifier | `none` | `myproject` |
| `PLUGIN_PRODUCTION_ENVIRONMENT_NAME` | Name of production environment | `Production` | `prod` |
| `PLUGIN_MAX_FLAGS_IN_PROJECT` | Maximum allowed flags | `-1` (disabled) | `50` |
| `PLUGIN_FLAG_LAST_MODIFIED_THRESHOLD` | Age threshold for stale flags | `-1` (disabled) | `90d`, `30d 12h` |
| `PLUGIN_FLAG_LAST_TRAFFIC_THRESHOLD` | Traffic threshold for inactive flags | `-1` (disabled) | `30d`, `7d` |
| `PLUGIN_TAG_REMOVE_THESE_FLAGS` | Comma-separated tags that fail builds | `""` | `deprecated,remove` |
| `PLUGIN_TAG_PERMANENT_FLAGS` | Comma-separated tags for permanent flags | `""` | `permanent,keep` |

**Required Variables**: The following environment variables are **required** and the plugin will fail fast if they are missing:
- `PLUGIN_HARNESS_API_TOKEN` - Valid Harness API token with Feature Flags permissions
- `HARNESS_ACCOUNT_ID` - Your Harness account identifier  
- `HARNESS_PROJECT_ID` - Project identifier where your feature flags are configured
- `DRONE_COMMIT_BEFORE` - Starting commit hash (usually provided by CI)
- `DRONE_COMMIT_AFTER` - Ending commit hash (usually provided by CI)

### Time Duration Format

The plugin supports flexible time duration formats for thresholds:
- `90d` - 90 days
- `30d 12h` - 30 days and 12 hours  
- `1w 2d 3h 30m` - 1 week, 2 days, 3 hours, 30 minutes
- Supported units: `s` (seconds), `m` (minutes), `h` (hours), `d` (days), `w` (weeks)

## Analysis Methods & Limitations

The plugin uses **AST (Abstract Syntax Tree) parsing** with **regex fallback** for robust feature flag detection:

### Language-Specific AST Support
- **JavaScript/TypeScript** (.js/.jsx): Full AST parsing with variable resolution
- **Java** (.java): AST parsing using javalang library
- **Python** (.py): Built-in AST parsing support
- **C#** (.cs): Lexical parsing using pygments with regex fallback
- **Other files**: Regex pattern matching fallback

### What CAN Be Detected ✅

**With AST Parsing (JS/Java/Python/C#):**
- **All string literals in method calls**: Extracts every string argument for safety
  ```javascript
  // Single flag evaluation
  getTreatment("my-flag")                    // ✅ "my-flag"
  getTreatment(userId, "my-flag")            // ✅ "my-flag" 
  getTreatment("my-flag", attributes)        // ✅ "my-flag"
  getTreatmentWithConfig("test-flag", config) // ✅ "test-flag"
  
  // Multiple flag evaluation
  getTreatments(["flag1", "flag2", "flag3"]) // ✅ "flag1", "flag2", "flag3"
  getTreatments(userId, ["flag-a", "flag-b"]) // ✅ "flag-a", "flag-b"
  getTreatmentsWithConfig(["test1", "test2"], config) // ✅ "test1", "test2"
  ```
- **Simple variable resolution**: 
  ```javascript
  const FLAG_NAME = "my-flag";
  const FLAG_LIST = ["flag-a", "flag-b"];
  getTreatment(FLAG_NAME); // ✅ Resolves to "my-flag"
  getTreatment(userId, FLAG_NAME, attrs); // ✅ Also resolves
  getTreatments(FLAG_LIST); // ✅ Resolves to ["flag-a", "flag-b"]
  ```
- **Multiple SDK signatures**: Handles different Split.io SDK calling patterns
- **Variable declarations and usage in same file**
- **Multiple assignment patterns**: `let`, `const`, `var`, `string`, etc.
- **Method call variants**: Object method calls like `client.getTreatment()`, `splitClient.getTreatmentWithConfig()`, `client.getTreatments()`
- **Array/List parsing**: Extracts individual flags from arrays and lists in all supported languages
- **Language-specific syntax**: 
  - **JavaScript**: `['flag1', 'flag2']`
  - **Java**: `Arrays.asList("flag1", "flag2")`
  - **Python**: `['flag1', 'flag2']`
  - **C#**: `new List<string> {"flag1", "flag2"}`

**With Regex Fallback:**
- **All string arguments**: Extracts any string within method calls regardless of position
- **Method variations**: `getTreatment`, `GetTreatment`, `get_treatment`, `getTreatmentWithConfig`, `getTreatments`, `GetTreatments`, `getTreatmentsWithConfig`, `GetTreatmentsAsync`, `GetTreatmentsWithConfigAsync`
- **Array/List patterns**: Detects arrays and lists in multiple languages with flag extraction

### What CANNOT Be Detected ❌
- **Dynamic flag names**: `getTreatment("prefix_" + userId + "_feature")`
- **Template literals**: `getTreatment(\`flag_\${environment}_\${feature}\`)`
- **Cross-file imports**: Variables defined in other files
- **Runtime-determined flags**: Flag names from databases/APIs
- **Complex expressions**: `getTreatment(flags[Math.random()])`
- **Get Treatments by Flag Sets**: `getTreatmentsByFlagSet(["flag_set_name", "flag_set_name2"])`
- **Obfuscated code**: Minified or transformed code

### Detection Methods by File Type

| File Extension | Method | Variable Resolution | Examples |
|----------------|--------|-------------------|----------|
| `.js`, `.jsx` | JavaScript AST | ✅ Yes | `getTreatment("flag")`, `getTreatments(["flag1", "flag2"])` |
| `.java` | Java AST | ✅ Yes | `getTreatment("flag")`, `getTreatments(Arrays.asList("flag1", "flag2"))` |
| `.py` | Python AST | ✅ Yes | `get_treatment("flag")`, `get_treatments(["flag1", "flag2"])` |
| `.cs` | Lexical Parsing | ✅ Yes | `GetTreatment("flag")`, `GetTreatments("key", flagList)` |
| Others | Regex Fallback | ❌ No | `getTreatment("literal-only")`, `getTreatments(["flag1"])` |

### Best Practices for Maximum Detection
1. **Use string literals anywhere in method calls**: Plugin extracts all string arguments safely
2. **Simple variables work great**: `const FLAG = "name"; client.getTreatment(userId, FLAG)`
3. **Keep variable assignments in same file** as usage for resolution
4. **Any argument position works**: `getTreatment("flag")`, `getTreatment(user, "flag")`, `getTreatment("flag", attrs)`
5. **Use standard method names**: `getTreatment`, `getTreatmentWithConfig`, `getTreatments`, `getTreatmentsWithConfig`, `GetTreatmentsAsync`
6. **Array/List literals work**: `getTreatments(["flag1", "flag2"])`, `new List<string> {"flag1", "flag2"}`
7. **Avoid dynamic construction** for static flags

### Smart Filtering
The plugin extracts **all string arguments** from method calls, then cross-references them against your actual Harness flag list. This means:
- ✅ **False positives filtered out**: User IDs and other strings are ignored
- ✅ **Position-independent**: Works with any Split.io SDK signature
- ✅ **Future-proof**: Handles new SDK patterns automatically

### How Smart Filtering Works

```javascript
// Single flag example:
client.getTreatment("user123", "my-feature-flag", { attr: "value" });

// Multiple flags example:
client.getTreatments("user123", ["feature-a", "feature-b", "unrelated-string"]);

// Step 1: Plugin extracts ALL strings from both calls
["user123", "my-feature-flag", "value", "feature-a", "feature-b", "unrelated-string"]

// Step 2: Cross-reference with Harness flags  
// Only "my-feature-flag", "feature-a", "feature-b" exist in your Harness project

// Step 3: Result
["my-feature-flag", "feature-a", "feature-b"] ✅ Correctly identified!
```

This approach is **much safer** than trying to guess argument positions across different SDK versions.

### AST vs Regex Comparison

**AST Parsing Advantages:**
- Resolves simple variable assignments
- Language-aware syntax understanding
- Better accuracy for supported languages
- Extracts all string arguments safely

**Regex Fallback Benefits:**
- Works with any file type
- Simple and fast
- No language-specific dependencies
- Also extracts all string arguments

## Build and Deploy

### Docker Build
```bash
docker build -t feature-flag-ci-plugin .
```

### Local Testing
```bash
# Set up environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DRONE_COMMIT_BEFORE="HEAD~1"
export DRONE_COMMIT_AFTER="HEAD"
export PLUGIN_HARNESS_API_TOKEN="your-token"
export HARNESS_ACCOUNT_ID="your-account"
export HARNESS_PROJECT_ID="your-project"
# ... other vars

# Run the plugin
python app/main.py
```

## Validation Checks

The plugin performs the following governance checks:

### 1. **Removal Tag Check**
- Fails if any flag in code has tags marked for removal
- Configurable via `PLUGIN_TAG_REMOVE_THESE_FLAGS`
- Example: Flags tagged with "deprecated" or "remove"

### 2. **Flag Count Limit**
- Enforces maximum number of flags per project
- Prevents flag sprawl and technical debt
- Configurable via `PLUGIN_MAX_FLAGS_IN_PROJECT`

### 3. **Stale Flag Detection**
- **Last Modified Check**: Flags not updated in X days
- **Traffic Check**: Flags not receiving traffic in X days  
- **100% Flag Checks**: Special handling for flags at 100% allocation
- Configurable thresholds via duration format

### 4. **Permanent Flag Exemptions**
- Flags tagged as "permanent" skip stale detection
- Useful for foundational flags that should persist
- Configurable via `PLUGIN_TAG_PERMANENT_FLAGS`

## Exit Codes

- `0`: All checks passed successfully
- `1`: One or more checks failed (fails the CI build)
- `1`: Configuration error or missing required environment variables
- `1`: Failed to connect to Harness API or fetch flag data

**Fail-Fast Behavior**: The plugin will exit immediately with code `1` if:
- Required environment variables are missing or invalid
- Cannot connect to Harness API 
- Cannot fetch flag data from Harness
- Cannot analyze code changes (git operations fail)

This ensures that CI builds fail early with clear error messages rather than proceeding with incomplete data that could lead to false results.

## Error Handling & Reliability

The plugin is designed for production CI environments with robust error handling:

### Network & API Resilience
- **30-second timeouts** prevent hanging on slow networks
- **Fail-fast behavior** when Harness API is unavailable (prevents false results)
- **Harness Code Repository API** integration for git diff operations in CI environments
- **GitPython fallback** for local development when Harness API is unavailable
- **Safe API access** handles response format changes without crashing
- **Comprehensive logging** for debugging connection issues

### Data Validation
- **Response structure validation** catches API format changes
- **Safe attribute access** prevents crashes on missing fields
- **Project existence verification** with clear error messages
- **Environment validation** warns when production environment not found

### Fallback Behavior
- **AST parsing with regex fallback** ensures flag detection works
- **GitPython → subprocess fallback** for git operations when libraries unavailable
- **API-first with graceful fallback** for code change detection
- **Fail-fast on critical failures** to prevent misleading results
- **Clear error messages** help diagnose configuration issues

## Troubleshooting

### Common Issues

1. **Plugin exits immediately with "Configuration Error"**: 
   - Check that all required environment variables are set correctly
   - Verify `PLUGIN_HARNESS_API_TOKEN` instead of `HARNESS_API_TOKEN`
   - Ensure `DRONE_COMMIT_BEFORE` and `DRONE_COMMIT_AFTER` are provided by CI

2. **"Failed to fetch flags from Harness"**: 
   - Check network connectivity to Harness API
   - Verify API token has correct permissions for Feature Flags
   - Confirm account/org/project IDs are correct

3. **"Cannot analyze code changes"**:
   - Ensure container has access to git history
   - Check that commit hashes are valid
   - Verify `DRONE_REPO_NAME` is set for Harness Code Repository API

4. **Authentication errors**: Verify API token has correct permissions
5. **Project not found**: Confirm account/org/project IDs are correct  
6. **File encoding errors**: Some files may not be readable as UTF-8
7. **Missing production environment**: Check environment name matches exactly

### Debug Mode

Set `PYTHONPATH` and run with debug logging:
```bash
export PYTHONPATH=/app
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python app/main.py
```

## Testing

The project includes a comprehensive test suite with multiple categories of tests.

### Quick Start

```bash
# Run all tests
./run_tests.sh

# Or manually:
pip install -r requirements-test.txt
pytest tests/
```

### Test Categories

- **Unit Tests** (`pytest -m "unit"`): Test individual functions in isolation
- **Integration Tests** (`pytest -m "integration"`): Test component interactions  
- **AST Tests** (`pytest -m "ast"`): Focused AST parsing functionality tests
- **Slow Tests** (`pytest -m "slow"`): Longer-running tests

### Coverage

```bash
# Run with coverage report
pytest tests/ --cov=app --cov-report=html --cov-report=term

# View detailed coverage
open htmlcov/index.html
```

### Test Structure

```
tests/
├── test_ast_parsing.py      # AST parsing functionality
├── test_ci_runner.py        # CI runner integration  
├── test_error_handling.py   # Error handling scenarios
└── conftest.py              # Shared fixtures
```

For detailed testing information, see [TESTING.md](TESTING.md).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `./run_tests.sh`
6. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).
