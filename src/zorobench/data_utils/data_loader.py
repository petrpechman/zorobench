import json
import warnings

from pathlib import Path
from ..threading_utils.session_queue import RequestPayload

class DataLoader:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.data = []
        self._load_file()

    def _load_file(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"File {self.file_path} does not exist.")
        
        found_model = False
        found_stream = False

        with self.file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # skip empty lines
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Error parsing JSON on line: {line}\n{e}")

                if 'model' in entry:
                    found_model = True
                if 'stream' in entry:
                    found_stream = True

                self.data.append(entry)

        if found_model:
            warnings.warn(
                "The file contains the key 'model'. Any defined model may be overwritten.",
                UserWarning
            )
        if found_stream:
            warnings.warn(
                "The file contains the key 'stream'. Stream will be ignored.",
                UserWarning
            )

    def get_data(self) -> list[dict]:
        return self.data
    
    def _convert_data_into_kwargs(self) -> list[RequestPayload]:
        request_payloads = []
        for dato in self.data:
            session_id = dato.pop("session_id")
            messages = dato.pop("messages")
            params = dato
            request_payloads.append(
                RequestPayload(messages, session_id, params)
            )
        return request_payloads
    
    def get_request_payloads(self) -> list[RequestPayload]:
        return self._convert_data_into_kwargs()
