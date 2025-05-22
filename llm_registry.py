# llm_registry.py
# llm_registry.py
class LLMRegistry:
    def __init__(self):
        self.llms = {}

    def register_llm(self, llm_id, api_key):
        self.llms[api_key] = llm_id

    def get_llm_id(self, api_key):
        return self.llms.get(api_key)

    def unregister_llm(self, api_key):
        if api_key in self.llms:
            del self.llms[api_key]
