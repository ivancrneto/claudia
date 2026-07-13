"""FasterWhisperSTT — self-hosted PT-BR speech-to-text (faster-whisper / CTranslate2).

The model load and decode are left as a Phase-1 wiring TODO (heavy GPU dependency); the
adapter shape and lazy-load pattern are fixed so the pipeline can depend on it today and
swap the stub for this in deployment. Streaming partials land in Phase 3.
"""

from __future__ import annotations


class FasterWhisperSTT:
    name = "faster-whisper"

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "auto",
        compute_type: str = "int8",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # local import — optional heavy dep

            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        return self._model

    async def transcribe(self, audio: bytes, locale: str = "pt-BR") -> str:
        # TODO(phase-1): decode Opus/PCM to float32 PCM, run
        #   segments, _ = model.transcribe(pcm, language=locale.split("-")[0])
        # and join segment texts. Run in a thread executor (model is sync/CPU-GPU bound).
        raise NotImplementedError("Wire faster-whisper decoding in Phase 1 deployment")
