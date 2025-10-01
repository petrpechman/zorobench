# ZoroBench

ZoroBench is a tool for asynchronous model evaluation with configurable concurrency.

Current works only for vLLM OpenAI API endpoints.

## Installation

```bash
pip install .
```

### Optional Configuration

If you are using the OpenAI API, you can set your API key and base URL:
```bash
export OPENAI_API_KEY="<TOKEN>"
export OPENAI_BASE_URL="<BASE-URL>"
```

## Usage

To run a model with a specified concurrency (e.g., 3), use:

```bash
zorobench run "<MODEL-NAME>" data/example.jsonl -c 3
```

- MODEL-NAME – the name of the model to test
- data/example.jsonl – path to the input data file
- 3 – the number of concurrent tasks

## Testing

Install dependencies and run pytest with uv:

```bash
uv sync
uv run pytest
```

