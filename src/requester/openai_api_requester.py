import time

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

            if "model" not in params:
                raise ValueError("Missing 'model' key in parameters. Please define it in the code or in the data file.")
            
            response_stream = self.client.chat.completions.create(
                messages=messages,
                stream=True,
                **params
            )

            first_token_time = None
            last_token_time = None

            for chunk in response_stream:

                delta = chunk.choices[0].delta
                if delta:

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
                            
            
            e2e = last_token_time - start_request
            if session_id:
                if full_text:
                    self.memory.add_assistant_message(session_id, full_text)
                if final_tool_calls:
                    self.memory.add_tool_call(session_id, final_tool_calls)

            print("\n\n" ,session_id)
            print(messages)
            print(f"\nE2E: {e2e:.4f}s, TTFT: {ttft:.4f}s, ITL průměr: {sum(itl_list)/len(itl_list) if itl_list else 0:.4f}s")
            return RequestStatistics(e2e, ttft, tuple(itl_list), 1 + len(itl_list))

        else:
            start_request = time.perf_counter()
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
            return RequestStatistics(e2e, None, None, None)
        
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
            
            response_stream = await self.aclient.chat.completions.create(
                messages=messages,
                stream=True,
                **params
            )

            first_token_time = None
            last_token_time = None

            async for chunk in response_stream:

                delta = chunk.choices[0].delta
                if delta:

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
                            
            
            e2e = last_token_time - start_request
            if session_id:
                if full_text:
                    self.memory.add_assistant_message(session_id, full_text)
                if final_tool_calls:
                    self.memory.add_tool_call(session_id, final_tool_calls)

            print("\n\n" ,session_id)
            print(messages)
            print(f"\nE2E: {e2e:.4f}s, TTFT: {ttft:.4f}s, ITL průměr: {sum(itl_list)/len(itl_list) if itl_list else 0:.4f}s")
            return RequestStatistics(e2e, ttft, tuple(itl_list), 1 + len(itl_list))

        else:
            start_request = time.perf_counter()
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
            return RequestStatistics(e2e, None, None, None)