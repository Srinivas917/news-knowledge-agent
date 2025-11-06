from constants.llms import models
import json

def refine_response_with_gemini(user_query: str, full_response: str) -> str:
    """
    Validates and refines the main agent's response using trusted summaries.
    Ensures:
      - Factual alignment with provided summaries only.
      - Logical correlation between user question and answer.
      - No hallucination or speculative rewriting.
      - Keeps only relevant reference links (and preserves valid ones).
      - Graceful fallback if summaries lack relevant info.
    """

    # Load summaries safely
    with open("summary.json", "r") as f:
        summaries = json.load(f)

    # Convert summaries to readable text (in case they're dicts)
    summaries_response = "\n\n".join(
        s["summary"] if isinstance(s, dict) and "summary" in s else str(s)
        for s in summaries
    )

    identity_keywords = [
        "hi","how are you","who are you", "what are you", "your name", "which model", "what model",
        "are you real", "are you human", "what version", "who made you",
        "identity"
    ]
    if any(keyword in user_query.lower() for keyword in identity_keywords):
        return full_response

    prompt = f"""
You are a **Strict and Intelligent Response Validation Agent**.

Your responsibility is to **verify, validate, refine, and reformat** the assistant's response
using only the trusted factual summaries provided below.

---

### User Question:
{user_query}

### Assistant's Original Response:
{full_response}

### Trusted Summaries:
{summaries_response}

---

## 🔍 Validation & Refinement Rules

1. **Factual Alignment**
   - Use *only* information that appears in the trusted summaries.
   - Do **not** add, infer, or speculate beyond what's provided.
   - You may paraphrase, merge, or reorder sentences for clarity.

2. **Relevance & Intent Understanding**
   - Understand the **user's intent** behind the question (informational, comparative, analytical, etc.).
   - Ensure the refined answer **directly and completely addresses** that intent.
   - If multiple summaries mention related aspects, integrate them into a cohesive explanation.

3. **Formatting & Structure**
   - Structure the final output for **clarity and readability**.
   - Use markdown formatting:
     - Headings (`###`) for key sections.
     - Bulleted or numbered lists for supporting details.
     - **Bold** for important terms or statistics.
     - *Italics* for subtle emphasis.
   - Ensure the tone matches the query type (e.g., explanatory for “how/why,” factual for “what/is”).

4. **Depth & Explanation**
   - Be **clear, explanatory, and informative**.
   - Provide sufficient context from the summaries to make the response self-contained.
   - Highlight the **most important key points** clearly (e.g., using bold or subheadings).

5. **Reference Link Preservation**
   - Keep only those links that are directly related to the refined answer.
   - Preserve their markdown format:
     ```
     **Related Articles:**
     - [Title](URL)
     ```
   - Do not fabricate or modify link titles or URLs.
   - Keep at least one link if a valid supporting one exists.

6. **Fallback Condition**
   - If none of the summaries cover the topic (even loosely),
     return exactly:
     **"I currently do not have enough information to answer your question."**

---

### 🎯 Final Output Guidelines
- Provide a **polished, factual, and well-structured** final answer.
- Ensure it matches the **user's intent** and is **easy to understand**.
- Return only the **final validated and refined response** — no reasoning, commentary, or metadata.
"""


    try:
        response = models.groq_llm.invoke(prompt)
        refined_text = getattr(response, "content", str(response)).strip()
        return refined_text or full_response

    except Exception as e:
        print("⚠️ Refinement error:", e)
        return full_response
