# Credits

## Karaoke Game (Ex. 1)

### Assets

**[Animal Pack - Kenney](https://kenney.nl/assets/animal-pack)**
- Used for: player sprite (penguin)
- License: Creative Commons CC0 (Public Domain)

**[Fredoka - Google Fonts](https://fonts.google.com/specimen/Fredoka)**
- Used for: UI font
- License: SIL Open Font License 1.1 (OFL)

**[Coolors](https://coolors.co/4357ad-48a9a6-e4dfda-d4b483-c1666b)**
- Used for: color palette selection

### References

**[mido — MIDI Objects for Python](https://mido.readthedocs.io)**
- Used for: reading and parsing MIDI files

**[MIDI Tuning Standard — Wikipedia](https://en.wikipedia.org/wiki/MIDI_tuning_standard)**
- Used for: formula to convert MIDI note numbers to frequencies: f = 440 * 2^((n - 69) / 12)

**[Voice Frequency — Wikipedia](https://en.wikipedia.org/wiki/Voice_frequency)**
- Used for: determining realistic frequency ranges for human voice filtering

**[NumPy Documentation](https://numpy.org/doc/stable/)**
- Used for: FFT computation (`np.fft.rfft`, `np.fft.rfftfreq`), array operations, Hamming window

**[Pyglet Media Documentation](https://pyglet.readthedocs.io/en/latest/programming_guide/media.html)**
- Used for: MP3 audio playback (song preview feature)

**[SciPy Signal Documentation](https://docs.scipy.org/doc/scipy/reference/signal.html)**
- Used for: Butterworth bandpass filter (`scipy.signal.butter`, `scipy.signal.lfilter`)

### Code
- Code structure for audio capture and FFT-based frequency detection based on sample code provided by the Interactive Techniques and Technologies course (ITT), Universität Regensburg.
- [pyglet documentation](https://pyglet.org) used as reference for game loop, sprites, window, and text rendering.
- Claude (Anthropic) used for guided learning and code assistance. See info.txt for details.

---

## Whistle Input (Ex. 2)

### Assets

**[Fredoka - Google Fonts](https://fonts.google.com/specimen/Fredoka)**
- Used for: UI font
- License: SIL Open Font License 1.1 (OFL)

**[Coolors](https://coolors.co/4357ad-48a9a6-e4dfda-d4b483-c1666b)**
- Used for: color palette selection

### References

**[NumPy Documentation](https://numpy.org/doc/stable/)**
- Used for: FFT computation (`np.fft.rfft`, `np.fft.rfftfreq`), array operations, Hamming window

**[SciPy Signal Documentation](https://docs.scipy.org/doc/scipy/reference/signal.html)**
- Used for: Butterworth bandpass filter (`scipy.signal.butter`, `scipy.signal.lfilter`)

**[pynput Documentation](https://pynput.readthedocs.io/en/latest/)**
- Used for: triggering programmatic arrow key presses system-wide

### Code
- Code structure for audio capture and FFT-based frequency detection based on sample code provided by the Interactive Techniques and Technologies course (ITT), Universität Regensburg.
- [pyglet documentation](https://pyglet.org) used as reference for window, shapes, and text rendering.
- Claude (Anthropic) used for guided learning and code assistance. See info.txt for details.