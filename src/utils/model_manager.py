import os
import ssl

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from langchain_community.chat_models.azureml_endpoint import (
    AzureMLChatOnlineEndpoint,
    AzureMLEndpointApiType,
    CustomOpenAIChatContentFormatter,
)
from langchain_deepseek import ChatDeepSeek
from langchain_openai import AzureChatOpenAI


# LLM config
class ModelManager:
    """
    A class to manage different types of chat models, including OpenAI, Open Source VM,
    and Open Source API models. Selects correct endpoint and credential based on model type.
    """

    def __init__(self, model_type):
        current_directory = os.getcwd()
        env_path = os.path.join(current_directory, "..", ".env")
        load_dotenv(env_path)
        self.model_type = model_type

    def create_chat_model(self, model_name, temperature):
        if self.model_type == "openai":
            return self._create_openai_model(model_name, temperature)
        elif self.model_type == "deepseek":
            return self._create_deepseek_model(model_name, temperature)
        elif self.model_type == "opensource_vm":
            return self._create_opensource_model_vm(model_name, temperature)
        elif self.model_type == "opensource_api":
            return self._create_opensource_model_api(model_name, temperature)
        else:
            raise ValueError(
                "Invalid model type. Choose either 'openai' or 'opensource'."
            )

    def _create_openai_model(self, model_name, temperature):
        return AzureChatOpenAI(
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            azure_deployment=model_name,
            temperature=temperature
            if model_name not in ["o4-mini", "o3-mini", "o3", "o1"]
            else None,
            model=model_name,
        )

    def _create_deepseek_model(self, model_name, temperature):
        if model_name == "DeepSeek-R1-qcbar":
            return ChatDeepSeek(
                api_key=os.getenv("DEEPSEEK_R1_API_KEY"),
                api_base=os.getenv("DEEPSEEK_R1_ENDPOINT"),
                temperature=temperature,
                model=model_name,
            )
        elif model_name == "DeepSeek-V3-0324":
            return ChatDeepSeek(
                api_key=os.getenv("DEEPSEEK_V3_API_KEY"),
                api_base=os.getenv("DEEPSEEK_V3_ENDPOINT"),
                temperature=temperature,
                model=model_name,
            )
        else:
            raise ValueError(
                f"Unsupported model: {model_name}. Please choose a valid model."
            )

    def _create_opensource_model_vm(self, model_name, temperature):
        # This method handles open-source VM models
        ssl._create_default_https_context = ssl._create_unverified_context

        return AzureMLChatOnlineEndpoint(
            endpoint_url=os.getenv("AZURE_LLAMA_ENDPOINT"),
            endpoint_api_type=AzureMLEndpointApiType.dedicated,
            endpoint_api_key=os.getenv("AZURE_LLAMA_KEY"),
            content_formatter=CustomOpenAIChatContentFormatter(),
            model_kwargs={
                "max_tokens": 2000,
                "temperature": temperature,
                "model_name": model_name,
            },
        )

    def _create_opensource_model_api(self, model_name, temperature):
        # Determine the correct endpoint and key based on the model for API models only
        if model_name == "llama-8b":
            endpoint = os.getenv("AZURE_LLAMA_8B_ENDPOINT")
            api_key = os.getenv("AZURE_LLAMA_8B_KEY")
        elif model_name == "llama-405b":
            endpoint = os.getenv("AZURE_LLAMA_405B_ENDPOINT")
            api_key = os.getenv("AZURE_LLAMA_405B_KEY")
        elif model_name == "mistral-large":
            endpoint = os.getenv("AZURE_MISTRAL_LARGE_2_ENDPOINT")
            api_key = os.getenv("AZURE_MISTRAL_LARGE_2_KEY")
        elif model_name == "mistral-nemo":
            endpoint = os.getenv("AZURE_MISTRAL_NEMO_ENDPOINT")
            api_key = os.getenv("AZURE_MISTRAL_NEMO_KEY")
        else:
            raise ValueError(
                f"Unsupported model: {model_name}. Please choose a valid model."
            )

        return ChatCompletionsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key),
            temperature=temperature,
            # max_tokens=128000,
            model_name=model_name,
        )
