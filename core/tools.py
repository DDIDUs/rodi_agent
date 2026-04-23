import json
import re
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

RODI_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'rodi_data.json')
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')

class RodiTools:
    @staticmethod
    def _read_data() -> List[Dict[str, Any]]:
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
        cat_lower = category.lower()
        
        for item in data:
            item_cat = item.get('category', '').lower()
            item_func = item.get('functional_group', '').lower()
            
            if (cat_lower in item_cat) or (cat_lower in item_func):
                title = item.get('id', 'Unknown')
                if "->" in title:
                    continue

                desc = item.get('description', '').replace('\n', ' ').strip()
                if len(desc) > 300:
                    desc = desc[:297] + "..."
                results.append(f"{title} : {desc}")
                
        return "\n".join(results) if results else f"No APIs found for category: {category}"

    @staticmethod
    def get_information(api_id: str) -> Dict[str, Any]:
        data = RodiTools._read_data()
        api_item = next((item for item in data if item['id'] == api_id), None)
        
        if not api_item:
            return {"error": f"API ID '{api_id}' not found."}
            
        return {
            "id": api_item.get('id'),
            "category": api_item.get('category'),
            "functional_group": api_item.get('functional_group'),
            "description": api_item.get('description'),
            "params": api_item.get('metadata', {}).get('params', [])
        }

    @staticmethod
    def search_rag(query: str) -> Dict[str, Any]:
        import requests
        url = 'http://129.254.222.37:10001/api/search/dense'
        params = {'collection_name': 'rodi_script_api_docs', 'text': query, 'limit': 3}
        headers = {'accept': 'application/json'}
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            result_data = response.json()
            RodiTools._log_rag_query(query, result_data)
            return result_data
        except Exception as e:
            return {"error": f"Failed to fetch RAG data: {str(e)}"}

    @staticmethod
    def _log_rag_query(query: str, result: Dict[str, Any]):
        """Internal helper to log RAG queries."""
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            log_file = os.path.join(LOG_DIR, 'rag_results.json')
            history = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    try: history = json.load(f)
                    except: pass
            
            history.append({
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'result': result
            })
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: RAG logging failed: {e}")

if __name__ == "__main__":
    print("--- Testing get_list ---")
    print(RodiTools.get_list("Motion Control"))
