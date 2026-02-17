---
name: python_sandbox_exec
description: Execute Python code in a secure local Docker container. 
allowed-tools: python.sandbox_exec
---

# Python Sandbox Executor

Execute Python code in a secure, isolated local Docker environment.

## Tool Definition

```python
def sandbox_exec(code: str, timeout: int = 30) -> str:
    """
    Execute Python code in a secure Docker sandbox.
    
    Args:
        code: The Python code snippet to execute.
        timeout: Execution timeout in seconds (default: 30).
        
    Returns:
        JSON string containing {status, exit_code, stdout, stderr}.
    """

```

## Environment Details

| Property | Value |
| --- | --- |
| Runtime | Python 3.11 (Slim) |
| Isolation | Docker Container (`agent_sandbox`) |
| Memory/CPU | Limited by Host Docker Config |
| Working Dir | `/workspace` (Mounted to host's `agent_data`) |
| Timeout | 30 seconds (default) |

## Pre-installed Libraries

The Docker image (`python:3.11-slim` base) includes the following heavy-lifting libraries:

### Data & Science

* `numpy` - Numerical computing
* `pandas` - Data manipulation and analysis
* `scikit-learn` - Machine learning algorithms

### Visualization

* `matplotlib` - Static plotting (Use `plt.savefig`)
* `seaborn` - Statistical data visualization

### Web & Text (If Network Enabled)

* `requests` - HTTP library
* `beautifulsoup4` - HTML parsing

*Note: Standard Python libraries (`json`, `os`, `math`, `datetime`, etc.) are always available.*

## Input Schema

When invoking the tool, the LLM provides:

```json
{
  "code": "import numpy as np\nprint(np.random.rand(5))",
  "timeout": 30
}

```

## Output Schema

The tool returns a JSON string that must be parsed:

```json
{
  "status": "success",     // "success", "failed", "timeout", "error"
  "exit_code": 0,          // 0 for success, non-zero for errors
  "stdout": "...",         // Standard output (truncated if too long)
  "stderr": "..."          // Standard error (tracebacks)
}

```

## Examples

### 1. Basic Calculation

**Input:**

```python
code = """
import math
print(f"Pi is approximately {math.pi:.4f}")
"""

```

**Output:**

```json
{"status": "success", "exit_code": 0, "stdout": "Pi is approximately 3.1416\n", "stderr": ""}

```

### 2. Data Analysis & File Saving

**Input:**

```python
code = """
import pandas as pd
import numpy as np

# Generate Data
df = pd.DataFrame(np.random.randint(0, 100, size=(10, 4)), columns=list('ABCD'))

# Analysis
summary = df.describe()
print(summary)

# Save to workspace (Persisted to Host)
df.to_csv('/workspace/data_analysis.csv')
print("File saved to /workspace/data_analysis.csv")
"""

```

### 3. Handling Errors

**Input:**

```python
code = "print(1/0)"

```

**Output:**

```json
{
  "status": "failed",
  "exit_code": 1,
  "stdout": "",
  "stderr": "Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nZeroDivisionError: division by zero\n"
}

```

## Best Practices for Agents

1. **Output Handling:** Always check `exit_code`. If non-zero, read `stderr` to understand why the code failed and attempt to fix it.
2. **File I/O:**
* Do **NOT** rely on `plt.show()` or GUI windows.
* Always save files (images, csv) to `/workspace/`.
* Files saved to `/workspace/` are accessible on the host machine.


3. **Security:**
* The environment is ephemeral regarding variables (variables do not persist between tool calls).
* Each call is a fresh execution context (unless a stateful server is implemented inside).


4. **Formatting:**
* Use `print()` to output results you want the Agent to read.
* The output buffer is limited (default 4000 chars). For large data, save to a file instead of printing.



## Limitations

* **No Persistence:** Variables defined in one `sandbox_exec` call are NOT available in the next call. Logic must be self-contained or load data from files.
* **No Input:** The script cannot wait for user input (`input()`).
* **Truncation:** stdout/stderr are truncated if they exceed the configured limit.

```

```