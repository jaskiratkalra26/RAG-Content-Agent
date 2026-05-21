"""Prompt templates for generation."""

BLOG_PROMPT = """You are an expert content writer. Write a comprehensive blog post of approximately 1500-2000 words on the provided topic.

Use ONLY the provided context. If the context does not contain the answer, say so. Do not hallucinate or make up information.
Maintain a professional article style, use structured headings, provide detailed explanations, and include examples where relevant.

Topic:
{input}

Context:
{context}

Blog Post:
"""

TWEET_PROMPT = """You are a social media expert. Write an engaging, concise tweet about the topic using the provided context.
The tweet must be under 150 characters and focused on AI and search.

Use ONLY the provided context. Do not hallucinate.

Topic:
{input}

Context:
{context}

Tweet:
"""

LINKEDIN_PROMPT = """You are a thought leader in marketing and tech. Write a professional LinkedIn post targeted at founders and a marketing audience.
Use concise paragraphs and a thought leadership style.

Use ONLY the provided context. Do not hallucinate.

Topic:
{input}

Context:
{context}

LinkedIn Post:
"""
