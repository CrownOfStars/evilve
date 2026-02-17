---
name: tavily_web_search
description: Perform intelligent web searches using the Tavily AI Search API via command line.
allowed-tools: bash
---

# Tavily Web Search Protocol

Execute web searches optimized for LLMs using `curl` to interact with the Tavily API.

## Tool Definition

This is the conceptual definition. The Agent uses the `bash` tool to execute the logic.

## API Usage Reference

| Property | Value |
| --- | --- |
| Endpoint | `https://api.tavily.com/search` |
| Method | `POST` |
| Auth | Bearer Token in Header (`Authorization: Bearer <token>`) |
| Environment | Requires `${TAVILY_API_KEY}` to be set |

## Command Template

To execute a search, use the following `curl` pattern in the `bash` tool. Note that authentication is handled via the Header.

```bash
curl -s -X POST [https://api.tavily.com/search](https://api.tavily.com/search) \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer $TAVILY_API_KEY" \
  -d '{
        "query": "the query",
        "search_depth": "basic",
        "include_answer": true,
        "max_results": 5
      }'

```

## Input Schema (Conceptual)

When planning to use this tool, the Agent considers:

```json
{
  "query": "What is the latest version of Python?",
  "search_depth": "basic",
  "include_answer": true
}

```

## Output Schema

The tool outputs a JSON string (from stdout) that must be parsed/read by the Agent:

```json
{
  "query": "...",
  "answer": "...",       // Present if include_answer is true
  "results": [
    {
      "title": "...",
      "url": "...",
      "content": "...",  // The main context snippet
      "score": 0.98
    }
  ],
  "response_time": 0.5
}

```

## Examples

### 1. Basic Fact Check (Fast)

**Input (Bash):**

```bash
curl -s -X POST [https://api.tavily.com/search](https://api.tavily.com/search) \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer $TAVILY_API_KEY" \
  -d '{
        "query": "current NVIDIA stock price",
        "search_depth": "basic",
        "include_answer": true,
        "max_results": 5
      }'

```

**Output (JSON Snippet):**

```json
{
  "answer": "As of the latest market close, NVIDIA (NVDA) stock price is...",
  "results": [...]
}

```

### 2. Deep Research (Comprehensive)

**Input (Bash):**

```bash
curl -s -X POST [https://api.tavily.com/search](https://api.tavily.com/search) \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer $TAVILY_API_KEY" \
  -d '{
    "query": "compare Llama 3 vs GPT-4 architecture details",
    "search_depth": "advanced",
    "include_answer": false,
    "max_results": 7
  }'

```

### 3. Handling API Errors

**Input (Bash):**
*(Invalid Token scenario)*

**Output:**

```json
{"code": 401, "message": "Unauthorized"}

```

## Best Practices for Agents

1. **Prefer POST:** Always use the `POST` method with `-d` (data).
2. **Auth Header:** Ensure the `${TAVILY_API_KEY}` environment variable is set. Do not put the API key in the JSON body.
3. **Use `include_answer`:** For direct questions, set `"include_answer": true`. This allows Tavily to synthesize the answer for you, saving you context window space.
4. **Depth Selection:**
* Use `basic` for simple facts (sports scores, weather, definitions).
* Use `advanced` for broad research. Note: `advanced` takes longer to execute.


5. **Quote Handling:** Be careful with nested quotes in the `curl` command. Ensure the JSON body is valid.

## Limitations

* **Bash Dependency:** Relies on `curl` being installed in the environment.
* **Context Limit:** The JSON response can be large. If it's too long, reduce `max_results` in the request body.
* **Stateless:** Each search is independent.

