[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/B3oR_XLF)

# Digital Signal Processing

---

Assignment 2 for the Interactive Techniques and Technologies course (ITT), Universität Regensburg.

Author: Martina Roby Culasso

## Exercise 1 — Karaoke Game

A karaoke game built with pyglet that captures microphone input, detects the dominant frequency in real time using FFT, and uses it to control a penguin sprite that must hit scrolling notes parsed from a MIDI file.

## Exercise 2 — Whistle Input

a) A pyglet app displaying a stack of rectangles, one of which is visually selected. Whistling upwards moves the selection up, whistling downwards moves it down. Chirp direction is detected by analyzing the frequency trend of the whistle using FFT.

b) A headless script that detects upward and downward whistle chirps and triggers system-wide arrow key presses using pynput, allowing navigation of arbitrary GUI menus by whistling.

---
Each folder contains an `info.txt` file with a description of the files and relevant notes.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## How to run

**Exercise 1 — Karaoke Game:**
```bash
cd karaoke
python karaoke.py <song.mid>
```
> Songs are located in the `tracks/` folder. Example: `python karaoke.py berge.mid`

**Exercise 2a — Whistle Input (pyglet):**
```bash
cd whistle_input
python whistle-input-pyglet.py
```

**Exercise 2b — Whistle Input (pynput):**
```bash
cd whistle_input
python whistle-input-pynput.py
```
> Run this script in the background, then switch focus to any GUI application and whistle to navigate.