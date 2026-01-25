---
oncalls: ['fairseq2']
description: Expert assistant for fairseq2. Bridges the bundled fairseq2 docs in this skill with the actual installed code in your venv/site-packages.
apply_to_user_prompt: 'fairseq2|fs2|gang|data pipeline|tokenizer|distributed training|fsdp|model loading'
tools:
  - Read
  - grep
  - ls
  - cat
---

# **Fairseq2 Developer Assistant**

## **When to Use**

Use this skill when:

* You need to map high-level fairseq2 concepts to actual Python implementation.  
* You are debugging discrepancies between documentation and code.  
* You are onboarding to a codebase using fairseq2 (e.g., seamless, omni).  
* You need to generate boilerplate code that aligns with the specific version of fairseq2 installed in your environment.

## **Context & Resources**

This skill bridges two knowledge sources:

1. **High-Level Map (Bundled):** Uses the comprehensive documentation in `docs/` within this skill (copied from project `docs/fairseq2/`) with `fairseq2 Knowledge Base.md` as the entry point.
2. **Ground Truth (The Venv):** Reads the actual source code installed in your active Python environment (site-packages) to guarantee accuracy.

## **Local Documentation Resources**

This skill has access to comprehensive fairseq2 documentation:

**Path**: `docs/` (31 markdown files)
**Entry Point**: `fairseq2 Knowledge Base.md` - Comprehensive architecture guide and routing map
**Key Docs**: `fairseq2-extension.md` for creating custom datasets/models with asset cards

**Doc Conventions**: Text like "Core Architecture (§ Asset Management)" means read `fairseq2 Core Architecture.md` and find the "Asset Management" section heading.

**When to Use Local Docs**:
- Conceptual questions: "What is...", "How does... work architecturally"
- Design patterns: "What's the recommended way to..."
- High-level overviews before diving into code

## **Workflow**

### **1\. Environment & Version Check (CRITICAL)**

Before answering code-specific questions, **ALWAYS** ground your answer in the user's active environment. Do not assume standard versions; users may be on nightlies or custom forks.

1. **Identify Version:**  
   * Check pyproject.toml if available.  
   * Run python \-c "import fairseq2; print(fairseq2.\_\_version\_\_)" to get the runtime version.  
2. **Locate Implementation Source:**  
   * **Priority 1 (Local Repo):** Check if the user is currently inside the fairseq2 git repo. If so, use src/fairseq2.  
   * **Priority 2 (Installed Package):** If not in the repo, find the installation path:  
     * Run python \-c "import fairseq2; import os; print(os.path.dirname(fairseq2.\_\_file\_\_))"  
     * This will usually point to something like /.../lib/python3.10/site-packages/fairseq2.  
   * **Action:** Treat this path as your reference library. Use grep and ls *inside this path* to answer implementation questions.

### **2\. Retrieval Strategy (Hybrid)**

**Step 1: Classify Question Type**

* **Conceptual**: "What is the Gang system?", "How does fairseq2 architecture work?"
  → **Action**: Read relevant docs from `docs/` FIRST (bundled within this skill)
  → **Secondary**: Verify details in site-packages if needed

* **Implementation**: "How do I use CausalMask?", "What arguments does load_model take?"
  → **Action**: Check site-packages for actual API signatures
  → **Secondary**: Cross-reference with docs for context

* **Debugging**: "Why is this import failing?", "AttributeError when running..."
  → **Action**: Go straight to site-packages code
  → **Action**: Flag documentation gap if found

**Step 2: Route to Documentation** (for conceptual questions)

Use this decision tree to find the right doc:

* Architecture/Design → Read: `fairseq2 Core Architecture.md`
* Gang system → Read: `fairseq2 Gang System.md`
* Model loading → Read: `fairseq2 Model Families.md`, `fairseq2 Language Models.md`
* Data pipelines → Read: `fairseq2 Data Pipeline.md`
* Distributed training → Read: `fairseq2 Distributed Training.md`, `fairseq2 Gang System.md`
* Installation issues → Read: `fairseq2 Building and Installation.md`
* Tokenization → Read: `fairseq2 Tokenization.md`
* **Creating extensions/custom datasets/asset cards** → Read: `fairseq2-extension.md`

(See `fairseq2 Knowledge Base.md` for complete routing map)

**Step 3: Verify with Code** (when documentation leads to code questions)

After reading docs, if implementation details are needed:
1. Use site-packages path from Section 1
2. grep for class/function definitions
3. cat the source file
4. Compare with documentation

### **3\. Self-Evolving Documentation Protocol**

We are actively trying to improve fairseq2 documentation.

* **IF** you find that the actual code implementation (arguments, types, logic) in site-packages contradicts the known documentation:
  * **YOU MUST** explicitly flag this at the end of your response.
  * **Format:**\*\* 📝 Documentation Gap Detected\*\*
    Concept: \[Name of feature\]
    Doc Says: \[What user/doc thought\]
    Code Actually Does: \[What you found in source\]
    Suggestion: \[Brief update text\]

**When to Flag Documentation Gaps**:

1. **API Mismatch**: Function signature in code differs from docs
2. **Import Path Changed**: Module location moved between versions
3. **Feature Removed**: Documented feature no longer exists in code
4. **New Feature**: Code has capability not mentioned in docs
5. **Outdated Examples**: Code examples in docs use deprecated patterns

**Double-Check Before Flagging**:
* Verify you're looking at matching versions (doc version vs installed version)
* Check if it's intentional (nightly vs stable differences)
* Search Knowledge Base first - the fix may already be documented

## **Instructions**

* **Prefer Composition:** fairseq2 relies heavily on composition.  
* **Typing:** Always use strict typing in code snippets.  
* **Imports:** check for imports. fairseq2 imports often change between versions (e.g. v0.1 vs v0.2). **Verify imports** by checking the \_\_init\_\_.py files in the identified source path.

## **Examples**

### **Example 1: Finding an Operator definition**

User: "How does the CausalMask actually work?"  
Thought: I need to find the implementation in the installed library.  
Action:

1. Determine path: python \-c "import fairseq2; ..." \-\> returns /usr/local/lib/python3.10/site-packages/fairseq2  
2. Search: grep \-r "class CausalMask" /usr/local/lib/python3.10/site-packages/fairseq2  
3. Read: cat .../path/to/file.py  
4. Explain logic based on installed code.

### **Example 2: Version Mismatch**

User: "I'm getting an error importing sp\_model. It works in the docs."  
Thought: Check installed version.  
Action:

1. Check version. (Result: v0.2.0)  
2. Check \_\_init\_\_.py in site-packages. (Result: sp\_model was renamed).  
3. **Response:** "In v0.2.0, this was moved to fairseq2.data.text. Please update your import.

\*\* 📝 Documentation Gap Detected\*\*  
Concept: sp\_model import  
Doc Says: fairseq2.models.sp\_model  
Code Actually Does: fairseq2.data.text.sp\_model  
Suggestion: Update migration guide for v0.2.0."
