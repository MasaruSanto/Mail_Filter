
"""
================================================================================
PC音声 文字起こしツール
================================================================================
 
【概要】
PCで再生中の音声(システム音声/スピーカー出力)を録音し、
日本語で文字起こしして画面に表示するツール。
 
--------------------------------------------------------------------------------
【処理の流れ】
--------------------------------------------------------------------------------
1. Whisperモデル(音声認識AI)をメモリにロードする
2. [T]キーが押されるのを待機する
3. [T]キーで録音開始 → もう一度[T]で録音停止
4. 録音した音声をWhisperに渡して日本語テキストに変換する
5. 結果を画面に表示する
6. 2に戻って繰り返す ([Ctrl+C]で終了)
 
--------------------------------------------------------------------------------
【各処理が何をしているか】
--------------------------------------------------------------------------------
■ get_loopback_device
  スピーカーから出ている音(ループバック)を録音できるデバイスを探す。
  通常のマイク録音とは違い、これにより「PCで鳴っている音そのもの」を拾える。
  Windowsの音声API(WASAPI)を使用。
 
■ record_toggle
  実際の録音処理。
  - デバイスを開いて音声データを少しずつ読み取り frames に溜める
  - キー押しっぱなしの待機ループは、1回の押下を正しく扱うため(連続検知防止)
  - 録音後、ステレオならモノラルに平均化
  - int16 の数値を -1.0〜1.0 の float32 に正規化
  - Whisperが要求する16kHzにリサンプリングして返す
 
■ メインループ
  キー待機 → 録音 → whisper.transcribe で文字起こし → 表示、を繰り返す。
 
--------------------------------------------------------------------------------
【設定の意味】
--------------------------------------------------------------------------------
WHISPER_MODEL   = "small"
  音声認識モデルのサイズ。tiny < base < small < medium < large の順に
  精度が上がるが、重く遅くなる。CPUなら small か medium が現実的。

WHISPER_DEVICE  = "cpu"
  推論を実行するデバイス。GPUがあれば "cuda" にすると高速。

WHISPER_COMPUTE = "int8"
  モデルの量子化方式。int8 は精度をわずかに犠牲にしてメモリと速度を
  改善する、CPU向けの軽い設定。
 
TRIGGER_KEY     = "t"
  録音の開始・停止に使うキー。
 
TARGET_SR       = 16000
  目標サンプリングレート(16kHz)。Whisperは16kHz前提のため、
  録音時のレートが違えばこの値に変換する。
 
【transcribe の引数】
  language="ja"            : 日本語と明示(自動判定を省き精度・速度を安定化)
  beam_size=5              : 候補を複数探索して精度を上げる(大きいほど遅い)
  vad_filter=True          : 無音部分を検出して除外する
  min_silence_duration_ms  : 300ms以上の無音を区切りとみなす
  initial_prompt           : 文脈を与えて認識傾向を誘導するヒント
================================================================================
"""
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import time
import keyboard
import pyaudiowpatch as pyaudio
import numpy as np
from faster_whisper import WhisperModel
from scipy.signal import resample_poly

# ==== 設定 ====
WHISPER_MODEL: str = "small"
WHISPER_DEVICE: str = "cpu"
WHISPER_COMPUTE: str = "int8"
TRIGGER_KEY: str = "t"
TARGET_SR: int = 16000


def get_loopback_device(p: pyaudio.PyAudio) -> dict:
  wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
  default_speaker = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
  if not default_speaker.get("isLoopbackDevice", False):
    for i in range(p.get_device_count()):
      info = p.get_device_info_by_index(i)
      if default_speaker["name"] in info["name"] and info.get("isLoopbackDevice", False):
        return info
    raise RuntimeError("loopbackデバイスが見つかりません")
  return default_speaker


def record_toggle(key: str = TRIGGER_KEY) -> np.ndarray:
  """[T]で録音開始、もう一度[T]で停止"""
  p = pyaudio.PyAudio()
  try:
    device = get_loopback_device(p)
    rate = int(device["defaultSampleRate"])
    channels = device["maxInputChannels"]
    print(f"録音中... もう一度[{key}]キーを押すと停止")
    stream = p.open(
      format=pyaudio.paInt16,
      channels=channels,
      rate=rate,
      input=True,
      input_device_index=device["index"],
      frames_per_buffer=1024,
    )
    while keyboard.is_pressed(key):
      time.sleep(0.01)
    frames: list[bytes] = []

    while not keyboard.is_pressed(key):
      frames.append(stream.read(1024, exception_on_overflow=False))

    while keyboard.is_pressed(key):
      time.sleep(0.01)

    stream.stop_stream()
    stream.close()
    if not frames:
      return np.zeros(0, dtype=np.float32)

    pcm = np.frombuffer(b"".join(frames), dtype=np.int16)
    if channels > 1:
      pcm = pcm.reshape(-1, channels).mean(axis=1)
    audio = pcm.astype(np.float32) / 32768.0

    if rate != TARGET_SR:
      audio = resample_poly(audio, TARGET_SR, rate).astype(np.float32)
    return audio

  finally:
    p.terminate()


# ==== 初期化 ====

print("Whisperモデルをロード中...")

whisper = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
print("ロード完了")
print(f"\n[{TRIGGER_KEY}]キーを押すと、PC内音声を録音します。終了は Ctrl+C。")
while True:
  try:
    keyboard.wait(TRIGGER_KEY)
    audio: np.ndarray = record_toggle()
    segments, _ = whisper.transcribe(
      audio,
      language="ja",
      beam_size=5,
      vad_filter=True,
      vad_parameters={"min_silence_duration_ms": 300},
      initial_prompt="以下は日本語の発話です。",
    )
    text: str = "".join(s.text for s in segments).strip()
    if not text:
      print("音声を認識できませんでした")
      continue
    print("PC音声:", text)
  except KeyboardInterrupt:
    print("\n終了します")
    break
  except Exception as e:
    print(f"エラー: {e}")