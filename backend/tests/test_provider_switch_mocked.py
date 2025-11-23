import sys
from unittest.mock import MagicMock, patch

# Mock openai module BEFORE importing services that might use it
mock_openai = MagicMock()
sys.modules["openai"] = mock_openai

import pytest
from backend.app.services import llm_service, tts_service, stt_service

@pytest.mark.anyio
async def test_llm_provider_switch_azure():
    # Setup the mock for AsyncAzureOpenAI
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create = MagicMock() # AsyncMock not needed if we mock awaitable?
    # Actually, create needs to be awaitable.
    async def async_create(*args, **kwargs):
        return MagicMock(choices=[MagicMock(message=MagicMock(content="Azure Response"))])
    mock_client_instance.chat.completions.create.side_effect = async_create
    
    mock_openai.AsyncAzureOpenAI.return_value = mock_client_instance

    with patch("backend.app.services.llm_service.get_settings") as mock_settings:
        mock_settings.return_value.llm_provider = "azure"
        mock_settings.return_value.azure_openai_api_key = "fake-key"
        mock_settings.return_value.azure_openai_endpoint = "https://fake.azure.com"
        mock_settings.return_value.azure_deployment_name = "gpt-4o-azure"
        
        response = await llm_service.answer_user_question("test")
        
        assert "Azure Response" in response
        mock_openai.AsyncAzureOpenAI.assert_called_once()
        
        # Verify args
        call_kwargs = mock_client_instance.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-azure"

@pytest.mark.anyio
async def test_tts_provider_switch_azure():
    mock_openai.AsyncAzureOpenAI.reset_mock()
    # Setup mock
    mock_client_instance = MagicMock()
    mock_stream = MagicMock()
    async def async_stream_to_file(path):
        pass
    mock_stream.stream_to_file.side_effect = async_stream_to_file
    
    mock_context = MagicMock()
    async def async_enter():
        return mock_stream
    async def async_exit(*args):
        pass
    mock_context.__aenter__ = async_enter
    mock_context.__aexit__ = async_exit
    
    mock_client_instance.audio.speech.with_streaming_response.create.return_value = mock_context
    mock_openai.AsyncAzureOpenAI.return_value = mock_client_instance

    with patch("backend.app.services.tts_service.get_settings") as mock_settings:
        mock_settings.return_value.tts_provider = "azure"
        mock_settings.return_value.azure_openai_api_key = "fake-key"
        mock_settings.return_value.azure_openai_endpoint = "https://fake.azure.com"
        
        path = await tts_service.generate_tts_and_upload("test text", None)
        
        assert path.endswith(".mp3")
        mock_openai.AsyncAzureOpenAI.assert_called_once()

@pytest.mark.anyio
async def test_stt_provider_switch_azure():
    mock_openai.AsyncAzureOpenAI.reset_mock()
    # Setup mock
    mock_client_instance = MagicMock()
    async def async_transcribe(*args, **kwargs):
        return MagicMock(text="Azure Transcript")
    mock_client_instance.audio.transcriptions.create.side_effect = async_transcribe
    
    mock_openai.AsyncAzureOpenAI.return_value = mock_client_instance

    with patch("backend.app.services.stt_service.get_settings") as mock_settings:
        mock_settings.return_value.stt_provider = "azure"
        mock_settings.return_value.azure_openai_api_key = "fake-key"
        mock_settings.return_value.azure_openai_endpoint = "https://fake.azure.com"
        
        with patch("builtins.open", new_callable=MagicMock):
            with patch("os.path.exists", return_value=True):
                transcript = await stt_service.transcribe_audio("fake.mp3")
        
        assert transcript == "Azure Transcript"
        mock_openai.AsyncAzureOpenAI.assert_called_once()
