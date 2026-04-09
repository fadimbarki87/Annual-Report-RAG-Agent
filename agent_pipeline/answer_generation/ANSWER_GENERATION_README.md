# Answer Generation

This folder contains the grounded answer-generation layer for the annual-report RAG agent.

It is separate from `agent_pipeline/retrieval` on purpose:

- `retrieval` finds candidate evidence chunks
- `answer_generation` uses those chunks to write a grounded answer

This layer does not implement PII redaction, voice input, a web API, or a UI.

## Flow

```text
answer_question.py
-> answer_generator.py
-> retrieval_service.py
-> Azure OpenAI query embedding
-> Qdrant Cloud retrieval
-> context_builder.py
-> Azure OpenAI chat completion
-> grounded answer with resources and exact evidence
```

## Files

| File | Responsibility |
| --- | --- |
| `answer_question.py` | CLI entry point for asking one question. |
| `answer_generator.py` | Main orchestration: scope guard, retrieval, context building, and chat generation. |
| `azure_chat_client.py` | Calls Azure OpenAI chat completions. |
| `context_builder.py` | Formats retrieved chunks into model-readable evidence context. |
| `scope_guard.py` | Uses an AI scope classifier for unsupported questions and stores refusal strings. |
| `settings.py` | Loads answer-generation config and reuses Azure endpoint/API key when possible. |
| `answer_generation_config.template.json` | Safe template for chat model configuration. |
| `ANSWER_GENERATION_README.md` | Explains this layer. |

## Configuration

Create a local config file:

```powershell
Copy-Item .\agent_pipeline\answer_generation\answer_generation_config.template.json .\agent_pipeline\answer_generation\answer_generation_config.json
```

Then edit:

```text
agent_pipeline/answer_generation/answer_generation_config.json
```

Set:

- `chat_deployment`: your Azure OpenAI chat deployment name, for example a GPT-4o deployment
- `endpoint`: optional; if empty, the code reuses the endpoint from `ingestion_pipeline/embeeding/azure_openai_config.json`
- `api_key`: optional; if empty, the code reuses the API key from `ingestion_pipeline/embeeding/azure_openai_config.json`

The local `answer_generation_config.json` file is ignored by Git.

## Run Example

From the project root:

```powershell
python .\agent_pipeline\answer_generation\answer_question.py "What were BMW Group revenues in 2024?" --company bmw
```

```powershell
python .\agent_pipeline\answer_generation\answer_question.py "What does Volkswagen expect for 2025?" --company volkswagen
```

```powershell
python .\agent_pipeline\answer_generation\answer_question.py "What was Bosch liquidity at the end of the year in the cash flow statement?" --company bosch --chunk-type table
```

## Refusal Behavior

For out-of-scope questions, the code first runs a small AI scope-classification step. If the question is outside the annual-report scope, the code returns:

```text
Unsupported: This question is outside the scope of the 2024 annual reports.
```

If retrieval does not produce strong evidence, the code returns:

```text
No strong answer found in the provided documents.
```

If the model determines that evidence is insufficient for a computation, it is instructed to return:

```text
I do not find sufficient data in the documents to compute this.
```

## Important Limit

This layer can cite:

- company
- source PDF
- page number
- chunk ID
- section titles
- table metadata when available
- exact evidence text

It does not yet cite exact PDF coordinates or bounding boxes inside a page.
