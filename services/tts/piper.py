"""PiperTTS — self-hosted PT-BR text-to-speech (Piper).

Fast on CPU and streamable. The synth call is left as a Phase-1 wiring TODO; the adapter
shape is fixed so the pipeline depends on it now and swaps the stub for this in deployment.
Upgrade path: Coqui XTTS for higher fidelity.
"""

from __future__ import annotations


class PiperTTS:
    name = "piper"

    def __init__(self, model_path: str = "pt_BR-faber-medium.onnx") -> None:
        self.model_path = model_path
        self._voice = None

    def _load(self):
        if self._voice is None:
            from piper import PiperVoice  # local import — optional dependency

            self._voice = PiperVoice.load(self.model_path)
        return self._voice

    async def synthesize(self, text: str, voice: str = "pt_BR") -> bytes:
        # TODO(phase-1): run piper synthesis to WAV bytes in a thread executor:
        #   with io.BytesIO() as buf: self._load().synthesize(text, buf); return buf.getvalue()
        raise NotImplementedError("Wire Piper synthesis in Phase 1 deployment")
