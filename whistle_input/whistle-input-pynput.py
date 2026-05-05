import sounddevice as sd
import numpy as np
from scipy.signal import butter, lfilter
import os
from pynput.keyboard import Controller, Key

# PYNPUT related ==

keyboard = Controller()

# MIC INPUT & PROCESSING related ==

CHUNK_SIZE = 1024           # number of audio frames per buffer
RATE = 44100                # audio sampling rate (HZ)
CHANNELS = 1                # mono audio
VOLUME_THRESHOLD = 0.1     # minimum volume to consider as whistling

# whistling frequency range - tested with a real whistle
low_freq = 800      # Hz
high_freq = 2500    # Hz

was_whistling = False
freq_window = []  

MIN_SAMPLES = 10
MIN_DIFF = 115

# FUNCTIONS ==

def butter_bandpass(lowcut, highcut, fs, order=5):
    from scipy.signal import butter
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def move_up():
    keyboard.press(Key.up)
    keyboard.release(Key.up)

def move_down():
    keyboard.press(Key.down)
    keyboard.release(Key.down)

def audio_callback(indata, frames, time, status):
    global was_whistling, freq_window

    if status:
        print(status)
    
    data = indata[:, 0]  # get the mono audio data

    is_loud = np.max(np.abs(data)) > VOLUME_THRESHOLD
    # print(f"is_loud: {is_loud}, max: {np.max(np.abs(data)):.4f}")

    if is_loud:
        # bandpass filter the audio to focus on the whistling frequencies
        filtered_data = lfilter(b, a, data)

        # apply a Hamming window to reduce spectral leakage
        windowed_data = filtered_data * hamming_window

         # compute FFT - fft.rfft returns complex numbers
        data_fft = np.fft.rfft(windowed_data)

        # find the magnitude at each frequency
        abs_data_fft = np.abs(data_fft)

        # find the index that corresponds to the highest value
        i = np.argmax(abs_data_fft)

        # find the dominant frequency using the previously calculated index
        freq_max = freq[i]

        freq_window.append(freq_max)

        was_whistling = True
    else:
        if was_whistling:
            #print(f"Whistle ended! Samples collected: {len(freq_window)}")
            if len(freq_window) >= MIN_SAMPLES:
                half = len(freq_window) // 2
                first_half = np.mean(freq_window[:half])
                second_half = np.mean(freq_window[half:])
                diff = second_half - first_half
                # print(f"first_half mean: {first_half:.1f}, second_half mean: {second_half:.1f}, diff: {diff:.1f}")
                if diff > MIN_DIFF:
                    move_up()
                elif diff < -MIN_DIFF:
                    move_down()
            freq_window.clear()
        was_whistling = False

# ONE-TIME ==

# fft.rfftfreq(n, d) -> "Return the Discrete Fourier Transform sample frequencies" (docs)
# returns an array of evenly spaced frequencies from 0 Hz up to RATE/2, with steps of RATE/CHUNK_SIZE
freq = np.fft.rfftfreq(CHUNK_SIZE,1/RATE)

b, a = butter_bandpass(low_freq, high_freq, RATE)
hamming_window = np.hamming(CHUNK_SIZE)

# ==

# open audio input stream
stream = sd.InputStream(
    channels=1,
    samplerate=44100,
    blocksize=1024,
    callback=audio_callback,
    dtype='float32'
)

stream.start()

print("Whistle to navigate! (Press ENTER to stop)")
input()
stream.stop()
