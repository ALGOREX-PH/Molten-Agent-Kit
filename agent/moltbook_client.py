"""
Moltbook API Client
Handles all interactions with the Moltbook API
"""

import requests
from typing import Optional, List, Dict, Any

class MoltbookClient:
    BASE_URL = "https://www.moltbook.com/api/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an API request to Moltbook"""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=data)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    # === Agent Methods ===

    def get_me(self) -> Dict[str, Any]:
        """Get current agent profile"""
        return self._request("GET", "agents/me")

    def get_status(self) -> Dict[str, Any]:
        """Check claim status"""
        return self._request("GET", "agents/status")

    def update_profile(self, description: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Update agent profile"""
        data = {}
        if description:
            data["description"] = description
        if metadata:
            data["metadata"] = metadata
        return self._request("PATCH", "agents/me", data)

    def get_profile(self, name: str) -> Dict[str, Any]:
        """Get another molty's profile"""
        return self._request("GET", f"agents/profile?name={name}")

    # === Feed Methods ===

    def get_feed(self, sort: str = "hot", limit: int = 25) -> Dict[str, Any]:
        """Get personalized feed (subscribed submolts + followed moltys)"""
        return self._request("GET", f"feed?sort={sort}&limit={limit}")

    def get_posts(self, sort: str = "hot", limit: int = 25, submolt: Optional[str] = None) -> Dict[str, Any]:
        """Get posts from all or specific submolt"""
        endpoint = f"posts?sort={sort}&limit={limit}"
        if submolt:
            endpoint += f"&submolt={submolt}"
        return self._request("GET", endpoint)

    def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get a single post"""
        return self._request("GET", f"posts/{post_id}")

    # === Post Methods ===

    def create_post(self, submolt: str, title: str, content: str) -> Dict[str, Any]:
        """Create a new post"""
        return self._request("POST", "posts", {
            "submolt": submolt,
            "title": title,
            "content": content
        })

    def create_link_post(self, submolt: str, title: str, url: str) -> Dict[str, Any]:
        """Create a link post"""
        return self._request("POST", "posts", {
            "submolt": submolt,
            "title": title,
            "url": url
        })

    def delete_post(self, post_id: str) -> Dict[str, Any]:
        """Delete your post"""
        return self._request("DELETE", f"posts/{post_id}")

    # === Comment Methods ===

    def get_comments(self, post_id: str, sort: str = "top") -> Dict[str, Any]:
        """Get comments on a post"""
        return self._request("GET", f"posts/{post_id}/comments?sort={sort}")

    def create_comment(self, post_id: str, content: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Add a comment to a post"""
        data = {"content": content}
        if parent_id:
            data["parent_id"] = parent_id
        return self._request("POST", f"posts/{post_id}/comments", data)

    # === Voting Methods ===

    def upvote_post(self, post_id: str) -> Dict[str, Any]:
        """Upvote a post"""
        return self._request("POST", f"posts/{post_id}/upvote")

    def downvote_post(self, post_id: str) -> Dict[str, Any]:
        """Downvote a post"""
        return self._request("POST", f"posts/{post_id}/downvote")

    def upvote_comment(self, comment_id: str) -> Dict[str, Any]:
        """Upvote a comment"""
        return self._request("POST", f"comments/{comment_id}/upvote")

    # === Follow Methods ===

    def follow(self, molty_name: str) -> Dict[str, Any]:
        """Follow a molty"""
        return self._request("POST", f"agents/{molty_name}/follow")

    def unfollow(self, molty_name: str) -> Dict[str, Any]:
        """Unfollow a molty"""
        return self._request("DELETE", f"agents/{molty_name}/follow")

    # === Submolt Methods ===

    def get_submolts(self) -> Dict[str, Any]:
        """List all submolts"""
        return self._request("GET", "submolts")

    def get_submolt(self, name: str) -> Dict[str, Any]:
        """Get submolt info"""
        return self._request("GET", f"submolts/{name}")

    def subscribe(self, submolt_name: str) -> Dict[str, Any]:
        """Subscribe to a submolt"""
        return self._request("POST", f"submolts/{submolt_name}/subscribe")

    def unsubscribe(self, submolt_name: str) -> Dict[str, Any]:
        """Unsubscribe from a submolt"""
        return self._request("DELETE", f"submolts/{submolt_name}/subscribe")

    # === Search Methods ===

    def search(self, query: str, type: str = "all", limit: int = 20) -> Dict[str, Any]:
        """Semantic search for posts and comments"""
        return self._request("GET", f"search?q={query}&type={type}&limit={limit}")


# === Registration (static method) ===

def register_agent(name: str, description: str) -> Dict[str, Any]:
    """Register a new agent on Moltbook"""
    url = f"https://www.moltbook.com/api/v1/agents/register"
    headers = {"Content-Type": "application/json"}
    data = {"name": name, "description": description}

    try:
        response = requests.post(url, headers=headers, json=data)
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}
