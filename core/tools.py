import json
import re
import os

RODI_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'rodi_data.json')

class RodiTools:
    @staticmethod
    def _read_data():
        """Reads rodi_data.json on demand."""
        try:
            with open(RODI_DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to read rodi_data.json: {e}")

    @staticmethod
    def get_list(category: str) -> str:
        data = RodiTools._read_data()
        results = []
        
        for item in data:
            item_cat = item.get('category', '')
            item_func = item.get('functional_group', '')
            
            # Simple case-insensitive match
            if (category.lower() in item_cat.lower()) or (category.lower() in item_func.lower()):
                title = item.get('id', 'Unknown')
                
                # Filter out "dirty" IDs that are likely documentation artifacts (e.g., "-> move/moveLinear")
                if title.startswith("->") or "->" in title:
                    continue

                desc = item.get('description', '').replace('\n', ' ').strip()
                if len(desc) > 300:
                    desc = desc[:297] + "..."
                results.append(f"{title} : {desc}")
                
        if not results:
            return f"No APIs found for category: {category}"
            
        return "\n".join(results)

    @staticmethod
    def get_information(api_id: str) -> dict:
        data = RodiTools._read_data()
        api_item = next((item for item in data if item['id'] == api_id), None)
        
        if not api_item:
            return {"error": f"API ID '{api_id}' not found."}
            
        content = api_item.get('content', '')
        
        # Simplified Structure for better LLM context
        return {
            "id": api_item.get('id'),
            "category": api_item.get('category'),
            "functional_group": api_item.get('functional_group'),
            "description": api_item.get('description'),
            "params": api_item.get('metadata', {}).get('params', [])
        }

    @staticmethod
    def check_todo(step_description: str) -> str:
        return f"[TODO Checked] Marked step as complete: {step_description}. Please proceed to the next step or output the final code if all steps are done."

    @staticmethod
    def search_rag(query: str) -> dict:
        import requests
        url = 'http://129.254.222.37:10001/api/search/dense'
        params = {
            'collection_name': 'rodi_api',
            'text': query,
            'limit': 3
        }
        headers = {
            'accept': 'application/json'
        }
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to fetch RAG data: {str(e)}"}

if __name__ == "__main__":
    # Test script for development verification
    print("--- Testing get_list ---")
    print(RodiTools.get_list("Motion Control"))
    print("\n--- Testing get_information ---")
    print(json.dumps(RodiTools.get_information("Global.moveLinear"), indent=2))
