import os
import json
import urllib.request
import urllib.error

class LLMClient:
    def generate(self, messages: list, stop_sequences: list = None) -> str:
        raise NotImplementedError

class OpenAILLMClient(LLMClient):
    def __init__(self, config_path: str = "llm_config.json"):
        if not os.path.isabs(config_path):
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_path)
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
        self.api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY") or "EMPTY"
        self.api_url = config.get("api_url", "https://api.openai.com/v1/chat/completions")
        self.model = config.get("model", "gpt-4-turbo")
        self.temperature = config.get("temperature", 0.0)
        self.top_p = config.get("top_p", 1.0)

    def generate(self, messages: list, stop_sequences: list = None) -> str:
        request_url = self.api_url
        if not request_url.endswith("/chat/completions"):
            request_url = request_url.rstrip("/") + "/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        if stop_sequences:
            payload["stop"] = stop_sequences

        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    request_url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers
                )
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    return result["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8', errors='ignore')
                if e.code == 400:
                    try:
                        err_json = json.loads(error_body)
                        param = err_json.get("error", {}).get("param")
                        if param and param in payload:
                            del payload[param]
                            continue
                    except: pass
                raise RuntimeError(f"API Error {e.code}: {error_body}")
            except Exception as e:
                if attempt == 2: raise RuntimeError(f"LLM failed after retries: {e}")
        
        raise RuntimeError("LLM Generation failed.")
