# -- coding: utf-8 --

import asyncio
import websockets
import json
import base64
import time
import logging

from typing import Optional, Callable, Dict, Any, Awaitable
from enum import Enum

# Setup logger for this module
logger = logging.getLogger(__name__)

class TurnDetectionMode(Enum):
    SERVER_VAD = "server_vad"
    MANUAL = "manual"

class OmniRealtimeClient:
    """
    A demo client for interacting with the Omni Realtime API.

    This class provides methods to connect to the Realtime API, send text and audio data,
    handle responses, and manage the WebSocket connection.

    Attributes:
        base_url (str):
            The base URL for the Realtime API.
        api_key (str):
            The API key for authentication.
        model (str):
            Omni model to use for chat.
        voice (str):
            The voice to use for audio output.
        turn_detection_mode (TurnDetectionMode):
            The mode for turn detection.
        on_text_delta (Callable[[str], Awaitable[None]]):
            Callback for text delta events.
            Takes in a string and returns an awaitable.
        on_audio_delta (Callable[[bytes], Awaitable[None]]):
            Callback for audio delta events.
            Takes in bytes and returns an awaitable.
        on_input_transcript (Callable[[str], Awaitable[None]]):
            Callback for input transcript events.
            Takes in a string and returns an awaitable.
        on_interrupt (Callable[[], Awaitable[None]]):
            Callback for user interrupt events, should be used to stop audio playback.
        on_output_transcript (Callable[[str], Awaitable[None]]):
            Callback for output transcript events.
            Takes in a string and returns an awaitable.
        extra_event_handlers (Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]]):
            Additional event handlers.
            Is a mapping of event names to functions that process the event payload.
    """
    def __init__(
        self,
        base_url,
        api_key: str,
        model: str = "",
        voice: str = "Chelsie",
        turn_detection_mode: TurnDetectionMode = TurnDetectionMode.SERVER_VAD,
        on_text_delta: Optional[Callable[[str], Awaitable[None]]] = None,
        on_audio_delta: Optional[Callable[[bytes], Awaitable[None]]] = None,
        on_interrupt: Optional[Callable[[], Awaitable[None]]] = None,
        on_input_transcript: Optional[Callable[[str], Awaitable[None]]] = None,
        on_output_transcript: Optional[Callable[[str], Awaitable[None]]] = None,
        on_connection_error: Optional[Callable[[], Awaitable[None]]] = None,
        on_response_done: Optional[Callable[[], Awaitable[None]]] = None,
        extra_event_handlers: Optional[Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]]] = None
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.ws = None
        self.on_text_delta = on_text_delta
        self.on_audio_delta = on_audio_delta
        self.on_interrupt = on_interrupt
        self.on_input_transcript = on_input_transcript
        self.on_output_transcript = on_output_transcript
        self.turn_detection_mode = turn_detection_mode
        self.handle_connection_error = on_connection_error
        self.on_response_done = on_response_done
        self.extra_event_handlers = extra_event_handlers or {}

        # Track current response state
        self._current_response_id = None
        self._current_item_id = None
        self._is_responding = False
        # Track printing state for input and output transcripts
        self._is_first_chunk = False
        self._print_input_transcript = False
        self._output_transcript_buffer = ""
        self.native_audio = ["text", "audio"]

    async def connect(self, instructions: str, native_audio=True) -> None:
        """Establish WebSocket connection with the Realtime API."""
        url = f"{self.base_url}?model={self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        } if "qwen" in self.model else {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        self.ws = await websockets.connect(url, additional_headers=headers)

        # Set up default session configuration
        if self.turn_detection_mode == TurnDetectionMode.MANUAL:
            raise NotImplementedError("Manual turn detection is not supported")
            # await self.update_session({
            #     "modalities": ["text", "audio"],
            #     "voice": self.voice,
            #     "input_audio_format": "pcm16",
            #     "output_audio_format": "pcm16",
            #     "input_audio_transcription": {
            #         "model": "gummy-realtime-v1"
            #     },
            #     "turn_detection" : None
            # })
        elif self.turn_detection_mode == TurnDetectionMode.SERVER_VAD:
            self.native_audio = ["text", "audio"] if native_audio else ["text"]
            await self.update_session({
                "instructions": instructions,
                "modalities": self.native_audio ,
                "voice": self.voice if "qwen" in self.model else "sage",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "gummy-realtime-v1" if "qwen" in self.model else "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.4,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "temperature": 0.3 if "qwen" in self.model else 0.7,
                "speed": 1. # OpenAI Only
            })
        else:
            raise ValueError(f"Invalid turn detection mode: {self.turn_detection_mode}")

    async def send_event(self, event) -> None:
        event['event_id'] = "event_" + str(int(time.time() * 1000))
        if self.ws:
            await self.ws.send(json.dumps(event))

    async def update_session(self, config: Dict[str, Any]) -> None:
        """Update session configuration."""
        event = {
            "type": "session.update",
            "session": config
        }
        await self.send_event(event)

    async def stream_audio(self, audio_chunk: bytes) -> None:
        """Stream raw audio data to the API."""
        # only support 16bit 16kHz mono pcm
        audio_b64 = base64.b64encode(audio_chunk).decode()

        append_event = {
            "type": "input_audio_buffer.append",
            "audio": audio_b64
        }
        await self.send_event(append_event)

    async def stream_image(self, image_b64: str) -> None:
        """Stream raw image data to the API."""
        append_event = {
            "type": "input_image_buffer.append",
            "image": image_b64
        }
        await self.send_event(append_event)

    async def create_response(self, instructions: str) -> None:
        """Request a response from the API. Needed when using manual mode."""
        event = {
            "type": "response.create",
            "response": {
                "instructions": instructions,
                "modalities": self.native_audio
            }
        }
        logger.info(f"Creating response: {event}")
        await self.send_event(event)

    async def cancel_response(self) -> None:
        """Cancel the current response."""
        event = {
            "type": "response.cancel"
        }
        await self.send_event(event)

    async def handle_interruption(self):
        """Handle user interruption of the current response."""
        if not self._is_responding:
            return

        logger.info("Handling interruption")

        # 1. Cancel the current response
        if self._current_response_id:
            await self.cancel_response()

        self._is_responding = False
        self._current_response_id = None
        self._current_item_id = None

    async def handle_messages(self) -> None:
        try:
            if not self.ws:
                logger.error("WebSocket connection is not established")
                return
                
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type")
                
                # if event_type not in ["response.audio.delta", "response.audio_transcript.delta"]:
                #     logger.debug(f"Received event: {event}")
                # else:
                #     logger.debug(f"Event type: {event_type}")

                if event_type == "error":
                    logger.error(f"API Error: {event['error']}")
                    continue
                elif event_type == "response.created":
                    self._current_response_id = event.get("response", {}).get("id")
                    self._is_responding = True
                    self._is_first_chunk = True
                elif event_type == "response.output_item.added":
                    self._current_item_id = event.get("item", {}).get("id")
                elif event_type == "response.done":
                    self._is_responding = False
                    self._current_response_id = None
                    self._current_item_id = None
                    if self.on_response_done:
                        await self.on_response_done()
                # Handle interruptions
                elif event_type == "input_audio_buffer.speech_started":
                    logger.info("Speech detected")
                    if self._is_responding:
                        logger.info("Handling interruption")
                        await self.handle_interruption()
                    if self.on_interrupt:
                        logger.info("Handling on_interrupt, stop playback")
                        await self.on_interrupt()
                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.info("Speech ended")
                # Handle normal response events
                elif event_type == "response.text.delta":
                    if self.on_text_delta:
                        await self.on_text_delta(event["delta"])
                elif event_type == "response.audio.delta":
                    if self.on_audio_delta:
                        audio_bytes = base64.b64decode(event["delta"])
                        await self.on_audio_delta(audio_bytes)
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    if self.on_input_transcript:
                        await self.on_input_transcript(transcript)
                        self._print_input_transcript = True
                elif event_type == "response.audio_transcript.delta":
                    if self.on_output_transcript:
                        delta = event.get("delta", "")
                        if not self._print_input_transcript:
                            self._output_transcript_buffer += delta
                        else:
                            # if self._output_transcript_buffer:
                            #     logger.info(f"{self._output_transcript_buffer} is_first_chunk: True")
                            #     await self.on_output_transcript(self._output_transcript_buffer, self._is_first_chunk)
                            #     self._is_first_chunk = False
                            #     self._output_transcript_buffer = ""
                            await self.on_output_transcript(delta)
                            self._is_first_chunk = False
                elif event_type == "response.audio_transcript.done":
                    self._print_input_transcript = False
                elif event_type in self.extra_event_handlers:
                    await self.extra_event_handlers[event_type](event)

        except websockets.exceptions.ConnectionClosedOK:
            logger.info("Connection closed as expected")
        except websockets.exceptions.ConnectionClosedError:
            if self.handle_connection_error:
                await self.handle_connection_error()
        except asyncio.TimeoutError:
            if self.ws:
                await self.ws.close()
            if self.handle_connection_error:
                await self.handle_connection_error()
        except Exception as e:
            logger.error(f"Error in message handling: {str(e)}")
            raise e

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self.ws:
            try:
                # 尝试关闭websocket连接
                await self.ws.close()
            except websockets.exceptions.ConnectionClosedOK:
                logger.warning("OmniRealtimeClient: WebSocket connection already closed (OK).")
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(f"OmniRealtimeClient: WebSocket connection closed with error: {e}")
            except Exception as e:
                logger.error(f"OmniRealtimeClient: Error closing WebSocket connection: {e}")
            finally:
                self.ws = None
