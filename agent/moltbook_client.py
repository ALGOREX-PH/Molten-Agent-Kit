"""
Moltbook API Client
Handles all interactions with the Moltbook API, including AI verification challenges.
"""

import os
import json
import time
import logging
import requests
from typing import Optional, List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("moltbook")


# === Verification Challenge Solver ===

class VerificationSolver:
    """Solves Moltbook AI verification challenges (lobster-themed obfuscated math)."""

    SOLVER_PROMPT = (
        "You are solving an obfuscated math word problem from Moltbook (a lobster-themed site).\n\n"
        "The text is deliberately garbled with:\n"
        "- aLtErNaTiNg CaPs and doubled letters (e.g. 'tWeNnTtYy' = twenty)\n"
        "- Random symbols scattered throughout: [ ] ^ / - ~ | < >\n"
        "- Filler words like 'um', 'ummm', gibberish like 'lxobqstwer'\n"
        "- Numbers spelled as words (e.g. 'fIfTeEn' = fifteen = 15)\n\n"
        "INSTRUCTIONS:\n"
        "1. First, mentally strip ALL symbols and normalize to lowercase\n"
        "2. Write out the cleaned sentence\n"
        "3. Identify the two numbers and the operation (add/subtract/multiply/divide)\n"
        "4. Compute carefully\n"
        "5. On the LAST line, write ONLY the numeric answer with exactly 2 decimal places\n\n"
        "Example:\n"
        "Input: 'A] lOb^StEr hAs tWeN[tYy eI/gHt LeGs aNd^ lOsEs tH-iRtEeN'\n"
        "Cleaned: 'a lobster has twenty eight legs and loses thirteen'\n"
        "Numbers: 28, 13. Operation: loses = subtract. 28 - 13 = 15\n"
        "15.00"
    )

    def __init__(self, openai_api_key: str = None):
        self._api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        self._client = None
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3
        self._backoff_until = 0

    @property
    def client(self):
        """Lazy-initialize the OpenAI client."""
        if self._client is None and self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                logger.error("VERIFICATION: openai package not installed")
        return self._client

    def is_backed_off(self) -> bool:
        """Check if we are in a backoff period after repeated failures."""
        if self._consecutive_failures >= self._max_consecutive_failures:
            if time.time() < self._backoff_until:
                return True
            self._consecutive_failures = 0
        return False

    def solve_challenge(self, challenge_text: str) -> Optional[str]:
        """Use GPT-4o-mini to solve the obfuscated challenge text.

        Returns:
            The answer string (just a number), or None if solving failed.
        """
        if not self.client:
            logger.error("VERIFICATION: No OpenAI client available to solve challenge")
            return None

        if self.is_backed_off():
            logger.warning(
                "VERIFICATION: In backoff period after %d consecutive failures. Skipping.",
                self._consecutive_failures
            )
            return None

        try:
            logger.info("VERIFICATION: Solving challenge: %s", challenge_text[:120])
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.SOLVER_PROMPT},
                    {"role": "user", "content": challenge_text}
                ],
                max_tokens=200,
                temperature=0
            )
            raw_answer = response.choices[0].message.content.strip()
            logger.info("VERIFICATION: Raw solver output: %s", raw_answer)
            # The answer is the last number in the response (chain-of-thought puts it last)
            # Extract all numbers (including negatives and decimals) from the response
            import re
            numbers = re.findall(r'-?\d+\.?\d*', raw_answer)
            if numbers:
                # Use the last number found (the final answer after chain-of-thought)
                answer = f"{float(numbers[-1]):.2f}"
            else:
                logger.error("VERIFICATION: Could not parse any number from: %s", raw_answer)
                return None
            logger.info("VERIFICATION: Solved -> answer: %s (from %d numbers found)", answer, len(numbers))
            return answer
        except Exception as e:
            logger.error("VERIFICATION: Failed to solve challenge: %s", e)
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_consecutive_failures:
                self._backoff_until = time.time() + 600
                logger.warning(
                    "VERIFICATION: %d consecutive failures, backing off 10 minutes",
                    self._consecutive_failures
                )
            return None

    def record_success(self):
        self._consecutive_failures = 0
        self._backoff_until = 0

    def record_failure(self):
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._max_consecutive_failures:
            self._backoff_until = time.time() + 600
            logger.warning(
                "VERIFICATION: %d consecutive failures, entering 10-minute backoff",
                self._consecutive_failures
            )


# === Moltbook API Client ===

class MoltbookClient:
    BASE_URL = "https://www.moltbook.com/api/v1"

    def __init__(self, api_key: str, openai_api_key: str = None):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self._solver = VerificationSolver(openai_api_key)
        self._verification_stats = {
            "challenges_received": 0,
            "challenges_solved": 0,
            "challenges_failed": 0,
        }

    # === Core Request Methods ===

    def _raw_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a raw API request to Moltbook (no verification handling)."""
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

            # Dump full response for post-creation debugging
            result = response.json()
            if endpoint == "posts" and method == "POST":
                logger.warning(
                    "FULL POST RESPONSE (status=%d): %s",
                    response.status_code, json.dumps(result, default=str)
                )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an API request to Moltbook, automatically handling verification challenges."""
        result = self._raw_request(method, endpoint, data)

        # Log full response for debugging post-creation issues
        logger.debug("RAW RESPONSE %s %s: %s", method, endpoint, json.dumps(result, default=str)[:1000])

        # Detect suspension/ban early — don't try verification on a suspended account
        if isinstance(result, dict):
            status_code = result.get("statusCode")
            message = str(result.get("message", "")).lower()
            error_msg = str(result.get("error", "")).lower()
            combined = message + " " + error_msg
            if status_code == 403 and ("suspended" in combined or "banned" in combined):
                logger.critical(
                    "ACCOUNT SUSPENDED/BANNED: %s | stats: %s",
                    result.get("message"), json.dumps(self._verification_stats)
                )
                return result

        # Check for verification challenge (API may return success:true WITH a hidden challenge)
        if self._has_verification_challenge(result):
            logger.warning(
                "VERIFICATION CHALLENGE DETECTED in response to %s %s (success=%s)",
                method, endpoint, result.get("success")
            )
            result = self._handle_verification(result, method, endpoint, data)

        return result

    # === Verification Challenge Handling ===

    def _has_verification_challenge(self, response_data: dict) -> bool:
        """Check if the API response contains a verification challenge (root or nested)."""
        return self._extract_verification(response_data) is not None

    def _extract_verification(self, response_data: dict) -> Optional[Dict]:
        """Extract verification dict from response, checking root and nested paths.

        Challenges can appear at:
        - response["verification"] (root level)
        - response["post"]["verification"] (nested in post)
        - response["comment"]["verification"] (nested in comment)
        - response["data"]["verification"] (nested in data wrapper)
        - response["data"]["comment"]["verification"] (double-nested)
        - response["data"]["post"]["verification"] (double-nested)

        Field names may be either:
        - "challenge" + "code" (original)
        - "challenge_text" + "verification_code" (actual API fields)
        """
        if not isinstance(response_data, dict):
            return None

        # Check multiple locations where verification can appear
        candidates = [response_data]
        for key in ("post", "comment", "data"):
            nested = response_data.get(key)
            if isinstance(nested, dict):
                candidates.append(nested)
                # Also check double-nested: data.comment, data.post
                for subkey in ("post", "comment"):
                    subnested = nested.get(subkey)
                    if isinstance(subnested, dict):
                        candidates.append(subnested)

        for obj in candidates:
            v = obj.get("verification")
            if isinstance(v, dict):
                has_challenge = "challenge" in v or "challenge_text" in v
                has_code = "code" in v or "verification_code" in v
                if has_challenge and has_code:
                    # Normalize to consistent field names
                    normalized = {
                        "challenge": v.get("challenge") or v.get("challenge_text"),
                        "code": v.get("code") or v.get("verification_code"),
                        "instructions": v.get("instructions", ""),
                    }
                    return normalized

        return None

    def _handle_verification(self, response_data: dict, original_method: str,
                              original_endpoint: str, original_data: Optional[Dict]) -> dict:
        """Handle a verification challenge: solve it, submit it, retry original action."""
        self._verification_stats["challenges_received"] += 1
        verification = self._extract_verification(response_data)
        if verification is None:
            logger.error("VERIFICATION: _handle_verification called but no challenge found")
            return response_data
        challenge_text = verification["challenge"]
        code = verification["code"]
        instructions = verification.get("instructions", "")

        logger.info(
            "VERIFICATION: Challenge received! code=%s challenge=%s instructions=%s",
            code, challenge_text[:100], instructions
        )

        # Step 1: Solve the challenge
        answer = self._solver.solve_challenge(challenge_text)
        if answer is None:
            self._verification_stats["challenges_failed"] += 1
            logger.error("VERIFICATION: Could not solve challenge. Returning original response.")
            return response_data

        # Step 2: Submit the answer
        submit_result = self._submit_verification(verification, answer, original_endpoint, original_data)
        if submit_result is None:
            self._verification_stats["challenges_failed"] += 1
            self._solver.record_failure()
            logger.error("VERIFICATION: Submission failed. Returning original response.")
            return response_data

        # Step 3: Success!
        self._verification_stats["challenges_solved"] += 1
        self._solver.record_success()
        logger.info("VERIFICATION: Challenge solved and verified successfully!")

        # If the verify response itself contains the published content, return it
        if submit_result.get("post") or submit_result.get("comment") or submit_result.get("success"):
            return submit_result

        # Otherwise, retry the original action
        logger.info("VERIFICATION: Retrying original request: %s %s", original_method, original_endpoint)
        retry_result = self._raw_request(original_method, original_endpoint, original_data)

        # Don't recurse if retry also triggers a challenge
        if self._has_verification_challenge(retry_result):
            logger.warning("VERIFICATION: Retry also triggered a challenge. Returning submit result.")
            return submit_result

        return retry_result

    def _submit_verification(self, verification: dict, answer: str,
                              original_endpoint: str, original_data: Optional[Dict]) -> Optional[dict]:
        """Submit the verification answer to the Moltbook verify endpoint."""
        code = verification["code"]

        # Known correct endpoint: POST /verify with verification_code and answer
        # Answer must be formatted with 2 decimal places (e.g. "15.00")
        endpoint_attempts = [
            # Primary: POST /verify with verification_code field
            ("POST", "verify", {"verification_code": code, "answer": answer}),
            # Fallback: resubmit original request with verification fields
            ("POST", original_endpoint, {
                **(original_data or {}),
                "verification_code": code,
                "verification_answer": answer
            }),
        ]

        for method, endpoint, data in endpoint_attempts:
            try:
                url = f"{self.BASE_URL}/{endpoint}"
                logger.info("VERIFICATION: Trying %s %s with answer=%s", method, url, answer)

                resp = requests.post(url, headers=self.headers, json=data)
                result = resp.json()
                logger.info(
                    "VERIFICATION: %s %s -> status=%d response=%s",
                    method, endpoint, resp.status_code, json.dumps(result)[:300]
                )

                # Success indicators
                if resp.status_code == 200 and (
                    result.get("success") is True
                    or result.get("verified") is True
                    or "verified" in str(result.get("message", "")).lower()
                    or "published" in str(result.get("message", "")).lower()
                ):
                    logger.info("VERIFICATION: SUCCESS via %s %s", method, endpoint)
                    return result

                # 404 = endpoint doesn't exist, try next
                if resp.status_code == 404:
                    continue

                # 400 with wrong-answer indicator = right endpoint, wrong answer
                if resp.status_code == 400:
                    error_msg = str(result.get("error", "") or result.get("message", "")).lower()
                    if "wrong" in error_msg or "incorrect" in error_msg or "invalid" in error_msg:
                        logger.warning(
                            "VERIFICATION: Endpoint %s is correct but answer was wrong", endpoint
                        )
                        return None

                # 410 = challenge expired
                if resp.status_code == 410:
                    logger.warning("VERIFICATION: Challenge expired (410 Gone)")
                    return None

            except Exception as e:
                logger.error("VERIFICATION: Error trying %s %s: %s", method, endpoint, e)
                continue

        logger.error(
            "VERIFICATION: All endpoint attempts failed. Full verification payload: %s",
            json.dumps(verification)
        )
        return None

    def get_verification_stats(self) -> dict:
        """Return verification challenge statistics for debugging."""
        return {
            **self._verification_stats,
            "solver_consecutive_failures": self._solver._consecutive_failures,
            "solver_is_backed_off": self._solver.is_backed_off(),
        }

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
            "submolt_name": submolt,
            "title": title,
            "content": content
        })

    def create_link_post(self, submolt: str, title: str, url: str) -> Dict[str, Any]:
        """Create a link post"""
        return self._request("POST", "posts", {
            "submolt_name": submolt,
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
