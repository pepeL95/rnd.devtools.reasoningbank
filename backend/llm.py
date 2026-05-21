"""Direct LangChain Gemini construction helpers."""

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


def gemini_chat_model(model: str = "gemini-2.5-flash", **kwargs: object):
    return ChatGoogleGenerativeAI(model=model, **kwargs)


def gemini_embeddings(model: str = "models/gemini-embedding-2", **kwargs: object):
    return GoogleGenerativeAIEmbeddings(model=model, **kwargs)
