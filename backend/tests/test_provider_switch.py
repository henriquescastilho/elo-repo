import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from backend.app.services import llm_service, tts_service, stt_service

@pytest.mark.anyio
async def test_llm_provider_switch_azure():
    with patch("backend.app.services.llm_service.get_settings") as mock_settings:
        mock_settings.return_value.llm_provider = "azure"
        mock_settings.return_value.azure_openai_api_key = "fake-key"
        mock_settings.return_value.azure_openai_endpoint = "https://fake.azure.com"
        mock_settings.return_value.azure_deployment_name = "gpt-4o-azure"
        
        with patch("openai.AsyncAzureOpenAI") as mock_azure:
            mock_instance = mock_azure.return_value
            mock_instance.chat.completions.create = AsyncMock()
            mock_instance.chat.completions.create.return_value.choices = [
                MagicMock(message=MagicMock(content="Azure Response"))
            ]
            
            response = await llm_service.answer_user_question("test")
            
            assert "Azure Response" in response
            mock_azure.assert_called_once()
            # Verify correct model/deployment was used
            call_kwargs = mock_instance.chat.completions.create.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o-azure"

@pytest.mark.anyio
async def test_tts_provider_switch_azure():
    with patch("backend.app.services.tts_service.get_settings") as mock_settings:
        mock_settings.return_value.tts_provider = "azure"
        mock_settings.return_value.azure_openai_api_key = "fake-key"
        mock_settings.return_value.azure_openai_endpoint = "https://fake.azure.com"
        
        with patch("openai.AsyncAzureOpenAI") as mock_azure:
            mock_instance = mock_azure.return_value
            mock_stream = AsyncMock()
            mock_stream.stream_to_file = AsyncMock()
            
            # Mock the context manager for with_streaming_response.create
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_stream
            mock_instance.audio.speech.with_streaming_response.create.return_value = mock_context
            
            path = await tts_service.generate_tts_and_upload("test text", None)
            
            assert path.endswith(".mp3")
            mock_azure.assert_called_once()

@pytest.mark.anyio
async def test_stt_provider_switch_azure():
    with patch("backend.app.services.stt_service.get_settings") as mock_settings:
        mock_settings.return_value.stt_provider = "azure"
        mock_settings.return_value.azure_openai_api_key = "fake-key"
        mock_settings.return_value.azure_openai_endpoint = "https://fake.azure.com"
        
        with patch("openai.AsyncAzureOpenAI") as mock_azure:
            mock_instance = mock_azure.return_value
            mock_instance.audio.transcriptions.create = AsyncMock()
            mock_instance.audio.transcriptions.create.return_value.text = "Azure Transcript"
            
            with patch("builtins.open", new_callable=MagicMock):
                with patch("os.path.exists", return_value=True):
                    transcript = await stt_service.transcribe_audio("fake.mp3")
            
            assert transcript == "Azure Transcript"
            mock_azure.assert_called_once()
