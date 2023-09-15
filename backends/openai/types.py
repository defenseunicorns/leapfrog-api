from pydantic import BaseModel
import typing


##########
# GENERIC
##########
class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


##########
# COMPLETION
##########
class CompletionRequest(BaseModel):
    model: str
    prompt: str | list[int]
    stream: bool | None = False
    max_new_tokens: int | None = 16
    temperature: float | None = 1.0


class CompletionChoice(BaseModel):
    index: int
    text: str
    logprobs: object | None
    finish_reason: str


class CompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[CompletionChoice]
    # usage: Usage


##########
# CHAT
##########


class ChatFunction(BaseModel):
    name: str
    parameters: typing.Dict[str, str]
    description: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatDelta(BaseModel):
    role: str
    content: str | None = ""


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    functions: list[ChatFunction] | None = None
    temperature: float | None = 1.0
    stream: bool | None = False
    stop: str | None = None
    max_tokens: int | None = 128


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatStreamChoice(BaseModel):
    index: int
    delta: ChatDelta
    finish_reason: str | None = ""


# TODO @JPERRY do we want two distinct response types for stream vs not-stream or do we want the choices to be unioned?
class ChatCompletionResponse(BaseModel):
    """https://platform.openai.com/docs/api-reference/chat/object"""

    id: str
    object: str
    created: int
    model: str
    choices: list[ChatChoice] | list[
        ChatStreamChoice
    ]  # TODO: @JPERRY look into this more, difference between streaming and not streaming
    usage: Usage | None


class CreateEmbeddingRequest(BaseModel):
    model: str
    input: str | list[str]
    user: str


class CreateEmbeddingResponse(BaseModel):
    index: int
    object: str
    embedding: list[float]


# yes I know, this is a pure API response class for matching OpenAI
class ModelResponseModel(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "leapfrogai"


class ModelResponse(BaseModel):
    object: str = "list"
    data: list[ModelResponseModel] = []
