def get_embedding_from_model(model, text: str):
    """Returns embedding vector from any supported model interface."""
    if hasattr(model, 'encode'):
        return model.encode(text)
    elif hasattr(model, 'get_embedding_and_usage'):
        return model.get_embedding_and_usage(text)[0]
    elif hasattr(model, 'get_embeddings'):
        return model.get_embeddings([text])[0]
    else:
        raise AttributeError(f"Unsupported embedding model type: {type(model)}")