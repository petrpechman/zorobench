import time
import json
import logging

from typing import Any
from openai import APIStatusError
from openai import AsyncOpenAI
from dataclasses import dataclass, field
from .request_statistics import RequestStatistics
from .conversation_memory import ConversationMemory
from .request_timer import RequestTimer
from ..data_utils.async_writer import AsyncFileWriter


@dataclass
class RequestResponse:
    content: str = ""
    tool_calls: dict = field(default_factory=dict)

    def to_serializable(self) -> dict:
        tool_calls = {}
        for k, v in self.tool_calls.items():
            name = v.function.name
            arguments = v.function.arguments
            tool_calls[k] = {"name": name, "arguments": arguments}

        return {
            "content": self.content,
            "tool_calls": tool_calls,
        }


class OpenAIAPIRequester:
    def __init__(
        self,
        stream: bool,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        memory: ConversationMemory | None = None,
        log_responses: bool = False,
    ):
        self.aclient = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        self.model = model
        self.stream = stream
        self.memory = ConversationMemory() if memory is None else memory
        self.async_writer = AsyncFileWriter("responses.jsonl") if log_responses else None

    def _log_error(
        self,
        err: Exception,
        messages: list[dict[str, Any]],
        params: dict[str, Any],
        session_id: str | None,
        start_time: float,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> int | None:
        elapsed = time.perf_counter() - start_time
        payload = {"messages": messages}
        payload.update(params or {})
        try:
            body_str = json.dumps(payload, ensure_ascii=False)
        except Exception:
            # Fallback if messages contain non-serializable objects
            body_str = str(payload)
        rid_part = f", request_id={request_id}" if request_id else ""
        error_message = (
            f"[ERROR] Request failed (status={status_code if status_code is not None else 'unknown'}) in {elapsed:.4f}s; "
            f"session_id={session_id}{rid_part}; error={type(err).__name__}: {err}\n"
            f"Request body: {body_str}"
        )
        logging.error(error_message)
        return status_code

    def _process_chunk(self, chunk, timer: RequestTimer, request_response: RequestResponse):
        delta = chunk.choices[0].delta if chunk.choices else None

        if delta and delta.role is None:
            timer.mark_token()
            if delta.content:
                request_response.content += delta.content
            for tool_call in delta.tool_calls or []:
                index = tool_call.index
                if index not in request_response.tool_calls:
                    request_response.tool_calls[index] = tool_call
                else:
                    if not request_response.tool_calls[index].function.arguments:
                        request_response.tool_calls[index].function.arguments = ""
                    request_response.tool_calls[index].function.arguments += tool_call.function.arguments

    def _process_params(self, params: dict):
        if self.model:
            params["model"] = self.model

        if "model" not in params:
            raise ValueError("Missing 'model' key in parameters. Please define it in the code or in the data file.")

        if self.stream:
            if "stream_options" in params:
                logging.warning("Warning: Provided 'stream_options' will be overwritten.")
            params["stream_options"] = {"include_usage": True}

    async def _asend_stream_request(
        self, messages: list[dict[str, str]], params: dict[str, str], timer: RequestTimer
    ) -> tuple[RequestStatistics, RequestResponse]:
        request_response = RequestResponse()
        completions_tokens = None

        timer.start()
        response_stream = await self.aclient.chat.completions.create(messages=messages, stream=True, **params)
        async for chunk in response_stream:
            self._process_chunk(chunk, timer, request_response)
            if chunk.usage:
                completions_tokens = chunk.usage.completion_tokens

        e2e, ttft, itl_list = timer.finalize()

        if completions_tokens is None:
            raise RuntimeError("Failed to retrieve the number of tokens from the stream.")

        output_tokens = 1 + len(itl_list)

        if completions_tokens != output_tokens:
            logging.warning(
                f"Completion tokens: {completions_tokens} != Output tokens: {output_tokens}\n"
                f"Request response: {request_response}"
            )

        logging.info(
            f"\nE2E: {e2e:.4f}s, TTFT: {ttft:.4f}s, ITL průměr: {sum(itl_list)/len(itl_list) if itl_list else 0:.4f}s"
        )
        return RequestStatistics(e2e, ttft, tuple(itl_list), completions_tokens, 200), request_response

    async def _asend_request(
        self, messages: list[dict[str, str]], params: dict[str, str], timer: RequestTimer
    ) -> tuple[RequestStatistics, RequestResponse]:
        request_response = RequestResponse()
        completions_tokens = None

        timer.start()
        response = await self.aclient.chat.completions.create(messages=messages, stream=False, **params)
        e2e, ttft, itl_list = timer.finalize()

        message = response.choices[0].message if response.choices else None

        if message:
            request_response.content = message.content
            tool_calls = message.tool_calls or []
        for i, tool_call in enumerate(tool_calls):
            request_response.tool_calls[i] = tool_call

        completions_tokens = response.usage.completion_tokens
        if completions_tokens is None:
            raise RuntimeError("Failed to retrieve the number of tokens from the stream.")
        logging.info(f"E2E: {e2e:.4f}s")
        return RequestStatistics(e2e, ttft, itl_list, completions_tokens, 200), request_response

    async def asend_request(
        self,
        messages: list[dict[str, str]],
        session_id: str | None = None,
        params: dict[str, str] = {},
    ) -> RequestStatistics:
        timer = RequestTimer()

        if session_id:
            self.memory.add_messages(session_id, messages)
            messages = self.memory.get_history(session_id)

        self._process_params(params)

        try:
            if self.stream:
                result, request_response = await self._asend_stream_request(messages, params, timer)
            else:
                result, request_response = await self._asend_request(messages, params, timer)

            if session_id:
                if request_response.content:
                    self.memory.add_assistant_message(session_id, request_response.content)
                if request_response.tool_calls:
                    self.memory.add_tool_call(session_id, request_response.tool_calls)

            if self.async_writer:
                await self.async_writer.write(json.dumps(request_response.to_serializable(), ensure_ascii=False))
        except APIStatusError as api_err:
            status_code = self._log_error(
                api_err, messages, params, session_id, timer.start_time, api_err.status_code, api_err.request_id
            )
            e2e = time.perf_counter() - timer.start_time
            result = RequestStatistics(e2e, None, None, None, status_code)

        return result
