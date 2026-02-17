---
name: search_result_refinement 
description: Process raw web search results to extract key information, remove noise, deduplicate content, and synthesize a concise answer based on user intent. 
allowed-tools: none
---

# Search Result Refinement Protocol

Execute an internal cognitive process to clean, filter, and summarize raw JSON search results into high-density information.

## Skill Definition

This skill does not invoke external APIs. It represents a logic gate where the Agent acts as a **Information Filter**. It takes raw search output (potentially noisy or redundant) and transforms it into a clean, cited summary strictly relevant to the `user_query`.

## Processing Logic Reference

| Phase | Action |
| --- | --- |
| **1. Intent Alignment** | Compare `raw_results` against `original_query` to determine relevance. |
| **2. Noise Filtering** | Discard results with low information density (SEO spam, login pages, generic homepages). |
| **3. Fact Extraction** | Extract specific entities (dates, prices, versions, definitions) from the `content` snippets. |
| **4. Synthesis** | Merge duplicate information and resolve conflicts between sources. |

## Internal Reasoning Template

When executing this skill, the Agent simulates the following logical flow:

```text
[INPUT]:
  Query: "{user_query}"
  Raw Data: {tavily_results_json}

[PROCESS]:
  1. SCAN: Read all 'content' fields.
  2. FILTER: Ignore sources where score < 0.5 or content is navigation text.
  3. EXTRACT:
     - Found Fact A from Source 1
     - Found Fact B from Source 2
  4. VERIFY: Do Fact A and B contradict? (If yes, note the conflict).
  5. FORMAT: Structure into clear bullet points with [Source ID].

[OUTPUT]:
  Return JSON object with 'summary', 'key_points', and 'sources'.

```

## Input Schema (Conceptual)

The input is the raw output from a previous search tool execution:

```json
{
  "original_query": "What are the release dates for Llama 3 models?",
  "raw_search_results": [
    {
      "title": "Meta AI Releases...",
      "url": "https://...",
      "content": "Llama 3 8B and 70B were released on April 18, 2024...",
      "score": 0.99
    },
    {
      "title": "Cooking Recipes",
      "url": "https://...",
      "content": "Llama is a woolly animal...",
      "score": 0.12
    }
  ]
}

```

## Output Schema

The skill produces a structured JSON strictly for consumption by the calling Agent or the next step in the chain:

```json
{
  "status": "success",
  "refined_summary": "...",   // A coherent paragraph summarizing the findings
  "key_facts": [              // Structured data points
    {
      "fact": "...",
      "source_url": "..."
    }
  ],
  "missing_information": [],  // What was asked but NOT found in the raw data
  "is_sufficient": true       // Boolean: do we need to search again?
}

```

## Examples

### 1. Noise Reduction (Standard)

**Input Context:**
*Query:* "Python 3.12 new features"
*Raw Data:* Contains 5 results, 2 are actual docs, 3 are generic tutorials or ads.

**Output (JSON Snippet):**

```json
{
  "status": "success",
  "refined_summary": "Python 3.12 introduces performance improvements, better error messages, and f-string limitations removal. The GIL is not yet removed but sub-interpreters are improved.",
  "key_facts": [
    {
      "fact": "F-strings are now parsed with the PEG parser, allowing nesting.",
      "source_url": "https://docs.python.org/3/whatsnew/3.12.html"
    },
    {
      "fact": "Performance overhead of tracing/profiling is reduced.",
      "source_url": "https://realpython.com/python312-features"
    }
  ],
  "is_sufficient": true
}

```

### 2. Conflict Resolution (Advanced)

**Input Context:**
*Query:* "Date of Apple Event 2025"
*Raw Data:* Result A says "September 10 (Predicted)", Result B says "September 12 (Rumor)", Result C says "Official Date: Sept 9".

**Output (JSON Snippet):**

```json
{
  "status": "success",
  "refined_summary": "There are conflicting reports regarding the Apple Event 2025. While rumors suggest dates between Sept 10-12, one source claims an official date of Sept 9.",
  "key_facts": [
    {
      "fact": "Official Date claim: September 9",
      "source_url": "https://apple-news-official..."
    },
    {
      "fact": "Rumored dates: September 10 or 12",
      "source_url": "https://macrumors..."
    }
  ],
  "missing_information": ["Official press release verification"],
  "is_sufficient": false
}

```

## Best Practices for Agents

1. **Strict Relevance:** Aggressively discard snippets that do not directly answer the `original_query`. If a snippet is just a "Learn More" link, ignore it.
2. **Source Preservation:** Never detach a fact from its `url`. The final output must allow the user to verify the claim.
3. **Tavily "Answer" Handling:** If the input `raw_search_results` includes a pre-generated `answer` from Tavily, treat it as a high-confidence summary but verify it against the individual `results` snippets.
4. **Formatting:** If the query asks for a list/table, the `refined_summary` should be formatted as Markdown (e.g., specific columns for 'Price', 'Model', 'Specs').
5. **Identify Gaps:** If the raw results do not contain the answer, explicitly state this in `missing_information` rather than hallucinating an answer.

## Limitations

* **Context Only:** This skill can only process the data provided in `raw_search_results`. It cannot fetch new data if the initial search was poor.
* **No Validation:** It assumes the text in `content` is true. It cannot verify facts externally (e.g., by running code).
* **Token Window:** Extremely large raw inputs may need to be chunked before being passed to this skill logic.