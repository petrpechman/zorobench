import time
import sys
import json
from typing import Any
from openai import APIStatusError

from openai import OpenAI, AsyncOpenAI
from .request_statistics import RequestStatistics
from .conversation_memory import ConversationMemory

class OpenAIAPIRequester:
    def __init__(
            self, 
            stream: bool,
            model: str | None = None, 
            api_key: str | None = None,
            base_url: str | None = None,
            memory: ConversationMemory | None = None,
        ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        self.aclient = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        self.model = model
        self.stream = stream
        self.memory = ConversationMemory() if memory is None else memory

    def _log_error(self, err: Exception, messages: list[dict[str, Any]], params: dict[str, Any], session_id: str | None, start_time: float, status_code: int | None = None, request_id: str | None = None) -> int | None:
        elapsed = time.perf_counter() - start_time
        payload = {"messages": messages}
        payload.update(params or {})
        try:
            body_str = json.dumps(payload, ensure_ascii=False)
        except Exception:
            # Fallback if messages contain non-serializable objects
            body_str = str(payload)
        rid_part = f", request_id={request_id}" if request_id else ""
        print(
            f"[ERROR] Request failed (status={status_code if status_code is not None else 'unknown'}) in {elapsed:.4f}s; "
            f"session_id={session_id}{rid_part}; error={type(err).__name__}: {err}\n"
            f"Request body: {body_str}",
            file=sys.stderr,
        )
        return status_code

    def send_request(
            self,
            messages: list[dict[str, str]],
            session_id: str | None = None,
            params: dict[str, str] = {},
        ) -> RequestStatistics:
        full_text = ""
        final_tool_calls = {}
        itl_list: list[float] = []

        if session_id:
            self.memory.add_messages(session_id, messages)
            messages = self.memory.get_history(session_id)

        if self.stream:
            start_request = time.perf_counter()
            if self.model:
                params["model"] = self.model

            if "stream_options" in params:
                print("Warning: Provided 'stream_options' will be overwritten.")
            params["stream_options"] = {"include_usage": True}

            if "model" not in params:
                raise ValueError("Missing 'model' key in parameters. Please define it in the code or in the data file.")
            try:
                response_stream = self.client.chat.completions.create(
                    messages=messages,
                    stream=True,
                    **params
                )

                first_token_time = None
                last_token_time = None
                completions_tokens = None

                for chunk in response_stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.role is None:
                        now = time.perf_counter()
                        if first_token_time is None:
                            first_token_time = now
                            ttft = first_token_time - start_request  # TTFT
                            last_token_time = first_token_time
                        else:
                            itl_list.append(now - last_token_time)  # ITL
                            last_token_time = now

                        if delta.content:
                            full_text += delta.content

                        for tool_call in delta.tool_calls or []:
                            index = tool_call.index
                            if index not in final_tool_calls:
                                final_tool_calls[index] = tool_call
                            else:
                                if not final_tool_calls[index].function.arguments:
                                    final_tool_calls[index].function.arguments = ""
                                final_tool_calls[index].function.arguments += tool_call.function.arguments

                    if chunk.usage:
                        completions_tokens = chunk.usage.completion_tokens

                output_tokens = 1 + len(itl_list)
                e2e = (last_token_time or time.perf_counter()) - start_request

                if completions_tokens is not None and completions_tokens != output_tokens:
                    print("Completion tokens: ", completions_tokens)
                    print("Output tokens: ", output_tokens)

                if session_id:
                    if full_text:
                        self.memory.add_assistant_message(session_id, full_text)
                    if final_tool_calls:
                        self.memory.add_tool_call(session_id, final_tool_calls)

                print("\n\n", session_id)
                print(messages)
                print(f"\nE2E: {e2e:.4f}s, TTFT: {ttft:.4f}s, ITL průměr: {sum(itl_list)/len(itl_list) if itl_list else 0:.4f}s")
                return RequestStatistics(e2e, ttft, tuple(itl_list), output_tokens, 200)
            except APIStatusError as api_err:
                status_code = self._log_error(api_err, messages, params, session_id, start_request, api_err.status_code, api_err.request_id)
                e2e = time.perf_counter() - start_request
                return RequestStatistics(e2e, None, None, None, status_code)

        else:
            start_request = time.perf_counter()
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **params
                )
                full_text = response.choices[0].message.content
                end_request = time.perf_counter()
                e2e = end_request - start_request

                if session_id:
                    self.memory.add_assistant_message(session_id, full_text)
                print(f"E2E: {e2e:.4f}s")
                return RequestStatistics(e2e, None, None, None, 200)
            except APIStatusError as api_err:
                status_code = self._log_error(api_err, messages, {"model": self.model, **(params or {})}, session_id, start_request, api_err.status_code, api_err.request_id)
                e2e = time.perf_counter() - start_request
                return RequestStatistics(e2e, None, None, None, status_code)
        
    async def asend_request(
            self,
            messages: list[dict[str, str]],
            session_id: str | None = None,
            params: dict[str, str] = {},
        ) -> RequestStatistics:
        full_text = ""
        final_tool_calls = {}
        itl_list: list[float] = []

        if session_id:
            self.memory.add_messages(session_id, messages)
            messages = self.memory.get_history(session_id)

        if self.stream:
            start_request = time.perf_counter()
            if self.model:
                params["model"] = self.model

            if "model" not in params:
                raise ValueError("Missing 'model' key in parameters. Please define it in the code or in the data file.")

            if "stream_options" in params:
                print("Warning: Provided 'stream_options' will be overwritten.")
            params["stream_options"] = {"include_usage": True}
            try:
                response_stream = await self.aclient.chat.completions.create(
                    messages=messages,
                    stream=True,
                    **params
                )

                first_token_time = None
                last_token_time = None
                completions_tokens = None

                async for chunk in response_stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.role is None:
                        now = time.perf_counter()
                        if first_token_time is None:
                            first_token_time = now
                            ttft = first_token_time - start_request  # TTFT
                            last_token_time = first_token_time
                        else:
                            itl_list.append(now - last_token_time)  # ITL
                            last_token_time = now

                        if delta.content:
                            full_text += delta.content

                        for tool_call in delta.tool_calls or []:
                            index = tool_call.index
                            if index not in final_tool_calls:
                                final_tool_calls[index] = tool_call
                            else:
                                if not final_tool_calls[index].function.arguments:
                                    final_tool_calls[index].function.arguments = ""
                                final_tool_calls[index].function.arguments += tool_call.function.arguments

                    if chunk.usage:
                        completions_tokens = chunk.usage.completion_tokens
                            
                output_tokens = 1 + len(itl_list)
                e2e = (last_token_time or time.perf_counter()) - start_request

                if completions_tokens is not None and completions_tokens != output_tokens:
                    print("WARNING:")
                    print("Completion tokens: ", completions_tokens)
                    print("Output tokens: ", output_tokens)

                if session_id:
                    if full_text:
                        self.memory.add_assistant_message(session_id, full_text)
                    if final_tool_calls:
                        self.memory.add_tool_call(session_id, final_tool_calls)

                print("\n\n", session_id)
                print(messages)
                print(f"\nE2E: {e2e:.4f}s, TTFT: {ttft:.4f}s, ITL průměr: {sum(itl_list)/len(itl_list) if itl_list else 0:.4f}s")
                return RequestStatistics(e2e, ttft, tuple(itl_list), output_tokens, 200)
            except APIStatusError as api_err:
                status_code = self._log_error(api_err, messages, params, session_id, start_request, api_err.status_code, api_err.request_id)
                e2e = time.perf_counter() - start_request
                return RequestStatistics(e2e, None, None, None, status_code)

        else:
            start_request = time.perf_counter()
            try:
                response = await self.aclient.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **params
                )
                full_text = response.choices[0].message.content
                end_request = time.perf_counter()
                e2e = end_request - start_request

                if session_id:
                    self.memory.add_assistant_message(session_id, full_text)
                print(f"E2E: {e2e:.4f}s")
                return RequestStatistics(e2e, None, None, None, 200)
            except APIStatusError as api_err:
                status_code = self._log_error(api_err, messages, {"model": self.model, **(params or {})}, session_id, start_request, api_err.status_code, api_err.request_id)
                e2e = time.perf_counter() - start_request
                return RequestStatistics(e2e, None, None, None, status_code)
