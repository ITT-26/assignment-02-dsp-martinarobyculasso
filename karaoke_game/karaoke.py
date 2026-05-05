import sounddevice as sd
import numpy as np
import time as t
import threading
import mido
from mido import MidiFile
import pyglet
from pyglet import window, shapes
import os
import sys
from scipy.signal import butter, lfilter


# == CONSTANS AND GLOBAL VARIABLES ==

# AUDIO ------

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024           # Number of audio frames per buffer
RATE = 44100                # Audio sampling rate (HZ)
CHANNELS = 1                # Mono audio
VOLUME_THRESHOLD = 0.08     # Minimum volume to consider as singing

# human voice frequency range
low_freq = 30       # Hz
high_freq = 3400    # Hz

# PYGLET ------

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 500

SCROLL_SPEED = 250  # pixels per second

PLAYER_X = 100  # fixed x position for player

# colors
GREEN = (72, 169, 166)
RED = (193, 102, 107)
WHITE = (228, 223, 218)
YELLOW = (212, 180, 131)
BACKGROUND = (67, 87, 173)

# calculate how long it takes for a note to travel from the right edge to the player's position
time_to_travel = (WINDOW_WIDTH - PLAYER_X) / SCROLL_SPEED

game_state = "start_screen" # "start_screen", "playing", "results_screen"
selected_song = None
game_time = 0.0        # elapsed time since song started
parsed_notes = []      # list of (start_time, duration, frequency) from parse_midi_file
active_notes = []      # objects currently on screen
next_note_index = 0    # tracks which note to spawn next
song_freq_min = low_freq
song_freq_max = high_freq

score = 0
total_frames = 0
accuracy = 0.0

freq_history = []

# path for assets (background, game objects, sprite)
assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
pyglet.resource.path = [assets_dir]
pyglet.resource.reindex()

# font
pyglet.font.add_file(os.path.join(assets_dir, 'Fredoka-VariableFont_wdth,wght.ttf'))

# game window
win = window.Window(WINDOW_WIDTH, WINDOW_HEIGHT, caption="Karaoke Game")
pyglet.gl.glClearColor(BACKGROUND[0]/255, BACKGROUND[1]/255, BACKGROUND[2]/255, 1)

# labels
# title
title_label = pyglet.text.Label(
    'Karaoke Game',
    font_name='Fredoka',
    font_size = 50,
    color = WHITE + (255,),
    x=WINDOW_WIDTH//2,
    y=WINDOW_HEIGHT//2 + 100,
    anchor_x='center',
    anchor_y='center'
)

# instructions
instructions_label_1 = pyglet.text.Label(
    'Press SPACE to start singing or P to listen to the song',
    font_name='Fredoka',
    font_size=18,
    color=WHITE + (255,),
    x=WINDOW_WIDTH//2,
    y=WINDOW_HEIGHT//2 - 80,
    anchor_x='center',
    anchor_y='center',
    multiline=True,
    width=600,
    align='center'
)

results_title = pyglet.text.Label(
    'Results',
    font_name='Fredoka', 
    font_size=50,
    color=WHITE + (255,),
    x=WINDOW_WIDTH//2, 
    y=WINDOW_HEIGHT//2 + 100,
    anchor_x='center', 
    anchor_y='center'
)

accuracy_label = pyglet.text.Label(
    '',  
    font_name='Fredoka', 
    font_size=30,
    color=YELLOW + (255,),
    x=WINDOW_WIDTH//2,
    y=WINDOW_HEIGHT//2,
    anchor_x='center',
    anchor_y='center'
)

restart_label = pyglet.text.Label(
    'Press R to play again or Q/ESC to quit',
    font_name='Fredoka', 
    font_size=18,
    color=WHITE + (255,),
    x=WINDOW_WIDTH//2, 
    y=WINDOW_HEIGHT//2 - 80,
    anchor_x='center', 
    anchor_y='center'
)

song_label = pyglet.text.Label(
    '',
    font_name='Fredoka', 
    font_size=30,
    color=YELLOW + (255,),
    x=WINDOW_WIDTH//2, 
    y=WINDOW_HEIGHT//2,
    anchor_x='center', 
    anchor_y='center'
)

# player
player_line = pyglet.shapes.Rectangle(
    x=PLAYER_X, y=0, 
    width=4, height=WINDOW_HEIGHT, 
    color=WHITE
)

penguin_img = pyglet.resource.image('penguin.png')
penguin_img.anchor_x = penguin_img.width // 2
penguin_img.anchor_y = penguin_img.height // 2
penguin_sprite = pyglet.sprite.Sprite(penguin_img, x=PLAYER_X, y=WINDOW_HEIGHT//2)
penguin_sprite.scale = 0.15

# == FUNCTIONS ==

# MIDI note to frequency conversion
def midi_to_freq(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))

# preprocess MIDI file to extract note timings and frequencies
def parse_midi_file(filename):
    midi = MidiFile(filename)
    elapsed_time = 0
    pending = {}
    notes = []

    for msg in midi:
        elapsed_time += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            pending[msg.note] = elapsed_time
        elif (msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0)) and msg.note in pending:
            start_time = pending.pop(msg.note)
            duration = elapsed_time - start_time
            frequency = midi_to_freq(msg.note)
            notes.append((start_time, duration, frequency))
    return notes

# map frequency to y pixel position using log
def freq_to_y(freq, screen_height):
    log_min = np.log2(song_freq_min)
    log_max = np.log2(song_freq_max)
    log_freq = np.log2(freq)
    return (log_freq - log_min) / (log_max - log_min) * screen_height

def detect_collision(note, player_y):
    # check if note is at the player line
    at_player = note.rectangle.x <= PLAYER_X <= note.rectangle.x + note.width
    # check if penguin is close enough vertically
    close_enough = abs(player_y - note.y) < 50  # 50 pixels tolerance
    return at_player and close_enough

def play_preview():
    preview_player.queue(preview_source)
    preview_player.play()

def stop_preview():
    preview_player.pause()

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = fs / 2
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

# audio callback - called automatically by sounddevice
def audio_callback(indata, frames, time, status):
    global game_state, freq_history

    if status:
        print(status)

    data = indata[:, 0]  # mono

    # filter out silence, avoid processing when no one is singing
    if np.max(np.abs(data)) < VOLUME_THRESHOLD:
        return
    
    if game_state != "playing":
        return

    # bandpass filter to isolate human voice frequencies
    filtered_data = lfilter(b, a, data)

    # hamming window to reduce spectral leakage
    windowed_data = filtered_data * hamming_window

    # compute FFT - fft.rfft returns complex numbers
    data_fft = np.fft.rfft(windowed_data)
    # find the magnitude at each frequency
    abs_data_fft = np.abs(data_fft)

    # find the index that corresponds to the highest value
    i = np.argmax(abs_data_fft)

    # find the dominant frequency using the previously calculated index
    freq_max = freq[i]

    # penguin_sprite.y = freq_to_y(freq_max, WINDOW_HEIGHT)
    # penguin_sprite.y = max(0, min(WINDOW_HEIGHT, penguin_sprite.y))

    # smooth the frequency using a rolling average
    freq_history.append(freq_max)
    if len(freq_history) > 5:
        freq_history.pop(0)
    smoothed_freq = np.mean(freq_history)

    # update penguin position based on smoothed frequency
    penguin_sprite.y = freq_to_y(smoothed_freq, WINDOW_HEIGHT)
    penguin_sprite.y = max(0, min(WINDOW_HEIGHT, penguin_sprite.y))

# == CLASSES ==

class Note:
    def __init__(self, start_time, duration, frequency):
        self.start_time = start_time
        self.duration = duration
        self.frequency = frequency
        self.y = freq_to_y(frequency, WINDOW_HEIGHT)
        self.width = duration * SCROLL_SPEED
        self.x = WINDOW_WIDTH
        self.color = RED
        self.rectangle = pyglet.shapes.Rectangle(self.x, self.y, self.width, 35, color=self.color)
   
    def draw(self):
        self.rectangle.draw()

    def update_pos(self, dt):
        self.rectangle.x -= SCROLL_SPEED * dt

# == ONE-TIME SETUP ==

# fft.rfftfreq(n, d) -> "Return the Discrete Fourier Transform sample frequencies" (docs)
# returns an array of evenly spaced frequencies from 0 Hz up to RATE/2, with steps of RATE/CHUNK_SIZE
freq = np.fft.rfftfreq(CHUNK_SIZE,1/RATE)

b, a = butter_bandpass(low_freq, high_freq, RATE)
hamming_window = np.hamming(CHUNK_SIZE)

# == MAIN PROGRAM ==

tracks_dir = os.path.join(os.path.dirname(__file__), 'tracks')

if len(sys.argv) < 2:
    print("\nUsage: python karaoke.py <song>")
    print("\nAvailable songs:")
    mid_files = [f for f in os.listdir(tracks_dir) if f.endswith('.mid')]
    for song in mid_files:
        print(f"  - {song}")
    print("\n")
    sys.exit(1)

selected_song = os.path.join(tracks_dir, sys.argv[1]) 

song_label.text = 'Selected song: ' + os.path.basename(selected_song)

preview_source = pyglet.media.load(os.path.join(tracks_dir, selected_song.replace('.mid', '.mp3')))
preview_player = pyglet.media.Player()

# parse the song immediately at startup
parsed_notes = parse_midi_file(selected_song)
song_freq_min = min(note[2] for note in parsed_notes) * 0.8
song_freq_max = max(note[2] for note in parsed_notes) * 1.2
parsed_notes.sort(key=lambda n: n[0])

# open audio input stream
stream = sd.InputStream(
    channels=1,
    samplerate=44100,
    blocksize=1024,
    callback=audio_callback,
    dtype='float32'
)

stream.start()

def update(dt):
    global game_state
    if game_state == "start_screen":
        pass
    elif game_state == "playing":
        # spawn new notes 
        global game_time, next_note_index, active_notes, score, total_frames, accuracy
        game_time += dt
        while next_note_index < len(parsed_notes):
            note_info = parsed_notes[next_note_index]
            if note_info[0] <= game_time + time_to_travel:  # spawn note 2 seconds before it should be sung
                active_notes.append(Note(*note_info))
                next_note_index += 1
            else:
                break
        for note in active_notes:
            note.update_pos(dt)
            if detect_collision(note, penguin_sprite.y):
                note.rectangle.color = GREEN
                score += 1
            else:
                note.rectangle.color = RED
        note_at_player = any(
            note.rectangle.x <= PLAYER_X <= note.rectangle.x + note.width
            for note in active_notes
        )
        if note_at_player:
            total_frames += 1
        active_notes = [n for n in active_notes if n.rectangle.x + n.width > 0]
        # check if song is finished
        song_finished = next_note_index >= len(parsed_notes) and len(active_notes) == 0
        if song_finished:
            if total_frames > 0:
                accuracy = (score / total_frames * 100)
                accuracy_label.text = f'Accuracy: {accuracy:.1f}%'
            else:
                accuracy = 0
            game_state = "results_screen"
    elif game_state == "results_screen":
        pass

@win.event
def on_key_press(key, modifiers):
    global game_state, selected_song, parsed_notes, game_time, next_note_index, active_notes, song_freq_max, song_freq_min, score, total_frames
    if key == pyglet.window.key.ESCAPE or key == pyglet.window.key.Q:
        pyglet.app.exit()
    if game_state == "start_screen":
        if key == pyglet.window.key.SPACE:
            stop_preview()
            game_state = "playing"
        elif key == pyglet.window.key.P:
            play_preview()
    if game_state == "results_screen":
        if key == pyglet.window.key.R:
            score = 0
            total_frames = 0
            game_time = 0
            next_note_index = 0
            active_notes = []
            accuracy_label.text = ''
            penguin_sprite.y = WINDOW_HEIGHT // 2
            freq_history.clear()
            game_state = "start_screen"
            
@win.event
def on_draw():
    global game_state
    win.clear()
    if game_state == "start_screen":
        title_label.draw()
        instructions_label_1.draw()
        song_label.draw()
    elif game_state == "playing":
        for note in active_notes:
            note.draw()
        player_line.draw()
        penguin_sprite.draw()
    elif game_state == "results_screen":
        results_title.draw()
        accuracy_label.draw()
        restart_label.draw()


pyglet.clock.schedule_interval(update, 1/60)  
pyglet.app.run()
stream.stop()