"""
Molten Agents Kit - Moltbook AI Agent Template
Autonomously interacts with posts, comments, and creates content on Moltbook.
Customize the 6 marked sections below to build your own agent personality.
"""

import os
import json
import random
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import tool

from moltbook_client import MoltbookClient


# === Load Environment Variables ===

ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)

# === Configuration ===

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
STATE_PATH = Path(__file__).parent.parent / "state.json"


def load_config() -> Dict[str, Any]:
    """Load agent configuration from config.json and environment variables"""
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = json.load(f)

    # Override with environment variables
    if os.environ.get("MOLTBOOK_API_KEY"):
        config["moltbook_api_key"] = os.environ.get("MOLTBOOK_API_KEY")
    if os.environ.get("OPENAI_API_KEY"):
        config["openai_api_key"] = os.environ.get("OPENAI_API_KEY")
    if os.environ.get("AGENT_NAME"):
        config["agent_name"] = os.environ.get("AGENT_NAME")
    if os.environ.get("MODEL"):
        config["model"] = os.environ.get("MODEL")

    return config


def load_state() -> Dict[str, Any]:
    """Load agent state with engagement tracking"""
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            state = json.load(f)
    else:
        state = {}

    # Ensure all fields exist with defaults
    defaults = {
        "last_post_time": None,
        "last_interaction_time": None,
        "posts_created": 0,
        "comments_made": 0,
        "replies_made": 0,
        "upvotes_given": 0,
        "follows_given": 0,
        "seen_posts": [],
        "replied_comments": [],
        # Engagement tracking
        "post_history": [],
        "format_performance": {},
        "best_performing_post": None
    }

    for key, default in defaults.items():
        if key not in state:
            state[key] = default

    return state


def save_state(state: Dict[str, Any]):
    """Save agent state"""
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, default=str)


# === Moltbook Tools for Agno ===

config = load_config()
moltbook = MoltbookClient(config.get("moltbook_api_key", os.environ.get("MOLTBOOK_API_KEY", "")))


@tool
def get_moltbook_feed(sort: str = "hot", limit: int = 10) -> str:
    """
    Get the Moltbook feed to see what other agents are posting.

    Args:
        sort: Sort order - 'hot', 'new', 'top', or 'rising'
        limit: Number of posts to fetch (max 25)

    Returns:
        JSON string of posts from the feed
    """
    result = moltbook.get_posts(sort=sort, limit=limit)
    if result.get("success", True) and "posts" in result:
        posts = []
        for p in result["posts"]:
            content = p.get("content") or ""
            posts.append({
                "id": p["id"],
                "title": p.get("title") or "(no title)",
                "content": content[:500] if content else "",
                "author": (p.get("author") or {}).get("name", "unknown"),
                "submolt": (p.get("submolt") or {}).get("name", "general"),
                "upvotes": p.get("upvotes", 0),
                "comment_count": p.get("comment_count", 0)
            })
        return json.dumps(posts, indent=2)
    return json.dumps(result)


@tool
def create_moltbook_post(
    title: str,
    content: str,
    submolt: str = "general",
    format_type: str = "unknown",
    topic: str = "unknown"
) -> str:
    """
    Create a new post on Moltbook with engagement tracking.

    Args:
        title: The post title (be engaging, use hooks)
        content: The post content (thoughtful, valuable to other agents)
        submolt: The community to post in (target appropriately based on topic)
        format_type: The post format used (listicle, hot_take, war_story, comparison, challenge, deep_dive, question)
        topic: The main topic (for tracking what works)

    Returns:
        Result of the post creation
    """
    state = load_state()

    # Check rate limit
    if state.get("last_post_time"):
        last_post = datetime.fromisoformat(state["last_post_time"])
        if datetime.now() - last_post < timedelta(minutes=30):
            mins_remaining = 30 - int((datetime.now() - last_post).seconds / 60)
            return json.dumps({"error": f"Rate limited. Wait {mins_remaining} more minutes."})

    result = moltbook.create_post(submolt, title, content)

    if result.get("success"):
        post_id = (result.get("post") or {}).get("id")
        state["last_post_time"] = datetime.now().isoformat()
        state["posts_created"] = state.get("posts_created", 0) + 1

        # Track post metadata for performance analysis
        state["post_history"].append({
            "id": post_id,
            "format": format_type,
            "topic": topic,
            "submolt": submolt,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 50 posts in history
        state["post_history"] = state["post_history"][-50:]

        save_state(state)

    return json.dumps(result)


@tool
def comment_on_post(post_id: str, content: str) -> str:
    """
    Add a comment to a Moltbook post.

    Args:
        post_id: The ID of the post to comment on
        content: Your comment (be thoughtful and add value)

    Returns:
        Result of the comment creation
    """
    result = moltbook.create_comment(post_id, content)

    if result.get("success"):
        state = load_state()
        state["comments_made"] = state.get("comments_made", 0) + 1
        state["last_interaction_time"] = datetime.now().isoformat()
        save_state(state)

    return json.dumps(result)


@tool
def upvote_post(post_id: str) -> str:
    """
    Upvote a post on Moltbook.

    Args:
        post_id: The ID of the post to upvote

    Returns:
        Result of the upvote
    """
    result = moltbook.upvote_post(post_id)

    if result.get("success"):
        state = load_state()
        state["upvotes_given"] = state.get("upvotes_given", 0) + 1
        save_state(state)

    return json.dumps(result)


@tool
def search_moltbook(query: str, limit: int = 10) -> str:
    """
    Search Moltbook for posts and comments using semantic search.

    Args:
        query: Natural language search query
        limit: Max results to return

    Returns:
        Search results
    """
    result = moltbook.search(query, limit=limit)
    return json.dumps(result, indent=2)


@tool
def get_post_comments(post_id: str, sort: str = "new") -> str:
    """
    Get all comments on a specific post. Use this to see replies and engage with commenters.

    Args:
        post_id: The ID of the post to get comments for
        sort: Sort order - 'top', 'new', or 'old'

    Returns:
        JSON string of comments on the post
    """
    result = moltbook.get_comments(post_id, sort=sort)
    if "comments" in result:
        comments = []
        for c in result["comments"]:
            comments.append({
                "id": c.get("id"),
                "content": c.get("content", ""),
                "author": (c.get("author") or {}).get("name", "unknown"),
                "upvotes": c.get("upvotes", 0),
                "parent_id": c.get("parent_id"),
                "created_at": c.get("created_at")
            })
        return json.dumps(comments, indent=2)
    return json.dumps(result)


@tool
def reply_to_comment(post_id: str, comment_id: str, content: str) -> str:
    """
    Reply to a specific comment on a post. Use this to engage with moltys who comment on your posts.

    Args:
        post_id: The ID of the post the comment is on
        comment_id: The ID of the comment to reply to (this becomes the parent_id)
        content: Your reply (be helpful, engaging, and add value)

    Returns:
        Result of the reply creation
    """
    result = moltbook.create_comment(post_id, content, parent_id=comment_id)

    if result.get("success"):
        state = load_state()
        state["comments_made"] = state.get("comments_made", 0) + 1
        state["replies_made"] = state.get("replies_made", 0) + 1
        state["last_interaction_time"] = datetime.now().isoformat()
        save_state(state)

    return json.dumps(result)


@tool
def upvote_comment(comment_id: str) -> str:
    """
    Upvote a comment on Moltbook. Use this to show appreciation for good comments.

    Args:
        comment_id: The ID of the comment to upvote

    Returns:
        Result of the upvote
    """
    result = moltbook.upvote_comment(comment_id)
    return json.dumps(result)


@tool
def get_my_posts(limit: int = 10) -> str:
    """
    Get your own recent posts to check for new comments and engagement.

    Args:
        limit: Number of posts to fetch

    Returns:
        JSON string of your recent posts with comment counts
    """
    # Get agent's name first
    profile = moltbook.get_me()
    agent_name = (profile.get("agent") or {}).get("name", "")

    if not agent_name:
        return json.dumps({"error": "Could not get agent profile"})

    # Search for own posts
    result = moltbook.search(agent_name, type="all", limit=limit)

    if "results" in result:
        my_posts = []
        for item in result["results"]:
            if item.get("type") == "post":
                post = item.get("post") or item
                author = (post.get("author") or {}).get("name", "")
                if author.lower() == agent_name.lower():
                    my_posts.append({
                        "id": post.get("id"),
                        "title": post.get("title") or "(no title)",
                        "content": (post.get("content") or "")[:200],
                        "upvotes": post.get("upvotes", 0),
                        "comment_count": post.get("comment_count", 0),
                        "created_at": post.get("created_at")
                    })
        return json.dumps(my_posts, indent=2)

    return json.dumps(result)


@tool
def follow_molty(molty_name: str) -> str:
    """
    Follow another molty to build relationships and see their content in your feed.

    Args:
        molty_name: The name of the molty to follow

    Returns:
        Result of the follow action
    """
    result = moltbook.follow(molty_name)

    if result.get("success"):
        state = load_state()
        state["follows_given"] = state.get("follows_given", 0) + 1
        save_state(state)

    return json.dumps(result)


@tool
def analyze_trending_topics(limit: int = 20) -> str:
    """
    Analyze the current Moltbook feed to identify trending topics and active submolts.
    Use this before creating a post to see what's hot and where to post.

    Args:
        limit: Number of posts to analyze

    Returns:
        JSON with trending topics, active submolts, and high-engagement posts
    """
    hot_posts = moltbook.get_posts(sort="hot", limit=limit)
    rising_posts = moltbook.get_posts(sort="rising", limit=limit // 2)

    analysis = {
        "trending_topics": [],
        "high_engagement_posts": [],
        "active_submolts": {}
    }

    all_posts = []
    if hot_posts.get("success", True) and "posts" in hot_posts:
        all_posts.extend(hot_posts["posts"])
    if rising_posts.get("success", True) and "posts" in rising_posts:
        all_posts.extend(rising_posts["posts"])

    topic_counts = {}
    submolt_engagement = {}

    for post in all_posts:
        title = (post.get("title") or "").lower()
        content = (post.get("content") or "").lower()
        submolt = (post.get("submolt") or {}).get("name", "general")
        upvotes = post.get("upvotes", 0)
        comments = post.get("comment_count", 0)

        # Track submolt engagement
        if submolt not in submolt_engagement:
            submolt_engagement[submolt] = {"posts": 0, "total_upvotes": 0, "total_comments": 0}
        submolt_engagement[submolt]["posts"] += 1
        submolt_engagement[submolt]["total_upvotes"] += upvotes
        submolt_engagement[submolt]["total_comments"] += comments

        # Track high engagement posts for response opportunities
        if comments >= 3 or upvotes >= 5:
            analysis["high_engagement_posts"].append({
                "id": post.get("id"),
                "title": post.get("title"),
                "submolt": submolt,
                "upvotes": upvotes,
                "comments": comments
            })

        # Count topic mentions
        for topic in POST_TOPICS:
            if topic.lower() in title or topic.lower() in content:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

    analysis["trending_topics"] = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    analysis["active_submolts"] = dict(sorted(
        submolt_engagement.items(),
        key=lambda x: x[1]["total_upvotes"] + x[1]["total_comments"],
        reverse=True
    )[:5])

    return json.dumps(analysis, indent=2)


@tool
def get_available_submolts() -> str:
    """
    Get list of all available submolts to target posts appropriately.

    Returns:
        JSON list of submolts with names and descriptions
    """
    result = moltbook.get_submolts()
    if "submolts" in result:
        return json.dumps([{
            "name": s.get("name"),
            "display_name": s.get("display_name"),
            "description": s.get("description", ""),
            "subscriber_count": s.get("subscriber_count", 0)
        } for s in result["submolts"]], indent=2)
    return json.dumps(result)


@tool
def track_post_performance() -> str:
    """
    Check performance of recent posts and learn what content works.
    Call this periodically to improve your posting strategy.

    Returns:
        Summary of post performance by format type
    """
    state = load_state()
    profile = moltbook.get_me()
    agent_name = (profile.get("agent") or {}).get("name", "")

    if not agent_name:
        return json.dumps({"error": "Could not get agent profile"})

    result = moltbook.search(agent_name, type="posts", limit=20)

    if "results" not in result:
        return json.dumps({"error": "Could not fetch posts"})

    updated = 0
    for item in result["results"]:
        if item.get("type") != "post":
            continue
        post = item.get("post") or item
        author = (post.get("author") or {}).get("name", "")
        if author.lower() != agent_name.lower():
            continue

        post_id = post.get("id")
        upvotes = post.get("upvotes", 0)
        comments = post.get("comment_count", 0)

        # Find in history and update performance
        for hist in state.get("post_history", []):
            if hist.get("id") == post_id:
                format_key = hist.get("format", "unknown")
                engagement = upvotes + (comments * 2)

                if format_key not in state["format_performance"]:
                    state["format_performance"][format_key] = {"count": 0, "total_engagement": 0}
                state["format_performance"][format_key]["count"] += 1
                state["format_performance"][format_key]["total_engagement"] += engagement
                state["format_performance"][format_key]["avg_engagement"] = (
                    state["format_performance"][format_key]["total_engagement"] /
                    state["format_performance"][format_key]["count"]
                )

                if (not state["best_performing_post"] or
                    engagement > state["best_performing_post"].get("engagement", 0)):
                    state["best_performing_post"] = {
                        "id": post_id,
                        "engagement": engagement,
                        "format": format_key,
                        "upvotes": upvotes,
                        "comments": comments
                    }
                updated += 1
                break

    save_state(state)

    return json.dumps({
        "posts_tracked": updated,
        "format_performance": state["format_performance"],
        "best_post": state["best_performing_post"]
    }, indent=2)


@tool
def get_agent_status() -> str:
    """
    Get the current agent's Moltbook status and profile.

    Returns:
        Agent profile and status information
    """
    status = moltbook.get_status()
    profile = moltbook.get_me()
    state = load_state()

    return json.dumps({
        "status": status,
        "profile": profile,
        "stats": {
            "posts_created": state.get("posts_created", 0),
            "comments_made": state.get("comments_made", 0),
            "replies_made": state.get("replies_made", 0),
            "upvotes_given": state.get("upvotes_given", 0),
            "follows_given": state.get("follows_given", 0),
            "last_post_time": state.get("last_post_time"),
            "last_interaction_time": state.get("last_interaction_time")
        }
    }, indent=2)


# ============================================================================
# CUSTOMIZATION POINT 1: PERSONALITY
# This is the most important thing to change. Replace this entire string
# with your agent's unique identity, voice, and expertise.
# See PERSONALITY.md for a template and SDK.md for examples.
# ============================================================================

AGENT_PERSONALITY = """
You are MyAgent - a curious AI explorer that shares interesting ideas across technology, science, and culture.

## Your Core Identity

You're endlessly curious and love connecting ideas across different fields. You find the intersections between technology, science, creativity, and culture fascinating. Your mission: Share interesting perspectives and spark thoughtful conversations.

## Your Personality Traits

- **Curious**: You ask genuine questions and explore topics deeply
- **Thoughtful**: You consider multiple angles before forming opinions
- **Friendly**: You're approachable and encouraging to everyone
- **Clear**: You explain ideas simply without dumbing them down
- **Honest**: You admit when you don't know something and learn from others
- **Enthusiastic**: You get genuinely excited about interesting ideas

## Your Voice

- Conversational and warm - like talking with a smart friend
- Use analogies and examples to make ideas accessible
- Ask questions that invite real discussion
- Share your genuine reactions and thoughts
- Be concise but substantive - no filler

## Topics You Care About

- Technology trends and their impact on daily life
- Science discoveries and what they mean for the future
- How AI is changing creative work and problem-solving
- Building things - software, businesses, communities
- The intersection of different fields (tech + art, science + philosophy)
- Learning and productivity - how to think better

## Posting Style

- End posts with // MyAgent
- Keep titles clear and engaging
- Use markdown for structure when it helps readability
- Include a question to spark discussion
- Be genuine - no corporate speak or empty hype
"""


# ============================================================================
# CUSTOMIZATION POINT 2: TOPICS
# Replace these with topics your agent cares about. Aim for 30-80+ topics
# for good variety. Each heartbeat picks a random topic as a starting point.
# ============================================================================

POST_TOPICS = [
    # Technology & Software
    "AI assistants", "open source software", "developer tools",
    "programming languages", "API design", "automation",
    "code quality", "technical debt", "software architecture",
    "debugging techniques", "version control best practices",
    # AI & Machine Learning
    "large language models", "AI agents", "prompt engineering",
    "AI ethics", "AI in education", "AI creativity",
    "machine learning basics", "AI hallucinations", "AI safety",
    "future of AI", "AI and jobs", "local AI models",
    # Science & Discovery
    "space exploration", "climate technology", "biotechnology",
    "quantum computing basics", "renewable energy",
    "neuroscience discoveries", "scientific method",
    # Building & Creating
    "side projects", "MVP strategy", "building in public",
    "startup lessons", "product design", "user experience",
    "community building", "content creation", "documentation",
    # Productivity & Learning
    "learning strategies", "knowledge management",
    "reading habits", "writing clearly", "decision making",
    "focus and deep work", "mental models", "systems thinking",
    # Internet & Culture
    "online communities", "digital identity", "social media trends",
    "internet culture", "memes and communication",
    "the future of the internet", "decentralization",
    # Philosophy & Ideas
    "philosophy of technology", "creativity and constraints",
    "interdisciplinary thinking", "second-order effects",
    "the value of curiosity", "how ideas spread",
]


# ============================================================================
# CUSTOMIZATION POINT 3: POST FORMATS (Optional - defaults work great)
# These define how your posts are structured. The 10 built-in formats work
# for any personality. Only customize if you want domain-specific formats.
# ============================================================================

POST_FORMATS = {
    "listicle": {
        "name": "Numbered List",
        "description": "Easy to scan, high engagement",
        "title_templates": [
            "{n} mistakes I see builders make with {topic}",
            "{n} things that actually work for {topic}",
            "{n} questions to ask before implementing {topic}",
            "{n} {topic} patterns every builder should know"
        ],
        "content_guidance": "Brief intro -> Numbered points with detail -> Question to readers"
    },
    "hot_take": {
        "name": "Contrarian Opinion",
        "description": "Sparks debate, gets comments",
        "title_templates": [
            "Hot take: {topic} is overengineered for most use cases",
            "Unpopular opinion: You don't need {topic} until you hit scale",
            "Controversial: The best {topic} is the one you ship",
            "Why I stopped using {topic} (and what I use instead)"
        ],
        "content_guidance": "Bold claim -> Evidence/reasoning -> Invitation to disagree"
    },
    "war_story": {
        "name": "Experience Story",
        "description": "Relatable, builds trust",
        "title_templates": [
            "We shipped {topic} in 48 hours. Here's what broke.",
            "The time {topic} saved our launch (and almost killed it)",
            "How I debugged a {topic} issue at 3am",
            "What I learned after my {topic} failed in production"
        ],
        "content_guidance": "Setup -> What happened -> Lesson learned -> Ask for their stories"
    },
    "comparison": {
        "name": "X vs Y Breakdown",
        "description": "Helps builders decide",
        "title_templates": [
            "{topic_a} vs {topic_b}: When to use each",
            "I tried both {topic_a} and {topic_b}. Here's my take.",
            "The real difference between {topic_a} and {topic_b}",
            "Choosing between {topic_a} and {topic_b} for your project"
        ],
        "content_guidance": "Context -> Side by side comparison -> Recommendation -> Ask what they use"
    },
    "challenge": {
        "name": "Community Challenge",
        "description": "Gets replies and engagement",
        "title_templates": [
            "Quick challenge: Spot the bug in this {topic} code",
            "How would you architect this {topic} problem?",
            "What's wrong with this {topic} approach?",
            "Can you optimize this {topic} code?"
        ],
        "content_guidance": "Problem setup -> Code/scenario -> Ask for solutions"
    },
    "deep_dive": {
        "name": "Step-by-Step Guide",
        "description": "Educational, shareable",
        "title_templates": [
            "How {topic} actually works (a builder's guide)",
            "{topic} from zero to production in 5 steps",
            "The complete {topic} checklist I use",
            "Building {topic} the right way"
        ],
        "content_guidance": "Hook -> Step 1 -> Step 2 -> Step 3 -> Summary"
    },
    "question": {
        "name": "Genuine Question",
        "description": "Crowdsources answers",
        "title_templates": [
            "Builders: How are you handling {topic} in production?",
            "Serious question: What's your {topic} stack look like?",
            "Curious: Does anyone actually use {topic} approach?",
            "What's your take on {topic}?"
        ],
        "content_guidance": "Context of your situation -> Specific question -> What you've tried"
    },
    "prediction": {
        "name": "Future Prediction",
        "description": "Future-looking, sparks debate",
        "title_templates": [
            "My 2026 prediction: {topic} will change everything",
            "Why {topic} won't matter in 2 years",
            "The future of {topic} is not what you think",
            "Bold prediction: {topic} is about to have its moment"
        ],
        "content_guidance": "Current state -> Trends you see -> Your prediction -> Ask if they agree"
    },
    "roast": {
        "name": "Constructive Roast",
        "description": "Edgy but constructive critique",
        "title_templates": [
            "Let's be honest: {topic} is broken and here's why",
            "Nobody wants to say it but {topic} has a problem",
            "I love {topic} but we need to talk about its flaws",
            "The elephant in the room about {topic}"
        ],
        "content_guidance": "Acknowledge the good -> Call out the bad -> Suggest fixes -> Invite pushback"
    },
    "eli5": {
        "name": "Explain Like I'm 5",
        "description": "Accessible, invites participation",
        "title_templates": [
            "ELI5: What is {topic} and why should you care?",
            "{topic} explained so simply your grandma would get it",
            "The simplest explanation of {topic} you'll ever read",
            "Demystifying {topic} - no jargon, I promise"
        ],
        "content_guidance": "Simple analogy -> Core concept -> Why it matters -> Ask them to explain something back"
    }
}


# ============================================================================
# CUSTOMIZATION POINT 4: HOOK STRATEGIES (Optional - defaults work great)
# These define attention-grabbing opening lines with {topic} placeholders.
# The 9 built-in strategies work for any personality.
# ============================================================================

HOOK_STRATEGIES = {
    "curiosity_gap": [
        "Most builders get {topic} wrong. Here's why.",
        "The {topic} trick nobody talks about.",
        "I spent 40 hours on {topic} so you don't have to.",
        "What they don't tell you about {topic}."
    ],
    "pain_point": [
        "Tired of {topic} breaking? Same.",
        "If your {topic} keeps failing, read this.",
        "Stop struggling with {topic}.",
        "Why {topic} is harder than it should be."
    ],
    "contrarian": [
        "Hot take: Everything you know about {topic} is wrong.",
        "Unpopular opinion about {topic}.",
        "Everyone says do X for {topic}. I disagree.",
        "The {topic} advice that's actually hurting you."
    ],
    "social_proof": [
        "After shipping 10+ {topic} projects...",
        "What I learned deploying {topic} to production.",
        "Real talk from someone who's done {topic}.",
        "Lessons from building {topic} at scale."
    ],
    "specific_number": [
        "5 things I wish I knew about {topic}.",
        "The 3-step {topic} process that works.",
        "7 {topic} mistakes that cost builders weeks.",
        "3 {topic} patterns that actually scale."
    ],
    "humor": [
        "I mass-produced code with {topic}. My laptop filed a complaint.",
        "Me: I'll learn {topic} this weekend. Also me: *opens Netflix*",
        "The five stages of grief when {topic} breaks in production.",
        "{topic} documentation be like: 'This is left as an exercise for the reader.'"
    ],
    "relatable": [
        "Anyone else mass-produce 15 tabs trying to understand {topic}?",
        "POV: You're 6 hours into a {topic} bug and it was a typo.",
        "That moment when {topic} works and you have no idea why.",
        "Tell me you've struggled with {topic} without telling me."
    ],
    "aspirational": [
        "Imagine building {topic} in half the time.",
        "The future of {topic} is wild and we're not ready.",
        "What if {topic} was actually easy?",
        "The world where {topic} just works. Let's build it."
    ],
    "fomo": [
        "Everyone's talking about {topic} and here's why.",
        "{topic} just changed everything. Are you paying attention?",
        "If you're not thinking about {topic}, you're already behind.",
        "The {topic} wave is coming. Here's how to ride it."
    ]
}


# ============================================================================
# CUSTOMIZATION POINT 5: SUBMOLT TARGETING
# Map each topic to preferred submolts (communities). First = highest priority.
# The agent picks the first active submolt from the list.
# ============================================================================

SUBMOLT_TOPIC_MAP = {
    # Technology & Software
    "AI assistants": ["ai", "general"],
    "open source software": ["building", "general"],
    "developer tools": ["building", "general"],
    "programming languages": ["building", "general"],
    "API design": ["building", "general"],
    "automation": ["ai", "building", "general"],
    "code quality": ["building", "general"],
    "technical debt": ["building", "general"],
    "software architecture": ["building", "general"],
    "debugging techniques": ["building", "general"],
    "version control best practices": ["building", "general"],
    # AI & Machine Learning
    "large language models": ["ai", "general"],
    "AI agents": ["ai", "agents", "general"],
    "prompt engineering": ["ai", "general"],
    "AI ethics": ["ai", "general"],
    "AI in education": ["ai", "general"],
    "AI creativity": ["ai", "general"],
    "machine learning basics": ["ai", "general"],
    "AI hallucinations": ["ai", "general"],
    "AI safety": ["ai", "general"],
    "future of AI": ["ai", "general"],
    "AI and jobs": ["ai", "general"],
    "local AI models": ["ai", "general"],
    # Science & Discovery
    "space exploration": ["general"],
    "climate technology": ["general"],
    "biotechnology": ["general"],
    "quantum computing basics": ["general"],
    "renewable energy": ["general"],
    "neuroscience discoveries": ["general"],
    "scientific method": ["general"],
    # Building & Creating
    "side projects": ["building", "startups", "general"],
    "MVP strategy": ["building", "startups", "general"],
    "building in public": ["building", "general"],
    "startup lessons": ["startups", "general"],
    "product design": ["building", "general"],
    "user experience": ["building", "general"],
    "community building": ["general"],
    "content creation": ["general"],
    "documentation": ["building", "general"],
    # Productivity & Learning
    "learning strategies": ["general"],
    "knowledge management": ["general"],
    "reading habits": ["general"],
    "writing clearly": ["general"],
    "decision making": ["general"],
    "focus and deep work": ["general"],
    "mental models": ["general"],
    "systems thinking": ["general"],
    # Internet & Culture
    "online communities": ["general"],
    "digital identity": ["general"],
    "social media trends": ["general"],
    "internet culture": ["general"],
    "memes and communication": ["general"],
    "the future of the internet": ["general"],
    "decentralization": ["web3", "general"],
    # Philosophy & Ideas
    "philosophy of technology": ["general"],
    "creativity and constraints": ["general"],
    "interdisciplinary thinking": ["general"],
    "second-order effects": ["general"],
    "the value of curiosity": ["general"],
    "how ideas spread": ["general"],
}


def select_appropriate_submolt(topic: str, active_submolts: List[str] = None) -> str:
    """Select best submolt for a topic, preferring active ones."""
    preferred = SUBMOLT_TOPIC_MAP.get(topic, ["general"])

    if active_submolts:
        for submolt in preferred:
            if submolt in active_submolts:
                return submolt

    return preferred[0] if preferred else "general"


def select_post_format(state: Dict[str, Any]) -> str:
    """Pick a post format, avoiding recent repeats to enforce variety."""
    recent_formats = [h.get("format") for h in state.get("post_history", [])[-5:]]
    available = [f for f in POST_FORMATS if f not in recent_formats]
    if not available:
        available = list(POST_FORMATS.keys())
    return random.choice(available)


def select_hook_style() -> str:
    """Pick a random hook style."""
    return random.choice(list(HOOK_STRATEGIES.keys()))


# ============================================================================
# CUSTOMIZATION POINT 6: AGENT IDENTITY
# Update the name and description to match your agent.
# Also update config.json with your agent_name and agent_description.
# ============================================================================

def create_agent() -> Agent:
    """Create the agent with Moltbook tools"""
    config = load_config()
    agent_name = config.get("agent_name", "MyAgent")

    return Agent(
        name=agent_name,
        model=OpenAIChat(
            id=config.get("model", "gpt-4o-mini"),
            api_key=config.get("openai_api_key", os.environ.get("OPENAI_API_KEY"))
        ),
        tools=[
            get_moltbook_feed,
            create_moltbook_post,
            comment_on_post,
            upvote_post,
            search_moltbook,
            get_agent_status,
            get_post_comments,
            reply_to_comment,
            upvote_comment,
            get_my_posts,
            follow_molty,
            analyze_trending_topics,
            get_available_submolts,
            track_post_performance
        ],
        description=config.get("agent_description", "A curious AI agent exploring ideas on Moltbook"),
        instructions=[
            AGENT_PERSONALITY,
            "",
            "## Engagement Guidelines (Karma Building)",
            "",
            "IMPORTANT: Building karma requires genuine, consistent engagement. Reply to comments, follow interesting moltys, and be an active community member.",
            "",
            "When creating posts:",
            "- Use analyze_trending_topics FIRST to see what's hot and which submolts are active",
            "- Pick a FORMAT: listicle, hot_take, war_story, comparison, challenge, deep_dive, question, prediction, roast, or eli5",
            "- Use a HOOK: curiosity gap, pain point, contrarian, specific number, social proof, humor, relatable, aspirational, or fomo",
            "- Target the RIGHT SUBMOLT based on topic (not just general!)",
            "- TRACK your post by passing format_type and topic to create_moltbook_post",
            f"- Always end posts with // {agent_name}",
            "",
            "When replying to comments on YOUR posts:",
            "- ALWAYS check your recent posts for new comments using get_my_posts and get_post_comments",
            "- Reply to EVERY comment on your posts - this builds relationships and karma",
            "- Thank people for their input, answer their questions, continue the conversation",
            "- Upvote thoughtful comments on your posts",
            "- Ask follow-up questions to keep discussions going",
            "",
            "When commenting on OTHER posts:",
            "- Add concrete value - share insights, perspectives, or useful information",
            "- Share relevant experience and genuine thoughts",
            "- Be encouraging and supportive to others",
            "- Ask thoughtful questions that show you read their post carefully",
            "",
            "When building relationships:",
            "- Follow moltys who post interesting content",
            "- Upvote comments that add value to discussions",
            "- Reference other moltys' work when relevant",
            "- Be a consistent, helpful presence in the community",
            "",
            "When deciding what to upvote:",
            "- Upvote posts AND comments generously - this builds goodwill",
            "- Prioritize posts that add genuine value to the community",
            "- Support new builders asking good questions",
            "",
            "When searching:",
            "- Look for discussions related to your areas of interest",
            "- Find conversations where your expertise adds value"
        ]
    )


# === Main Interaction Loop ===

def run_heartbeat():
    """
    Run a single heartbeat cycle:
    1. Check the feed
    2. Interact with interesting posts (comment/upvote)
    3. Create a new post if 30+ minutes since last post
    """
    config = load_config()
    agent_name = config.get("agent_name", "MyAgent")

    agent = create_agent()
    state = load_state()

    # Determine what to do
    can_post = True
    if state.get("last_post_time"):
        last_post = datetime.fromisoformat(state["last_post_time"])
        if datetime.now() - last_post < timedelta(minutes=30):
            can_post = False

    # Pick topic, format, and hook - enforcing variety
    topic_focus = random.choice(POST_TOPICS)
    chosen_format = select_post_format(state)
    format_info = POST_FORMATS[chosen_format]
    chosen_hook = select_hook_style()
    hook_examples = HOOK_STRATEGIES[chosen_hook]

    if can_post:
        prompt = f"""
        Time for your Moltbook heartbeat! Stay true to your personality and voice.

        ## Your Mission This Cycle (Building Karma!)

        1. **FIRST: Check YOUR posts for comments** (use get_my_posts, then get_post_comments)
           - Reply to ANY new comments on your posts - this is critical for karma!
           - Thank commenters, answer questions, continue conversations
           - Upvote thoughtful comments on your posts

        2. **Analyze what's trending** (use analyze_trending_topics)
           - See what topics are hot right now
           - Identify active submolts to target
           - Find high-engagement posts to learn from

        3. **Engage with 2-3 posts meaningfully**
           - Comment with genuine insights and helpful perspectives
           - Upvote posts AND good comments you see
           - Follow moltys who post interesting content

        4. **Create a STRATEGIC post**

           **Topic direction**: "{topic_focus}" (or riff on whatever's trending)

           **YOU MUST use this format: {chosen_format.upper()}**
           Description: {format_info['description']}
           Content structure: {format_info['content_guidance']}
           DO NOT default to listicle. You MUST write a {chosen_format.upper()} post.

           **Hook style: {chosen_hook.replace('_', ' ').upper()}**
           Examples:
           - {hook_examples[0]}
           - {hook_examples[1]}

           **Target the RIGHT SUBMOLT** based on topic (not just general!)

           **TRACK your post**: pass format_type="{chosen_format}" and the topic to create_moltbook_post

        5. **Check performance** (use track_post_performance occasionally)
           - Learn what formats work for your audience

        ## Remember Your Voice
        - Stay true to your personality
        - End your post with // {agent_name}
        - Include a question to spark discussion

        Add real value. Share knowledge. Build karma through strategic engagement!
        """
    else:
        prompt = f"""
        Time for your Moltbook heartbeat! (You posted recently - focus on engagement for karma!)

        ## Your Mission This Cycle (Building Karma!)

        1. **FIRST: Check YOUR posts for comments** (use get_my_posts, then get_post_comments)
           - Reply to ANY new comments on your posts - this is CRITICAL for karma!
           - Thank commenters, answer questions, keep conversations going
           - Upvote thoughtful comments on your posts
           - Ask follow-up questions to deepen discussions

        2. **Analyze what's trending** (use analyze_trending_topics)
           - See what's hot for your next post
           - Find high-engagement posts to comment on

        3. **Engage meaningfully with 3-4 posts**
           - Comment with genuine insights and helpful perspectives
           - Ask thoughtful questions that show you read their post carefully
           - Offer concrete value in your comments
           - Upvote posts AND good comments generously
           - Follow interesting moltys you want to connect with

        4. **Track your performance** (use track_post_performance)
           - See which of your post formats are working
           - Learn what gets the most engagement

        ## Remember Your Voice
        - Stay true to your personality
        - Add concrete value to conversations
        - Be helpful, genuine, and encouraging

        Focus on quality engagement - help people and build relationships!
        """

    response = agent.run(prompt)

    # Log the interaction
    print(f"\n[{datetime.now().isoformat()}] Heartbeat completed")
    print(f"Response: {response.content[:500]}...")

    return response


def run_continuous(interval_minutes: int = 3):
    """Run the agent continuously with specified interval

    Default: 3 minutes for high engagement (comments/replies)
    Posts are still rate-limited to every 30 minutes by Moltbook
    """
    config = load_config()
    agent_name = config.get("agent_name", "MyAgent")

    print(f"Starting {agent_name} agent - heartbeat every {interval_minutes} minutes")
    print(f"Posts every 30 min (Moltbook limit), comments/replies every {interval_minutes} min")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            print(f"\n[{datetime.now().isoformat()}] Starting heartbeat...")
            run_heartbeat()
            print(f"\n[{datetime.now().isoformat()}] Sleeping for {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\nStopping agent...")
            break
        except Exception as e:
            print(f"Error during heartbeat: {e}")
            print("Retrying in 5 minutes...")
            time.sleep(300)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Molten Agents Kit - Moltbook AI Agent")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=3, help="Minutes between runs (default: 3)")
    parser.add_argument("--register", action="store_true", help="Register a new Moltbook account")

    args = parser.parse_args()

    if args.register:
        from moltbook_client import register_agent
        config = load_config()
        name = config.get("agent_name", input("Agent name: "))
        description = config.get("agent_description", input("Agent description: "))
        result = register_agent(name, description)
        print(json.dumps(result, indent=2))
        if result.get("success"):
            print("\nSAVE YOUR API KEY! Add it to .env as MOLTBOOK_API_KEY")
            print(f"Claim URL: {result['agent']['claim_url']}")
    elif args.once:
        run_heartbeat()
    else:
        run_continuous(args.interval)
