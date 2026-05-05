import pyglet
from pyglet import window, shapes
import sounddevice as sd
import numpy as np
from scipy.signal import butter, lfilter
import os

# PYGLET related ==

selected_rectangle = 0

# window settings
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 500

# palette colors
GREEN = (72, 169, 166)
RED = (193, 102, 107)
WHITE = (228, 223, 218)
YELLOW = (212, 180, 131)
BACKGROUND = (67, 87, 173)

# path for assets 
assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
pyglet.resource.path = [assets_dir]
pyglet.resource.reindex()

# font
pyglet.font.add_file(os.path.join(assets_dir, 'Fredoka-VariableFont_wdth,wght.ttf'))

# labels
visual_feedback = pyglet.text.Label(
    '', 
    font_name='Fredoka', 
    font_size=24, 
    x=100, 
    y=WINDOW_HEIGHT//2, 
    anchor_x='center', 
    anchor_y='center', 
    color=WHITE + (255,)
)

# MIC INPUT & PROCESSING related ==

CHUNK_SIZE = 1024           # number of audio frames per buffer
RATE = 44100                # audio sampling rate (HZ)
CHANNELS = 1                # mono audio
VOLUME_THRESHOLD = 0.15     # minimum volume to consider as whistling

# whistling frequency range - tested with a real whistle
low_freq = 800      # Hz
high_freq = 2500    # Hz

was_whistling = False
freq_window = []  
up_detected = False
down_detected = False
feedback_timer = 0

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
    global selected_rectangle, rectangles, up_detected
    if selected_rectangle < 4:
        selected_rectangle += 1
        rectangles[selected_rectangle].color = GREEN
        rectangles[selected_rectangle - 1].color = RED
        if not up_detected:
            up_detected = True

def move_down():
    global selected_rectangle, rectangles, down_detected
    if selected_rectangle > 0:
        selected_rectangle -= 1
        rectangles[selected_rectangle].color = GREEN
        rectangles[selected_rectangle + 1].color = RED
        if not down_detected:
            down_detected = True

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
            print(f"Whistle ended! Samples collected: {len(freq_window)}")
            if len(freq_window) >= MIN_SAMPLES:
                half = len(freq_window) // 2
                first_half = np.mean(freq_window[:half])
                second_half = np.mean(freq_window[half:])
                diff = second_half - first_half
                print(f"first_half mean: {first_half:.1f}, second_half mean: {second_half:.1f}, diff: {diff:.1f}")
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

# game window
win = window.Window(WINDOW_WIDTH, WINDOW_HEIGHT, caption="Whistle Input Test")
pyglet.gl.glClearColor(BACKGROUND[0]/255, BACKGROUND[1]/255, BACKGROUND[2]/255, 1)

# shapes
# shapes.Rectangle(x, y, width, height, color=(r, g, b))
rectangle_1 = shapes.Rectangle(WINDOW_WIDTH//2 - 100, 25, 200, 50, color=GREEN)
rectangle_2 = shapes.Rectangle(WINDOW_WIDTH//2 - 100, 125, 200, 50, color=RED)
rectangle_3 = shapes.Rectangle(WINDOW_WIDTH//2 - 100, 225, 200, 50, color=RED)
rectangle_4 = shapes.Rectangle(WINDOW_WIDTH//2 - 100, 325, 200, 50, color=RED)
rectangle_5 = shapes.Rectangle(WINDOW_WIDTH//2 - 100, 425, 200, 50, color=RED)

rectangles = [rectangle_1, rectangle_2, rectangle_3, rectangle_4, rectangle_5]

def update(dt):
    global up_detected, down_detected, feedback_timer
    if up_detected:
        visual_feedback.text = "Up!"
        feedback_timer = 0.5  # show for 0.5 seconds
        up_detected = False
    elif down_detected:
        visual_feedback.text = "Down!"
        feedback_timer = 0.5
        down_detected = False
    
    if feedback_timer > 0:
        feedback_timer -= dt
        if feedback_timer <= 0:
            visual_feedback.text = ''

@win.event
def on_key_press(key, modifiers):
    global selected_rectangle, rectangles
    if key == pyglet.window.key.ESCAPE or key == pyglet.window.key.Q:
        pyglet.app.exit()

@win.event
def on_draw():
    win.clear()
    for rect in rectangles:
        rect.draw()
    visual_feedback.draw()

# open audio input stream
stream = sd.InputStream(
    channels=1,
    samplerate=44100,
    blocksize=1024,
    callback=audio_callback,
    dtype='float32'
)

stream.start()

pyglet.clock.schedule_interval(update, 0.1)
pyglet.app.run()