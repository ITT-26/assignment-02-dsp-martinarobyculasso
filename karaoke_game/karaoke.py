import sounddevice as sd
import numpy as np
import time as t
import threading
import mido
from mido import MidiFile
import pyglet
from pyglet import window, shapes
import os


# == CONSTANS AND GLOBAL VARIABLES ==

# AUDIO ------

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024           # Number of audio frames per buffer
RATE = 44100                # Audio sampling rate (HZ)
CHANNELS = 1                # Mono audio
VOLUME_THRESHOLD = 0.08     # Minimum volume to consider as singing

# human voice frequency range
low_freq = 150 #30       # Hz
high_freq = 1500 #3400    # Hz

SONGS = ['freude.mid', 'berge.mid']

# PYGLET ------
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 500

SCROLL_SPEED = 100  # pixels per second

PLAYER_X = 100  # fixed x position for player

GREEN = (72, 169, 166)
RED = (193, 102, 107)
WHITE = (228, 223, 218)
YELLOW = (212, 180, 131)
BACKGROUND = (67, 87, 173)

# calculate how long it takes for a note to travel from the right edge to the player's position
time_to_travel = (WINDOW_WIDTH - PLAYER_X) / SCROLL_SPEED

# variable to store the current note being sung and compare
song_note = None
current_note = None

game_state = "start_screen" # "start_screen", "singing", "results_screen"
selected_song = None
game_time = 0.0        # elapsed time since song started
parsed_notes = []      # list of (start_time, duration, frequency) from parse_midi_file
active_notes = []      # objects currently on screen
next_note_index = 0    # tracks which note to spawn next

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
    'Choose a song to start singing (number keys 1 or 2):',
    font_name='Fredoka',
    font_size=18,
    color=WHITE + (255,),
    x=WINDOW_WIDTH//2,
    y=WINDOW_HEIGHT//2 + 10,
    anchor_x='center',
    anchor_y='center',
    multiline=True,
    width=600,
    align='center'
)

test_label = pyglet.text.Label(
    'Test',
    font_name='Fredoka',
    font_size=30,
    color=WHITE + (255,),
    x=WINDOW_WIDTH//2,
    y=WINDOW_HEIGHT//2,
    anchor_x='center',
    anchor_y='center'
)

# buttons
btn1 = pyglet.shapes.Rectangle(
    x=WINDOW_WIDTH//2 - 150,
    y=WINDOW_HEIGHT//2 - 70,
    width=120,
    height=40,
    color=YELLOW
)
btn1_label = pyglet.text.Label(
    '[1] Freude', 
    font_name='Fredoka',
    font_size=16,
    color=WHITE + (255,),
    x=btn1.x + btn1.width//2,
    y=btn1.y + btn1.height//2,
    anchor_x='center',
    anchor_y='center'
)

btn2 = pyglet.shapes.Rectangle(
    x=WINDOW_WIDTH//2 + 30,
    y=WINDOW_HEIGHT//2 - 70,
    width=120,
    height=40,
    color=YELLOW
)
btn2_label = pyglet.text.Label(
    '[2] Berge', 
    font_name='Fredoka',
    font_size=16,
    color=WHITE + (255,),
    x=btn2.x + btn2.width//2,
    y=btn2.y + btn2.height//2,
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

# == ONE-TIME SETUP ==

# fft.rfftfreq(n, d) -> "Return the Discrete Fourier Transform sample frequencies" (docs)
# returns an array of evenly spaced frequencies from 0 Hz up to RATE/2, with steps of RATE/CHUNK_SIZE
freq = np.fft.rfftfreq(CHUNK_SIZE,1/RATE)

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

# audio callback - called automatically by sounddevice
def audio_callback(indata, frames, time, status):
    if status:
        print(status)

    data = indata[:, 0]  # mono

    # filter out silence, avoid processing when no one is singing
    if np.max(np.abs(data)) < VOLUME_THRESHOLD:
        return

    # compute FFT - fft.rfft returns complex numbers
    data_fft = np.fft.rfft(data)
    # find the magnitude at each frequency
    abs_data_fft = np.abs(data_fft)
    # eliminate frequencies outside the human voice range
    freq_human_voice = np.where((freq > low_freq) & (freq < high_freq), abs_data_fft, 0)
    # find the index that corresponds to the highest value
    i = np.argmax(freq_human_voice)
    # find the dominant frequency using the previously calculated index
    freq_max = freq[i]
    # compare the detected frequency with the current note from the MIDI file
    penguin_sprite.y = freq_to_y(freq_max, WINDOW_HEIGHT)
    if current_note is not None:
        if abs(freq_max - current_note) < 50:  # allow some tolerance
            print(f"Good job! Detected frequency: {freq_max:.1f} Hz matches the note {current_note:.1f} Hz")
        else:
            print(f"Keep trying! Detected frequency: {freq_max:.1f} Hz does not match the note {current_note:.1f} Hz")

# map frequency to y pixel position using log
def freq_to_y(freq, screen_height):
    log_min = np.log2(low_freq)
    log_max = np.log2(high_freq)
    log_freq = np.log2(freq)
    return (log_freq - log_min) / (log_max - log_min) * screen_height

# check if the player's y position is within a certain range of the note's y position
def detect_collision(note, player_y):
    pass
    # if abs(player_y - note.position) < 20:  # 20 pixels tolerance
    #     return True
    # return False

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

# == MAIN PROGRAM ==

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
        global game_time, next_note_index, active_notes
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
        active_notes = [n for n in active_notes if n.rectangle.x + n.width > 0]
    elif game_state == "results_screen":
        pass

@win.event
def on_key_press(key, modifiers):
    global game_state, selected_song, parsed_notes, game_time, next_note_index, active_notes
    if key == pyglet.window.key.ESCAPE or key == pyglet.window.key.Q:
        pyglet.app.exit()
    if game_state == "start_screen":
        if key == pyglet.window.key._1:
            selected_song = SONGS[0]
            game_state = "playing"
            parsed_notes = parse_midi_file(selected_song)
            parsed_notes.sort(key=lambda n: n[0]) 
            game_time = 0
            next_note_index = 0
            active_notes = []
        elif key == pyglet.window.key._2:
            selected_song = SONGS[1]
            game_state = "playing"
            parsed_notes = parse_midi_file(selected_song)
            parsed_notes.sort(key=lambda n: n[0]) 
            game_time = 0
            next_note_index = 0
            active_notes = []
    if game_state == "results_screen":
        if key == pyglet.window.key.R:
            game_state = "start_screen"
            
@win.event
def on_draw():
    global game_state
    win.clear()
    if game_state == "start_screen":
        title_label.draw()
        instructions_label_1.draw()
        btn1.draw()
        btn1_label.draw()
        btn2.draw()
        btn2_label.draw()
    elif game_state == "playing":
        for note in active_notes:
            note.draw()
        player_line.draw()
        penguin_sprite.draw()
    elif game_state == "results_screen":
        test_label.draw()


pyglet.clock.schedule_interval(update, 1/60)  # 60fps
pyglet.app.run()
stream.stop()