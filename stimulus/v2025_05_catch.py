# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 18:38:52 2025

Goal: Have him switch back to "detection strategy" rather than "timing/guessing strategy"
Fixes: 1. reward window: 0.2-0.8 --> 0.2-0.7
2. target contrast: 159/185 --> 145/185
3 (potential). detect accuracy proportion of each cti bin, then increase percentage of the bins that he doesn't perform well. 

@author: ly1232
"""


import os
import sys
import math
import numpy as np
import random
import pygame
import pyfirmata
import csv
import platform
from psychopy import data, core, gui


# Set to True if Arduino is connected
arduino_connected = True


refresh_rate = 60
frameDur = 1.0 / refresh_rate

# =============================================================================
# Initiate libraries
# =============================================================================
pygame.init()

# =============================================================================
# Arduino setup (if connected)
# =============================================================================
if arduino_connected:
    if 'Darwin' in platform.system():  # Mac
        serPort = "/dev/cu.usbmodem21101"
    else:
        serPort = "COM3" #change to COM3 if needed
    arduino = pyfirmata.Arduino(serPort)

# =============================================================================
# Mouse status
# =============================================================================
if 'Darwin' in platform.system():  # Mac
    pygame.mouse.set_visible(True)
else:
    pygame.mouse.set_visible(True)

# =============================================================================
# Parameters
# =============================================================================
info = {}

# Present dialog to collect info
info['session'] = ''
dlg = gui.DlgFromDict(info)
if not dlg.OK:
    if arduino_connected:
        arduino.exit()
    core.quit()

info['blks'] = 1000
info['monkey'] = "bogie"
info['bgColor'] = [127, 127, 127]
info['fixColor'] = [255, 255, 255]
info['cueColor'] = [95, 95, 95] ###
info['barColor'] = [185, 185, 185]
info['targetColor_start'] = [185, 185, 185]
info['leverColor'] = [255, 255, 255]
info['targetColor_end'] = [145, 145, 145] #if I want to change the contrast, make it closer to 190

# Sizes and positions
info['fixSize'] = 15
info['cueSize'] = 90 ###
info['targetSize'] = 70
info['leverSize'] = 110
info['leverOffset_x'] = 0
info['leverOffset_y'] = 50

screen_width = 1280
screen_height = 1024
win = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
win.fill(info['bgColor'])

center_x = win.get_width() / 2
center_y = win.get_height() / 2

info['fixPos'] = [center_x, center_y]

# Define the vertices of the invisible square
info['halfSide'] = 250
side_length = info['halfSide'] * 2
vertices = [
    (center_x - info['halfSide'], center_y - info['halfSide']),  # Top-left
    (center_x + info['halfSide'], center_y - info['halfSide']),  # Top-right
    (center_x - info['halfSide'], center_y + info['halfSide']),  # Bottom-left
    (center_x + info['halfSide'], center_y + info['halfSide'])  # Bottom-right
]

# Initial target position
target_pos = random.choice(vertices)
info['square_pos'] = pygame.Rect(target_pos[0] - info['targetSize'],  # left
                                 target_pos[1] - info['targetSize'],  # top
                                 info['targetSize'] * 2,  # width
                                 info['targetSize'] * 2)  # height
###
info['cue_square_pos'] = pygame.Rect(target_pos[0] - info['cueSize'],  # left
                                 target_pos[1] - info['cueSize'],  # top
                                 info['cueSize'] * 2,  # width
                                 info['cueSize'] * 2)  # height

# Timing parameters
info['fbTime'] = int(0.2 / frameDur)
info['iti'] = int(1 / frameDur)
#info['release_timeout'] = int(0.01 / frameDur)

info['dateStr'] = data.getDateStr().replace('-', '')  # Conve  'mm-dd-yyyy' to 'mmddyyyy'

filename = "results/" + info['monkey'] + '_' + info['dateStr']


# Timer
clock = pygame.time.Clock()


# =============================================================================
# Helper functions
# =============================================================================
def pts(num_sides, tilt_angle, x, y, radius):
    pts_pos = []
    for i in range(num_sides):
        x = x + radius * math.cos(tilt_angle + math.pi * 2 * i / num_sides)
        y = y + radius * math.sin(tilt_angle + math.pi * 2 * i / num_sides)
        pts_pos.append([int(x), int(y)])
    return pts_pos


def draw_bars(bar_orientation, target_pos, bar_color):
    """Draw two bars (either vertical or horizontal) based on orientation and target position."""
    # Calculate symmetric position
    symmetric_pos = (2 * center_x - target_pos[0], 2 * center_y - target_pos[1])

    # Draw bars at both the target position and the symmetric position
    if bar_orientation == "horizontal":
        # Bar at the target position
        pygame.draw.rect(win, bar_color,
                         pygame.Rect(target_pos[0] - info['targetSize'] - side_length if target_pos[0] > center_x else target_pos[0] - info['targetSize'],  # left
                                     target_pos[1] - info['targetSize'],  # top
                                     side_length + info['targetSize']*2,  # width
                                     info['targetSize'] * 2))  # height
        # Bar at the symmetric position
        pygame.draw.rect(win, bar_color,
                         pygame.Rect(symmetric_pos[0] - info['targetSize']-side_length if symmetric_pos[0] > center_x else symmetric_pos[0] - info['targetSize'],  # left
                                     symmetric_pos[1] - info['targetSize'],  # top
                                     side_length + info['targetSize']*2,  # width
                                     info['targetSize'] * 2))  # height
    elif bar_orientation == "vertical":
        # Bar at the target position
        pygame.draw.rect(win, bar_color,
                         pygame.Rect(target_pos[0] - info['targetSize'],
                                     target_pos[1] - info['targetSize'] - side_length if target_pos[1] > center_y else target_pos[1] - info['targetSize'],
                                     info['targetSize'] * 2,  # width
                                     side_length + info['targetSize']*2))  # height
        # Bar at the symmetric position
        pygame.draw.rect(win, bar_color,
                         pygame.Rect(symmetric_pos[0] - info['targetSize'],
                                     symmetric_pos[1] - info['targetSize'] - side_length if symmetric_pos[1] > center_y else symmetric_pos[1] - info['targetSize'],
                                     info['targetSize'] * 2,  # width
                                     side_length + info['targetSize']*2))  # height

def lever_show_draw(color):
    lever = pygame.draw.polygon(win, color,
                                pts(6, 0,
                                    win.get_width() - info['leverSize'] * 2 - info['leverOffset_x'],
                                    win.get_height() - info['leverSize'] * 2 - info['leverOffset_y'],
                                    info['leverSize']))
    return lever


def fix_draw(color):
    fix_dot = pygame.draw.circle(win, color, info['fixPos'], info['fixSize'])
    return fix_dot


def target_draw(color):
    target = pygame.draw.rect(win, color, info['square_pos'])
    return target

###
def cue_draw(color):
    cue=pygame.draw.rect(win, color, info['cue_square_pos'])
    return cue


# def target_draw(color):
#     # Create a surface for the target with per-pixel alpha
#     target_surface = pygame.Surface((info['square_pos'].width, info['square_pos'].height), pygame.SRCALPHA)
#     # Fill the surface with the color and set the alpha value to 128 (half transparent)
#     target_surface.fill((*color, 128))
#     # Blit the target surface onto the main window at the target's position
#     win.blit(target_surface, info['square_pos'].topleft)


def auditory_fb(sound_file):
    pygame.mixer.music.load(sound_file)
    pygame.mixer.music.set_volume(0.9)
    pygame.mixer.music.play()

def fallback_local_write(rows, fieldnames, mode='a'):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_folder = os.path.join(script_dir, "results")
    os.makedirs(results_folder, exist_ok=True)
    local_file = os.path.join(results_folder, "backup_data.csv")
    try:
        with open(local_file, mode, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if f.tell() == 0 and mode == 'w':
                writer.writeheader()  # Write header for a new file
            if isinstance(rows, dict):
                writer.writerow(rows)  # Single rowC
            else:
                writer.writerows(rows)  # Multiple rows
        print(f"Data saved locally to {local_file}")
    except Exception as e:
        print(f"Failed to save data locally: {e}")


# =============================================================================
# Trials conditions
# =============================================================================
experiment_start_time = pygame.time.get_ticks()  # Record experiment start time in ms

conditions = data.importConditions('conditions.xlsx')
trials = data.TrialHandler(trialList=conditions, nReps=1, method='random', name='mainExp')
allTrials = [trials]

thisExp = data.ExperimentHandler(name='ed', version='1.0', extraInfo=info, dataFileName=filename)

# Initialize global trial counter
global_trial_number = 1

# Initialize the consecutive correct counter before entering the trial loop
consecutive_correct = 0

# Define CSV header (note: 'block' is now unused)
header = ['block',
          'trial',
          'trial_type',
          'taps_start_loc_during_fix',
          'taps_end_loc_during_fix',
          'taps_on_lever_during_fix',
          'taps_on_lever_s_during_fix',
          'bar_orientation',
          'target_xy',
          'cti',
          'rt',
          'acc',
          'time',
          'pulses',
          'fa_rate_recent100',
          'p_catch']
with open(filename + '.csv', 'w', newline='') as f:  # Open in 'write' mode
    writer = csv.writer(f)
    writer.writerow(header)  # Write the header once

# =============================================================================
# Main experiment loop (no blocks; trial type is assigned at random)
# =============================================================================
total_trials = 10000  # or set to a fixed number, e.g., 1000
recent_trials = []  # will store tuples: (trial_type, acc, rt)
p_catch = 0.25
        
for trial_idx in range(total_trials):
    print(f"Global Trial {global_trial_number}")

    # Randomly assign trial type
    if random.random() < p_catch:
        trial_type = "catch"
    else:
        trial_type = "target"
        
    # Record trial start time
    trial_start_time = pygame.time.get_ticks()  # current time in ms
    time_elapsed = (trial_start_time - experiment_start_time) / 1000  # in seconds

    # Randomly select target position and bar orientation
    bar_orientation = random.choice(["vertical", "horizontal"])
    target_pos = random.choice(vertices)
    info['square_pos'] = pygame.Rect(target_pos[0] - info['targetSize'],
                                     target_pos[1] - info['targetSize'],
                                     info['targetSize'] * 2,
                                     info['targetSize'] * 2)
    info['cue_square_pos'] = pygame.Rect(target_pos[0] - info['cueSize'],
                                         target_pos[1] - info['cueSize'],
                                         info['cueSize'] * 2,
                                         info['cueSize'] * 2)

    # Set timing parameters
    tapDur = random.randint(500, 1200) / 1000
    info['tapDur_fix'] = int(tapDur / frameDur)
    fixDur = random.randint(500, 800) / 1000
    info['fixDur'] = int(fixDur / frameDur)
    RT = 0
    corr_resp = None
    response_locked = False
    # (The literal "3" in your code seems to be a leftover and is omitted)

    # =============================================================================
    # Beginning of Trial (lever appear phase)
    # =============================================================================
    mouse_is_down = False
    mouse_in_lever = False
    down_dur_frame = 0
    taps_down_time_fix = []  # all taps time (finger down)
    taps_down_loc_fix = []   # all taps location (finger down)
    taps_up_time_fix = []
    taps_up_loc_fix = []
    on_lever_fix = []        # if taps on lever
    taps_frame_fix = []      # tap duration in frames
    taps_s_fix = []          # tap duration in s
    rt = []
    cti = []
    frame_fix = 0

    running = True
    while running:
        clock.tick(refresh_rate)
        lever_show_draw(info['leverColor'])
        pygame.display.update()
        frame_fix += 1
        if frame_fix > 1:
            pygame.event.set_allowed(pygame.MOUSEBUTTONUP)
            pygame.event.set_allowed(pygame.MOUSEBUTTONDOWN)
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_is_down = True
                down_loc = pygame.mouse.get_pos()
                taps_down_loc_fix.append(down_loc)
                if lever_show_draw(info['bgColor']).collidepoint(down_loc):
                    mouse_in_lever = True
                    on_lever_fix.append(1)
                else:
                    mouse_in_lever = False
                    on_lever_fix.append(0)
            elif event.type == pygame.MOUSEBUTTONUP:
                running = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if arduino_connected:
                        arduino.exit()
                    pygame.quit()
                    sys.exit()
        if mouse_is_down and mouse_in_lever:
            down_dur_frame += 1
        if down_dur_frame > 1:
            running = False

    # =============================================================================
    # Fixation Phase
    # =============================================================================
    fixation_duration_frames = random.randint(int(0.5 / frameDur), int(0.8 / frameDur))
    frame_count = 0
    running = True
    barphase = False
    fix_start_time = pygame.time.get_ticks()
    while running:
        clock.tick(refresh_rate)
        fix_draw(info['fixColor'])
        pygame.display.update()
        frame_count += 1
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONUP:
                rt.append(('fix', (pygame.time.get_ticks() - fix_start_time) / 1000))
                corr_resp = 0
                response_locked=True
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_is_down = True
                down_time = pygame.time.get_ticks()
                taps_down_time_fix.append(down_time)
                taps_down_loc_fix.append(pygame.mouse.get_pos())
                if lever_show_draw(info['bgColor']).collidepoint(pygame.mouse.get_pos()):
                    mouse_in_lever = True
                    on_lever_fix.append(1)
                else:
                    mouse_in_lever = False
                    on_lever_fix.append(0)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if arduino_connected:
                        arduino.exit()
                    pygame.quit()
                    sys.exit()
        if frame_count >= fixation_duration_frames:
            running = False
            barphase = True

    # =============================================================================
    # Bar Phase
    # =============================================================================
    running = True
    change_cue_color = False
    frame_fix = 0
    down_dur_bar = 0
    bar_start_time = pygame.time.get_ticks()
    while running:
        clock.tick(refresh_rate)
        fix_draw(info['fixColor'])
        if barphase:
            draw_bars(bar_orientation, target_pos, info['barColor'])
            target_draw(info['targetColor_start'])
            lever_show_draw(info['leverColor'])
            pygame.display.update()
            stim_onset_time = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_is_down = True
                    down_time = pygame.time.get_ticks()
                    taps_down_time_fix.append(down_time)
                    taps_down_loc_fix.append(pygame.mouse.get_pos())
                    if lever_show_draw(info['bgColor']).collidepoint(pygame.mouse.get_pos()):
                        mouse_in_lever = True
                        on_lever_fix.append(1)
                        RT = down_time - stim_onset_time
                    else:
                        mouse_in_lever = False
                        on_lever_fix.append(0)
                elif event.type == pygame.MOUSEBUTTONUP:
                    up_time = pygame.time.get_ticks()
                    taps_up_time_fix.append(up_time)
                    taps_up_loc_fix.append(pygame.mouse.get_pos())
                    taps_frame_fix.append(down_dur_bar)
                    taps_s_fix.append(down_dur_bar * frameDur)
                    rt.append(('bar', (pygame.time.get_ticks() - bar_start_time) / 1000))
                    corr_resp = 0
                    response_locked=True
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if arduino_connected:
                            arduino.exit()
                        pygame.quit()
                        sys.exit()
            if mouse_is_down and mouse_in_lever:
                down_dur_bar += 1
            if down_dur_bar > info['tapDur_fix']:
                change_cue_color = True
                running = False
        else:
            running = False

    # =============================================================================
    # Cue & CTI Phase
    # =============================================================================
    info['cue_duration'] = int((100/1000) / frameDur)
    if trial_type == "catch":
        info['cue_target_interval'] = int((1700 / 1000) / frameDur)
    else:
        info['cue_target_interval'] = int((random.randint(350, 1550) / 1000) / frameDur)
        
    change_target_color = False
    cue_frame = 0
    running = True
    cue_returned = False
    cue_start_time = pygame.time.get_ticks()
    while running:
        clock.tick(refresh_rate)
        fix_draw(info['fixColor'])
        if change_cue_color:
            cue_frame += 1
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONUP:
                    rt.append(('cti', (pygame.time.get_ticks() - cue_start_time) / 1000))
                    corr_resp= 0
                    response_locked=True
                    running = False
                    change_cue_color = False
            if not cue_returned:
                cue_draw(info['cueColor'])
                draw_bars(bar_orientation, target_pos, info['barColor'])
                lever_show_draw(info['leverColor'])
                pygame.display.update()
            if cue_frame > info['cue_duration'] and not cue_returned:
                cue_draw(info['bgColor'])
                draw_bars(bar_orientation, target_pos, info['barColor'])
                lever_show_draw(info['leverColor'])
                pygame.display.update()
                cue_returned = True
            if cue_frame > info['cue_target_interval']:  # CTI phase
                corr_resp = 0
                cti.append(info['cue_target_interval'] * frameDur)
                running = False
                change_cue_color = False
                change_target_color = True
        else:
            running = False

    # =============================================================================
    # Target Change Phase
    # =============================================================================
    if trial_type == "catch":
        # Skip target drawing — catch trials have 0ms target phase
        running = True
        catch_start_time = pygame.time.get_ticks()
        catch_response_window = 0.0001  # Allow a brief moment to catch accidental clicks (e.g., 100ms)
    
        while running:
            clock.tick(refresh_rate)
            fix_draw(info['fixColor'])
            pygame.display.update()
    
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONUP:
                    taps_frame_fix.append(down_dur_frame)
                    taps_s_fix.append(down_dur_frame * frameDur)
                    up_time = pygame.time.get_ticks()
                    rt_in_seconds = (up_time - catch_start_time) / 1000
                    rt.append(rt_in_seconds)
                    corr_resp = 0  # Incorrect — responded during catch
                    response_locked=True
                    running = False
    
            if pygame.time.get_ticks() - catch_start_time > catch_response_window:
                rt.append(np.nan)
                if not response_locked:
                    corr_resp = 1  # Correct — withheld response
                running = False
    
    else:  # trial_type == "target"
        info['target_duration'] = int((150 / 1000) / frameDur)
        max_target_hold_frames = int((800 / 1000) / frameDur)
        running = True
        down_dur_t_frame = 0
        target_change_time = pygame.time.get_ticks()
        target_returned = False
    
        while running:
            clock.tick(refresh_rate)
            fix_draw(info['fixColor'])
    
            if change_target_color:
                down_dur_t_frame += 1
    
                if not target_returned:
                    draw_bars(bar_orientation, target_pos, info['barColor'])
                    target_draw(info['targetColor_end'])
                    lever_show_draw(info['leverColor'])
                    pygame.display.update()
    
                if down_dur_t_frame > info['target_duration'] and not target_returned:
                    draw_bars(bar_orientation, target_pos, info['barColor'])
                    target_draw(info['targetColor_start'])
                    lever_show_draw(info['leverColor'])
                    pygame.display.update()
                    target_returned = True
    
                for event in pygame.event.get():
                    if event.type == pygame.MOUSEBUTTONUP:
                        taps_frame_fix.append(down_dur_frame + down_dur_t_frame)
                        taps_s_fix.append((down_dur_frame + down_dur_t_frame) * frameDur)
                        up_time = pygame.time.get_ticks()
                        rt_in_seconds = (up_time - target_change_time) / 1000
                        rt.append(rt_in_seconds)
    
                        if 0.200 <= rt_in_seconds <= 0.800:
                            corr_resp = 1  # Valid target response
                        else:
                            corr_resp = 0  # Too early or too late
                            response_locked = True
                        running = False
                if down_dur_t_frame > max_target_hold_frames:
                    taps_frame_fix.append(down_dur_frame + down_dur_t_frame)
                    taps_s_fix.append((down_dur_frame + down_dur_t_frame) * frameDur)
                    rt.append(np.nan)
                    corr_resp = 0
                    response_locked = True
                    running = False
            else:
                running = False
    
    # Prevent queueing events
    pygame.event.set_blocked(pygame.MOUSEBUTTONUP)
    pygame.event.set_blocked(pygame.MOUSEBUTTONDOWN)
    
    # --- Reward Logic Insertion ---
    # At this point, corr_resp is set (1 for correct, 0 for incorrect)
    # --- Reward Logic Insertion ---
    # At this point, corr_resp is set (1 for correct, 0 for incorrect)
    
    '''if corr_resp == 1:
        consecutive_correct += 1
    
        if consecutive_correct == 4:
            reward_pulses = 2  # On 4th consecutive correct trial
        elif consecutive_correct == 8:
            reward_pulses = 3  # On 8th consecutive correct trial
            consecutive_correct = 0  # Reset after the big bonus
        else:
            reward_pulses = 1  # Normal correct trial
    else:
        reward_pulses = 0
        consecutive_correct = 0  # Reset on incorrect trial
    
    # Add a 300ms delay after each correct trial before sending the reward pulses
    if corr_resp == 1:
        win.fill(info['bgColor'])
        pygame.display.update()
        pygame.time.wait(300)'''
    # Custom reward logic (after corr_resp is determined)
    # --- Tiered Reward Logic ---
    if corr_resp == 1:
        consecutive_correct += 1
    
        if consecutive_correct >= 7:
            reward_pulses = 3
        elif consecutive_correct >= 4:
            reward_pulses = 2
        else:
            reward_pulses = 1
    else:
        reward_pulses = 0
        consecutive_correct = 0


    # Add a 500ms delay after each correct trial before sending the reward pulses
    if corr_resp == 1:
        # Clear the screen to blank it
        win.fill(info['bgColor'])
        pygame.display.update()
        #if trial_type == "catch":
           # auditory_fb("rightanswer-95219.mp3")
        #else:
            #auditory_fb("correct-choice-43861.mp3")
        pygame.time.wait(500)  # Wait 500ms with a blank screen
    # =============================================================================
    # Feedback Phase (send pulses based on reward_pulses)
    # =============================================================================
    frame_fb = 0
    if arduino_connected and corr_resp == 1:
        if reward_pulses == 3:
            # Send first pulse
            arduino.digital[13].write(1)
            pygame.time.wait(4)
            arduino.digital[13].write(0)
            pygame.time.wait(400)
            # Send second pulse
            arduino.digital[13].write(1)
            pygame.time.wait(4)
            arduino.digital[13].write(0)
            pygame.time.wait(400)
            # Send third pulse
            arduino.digital[13].write(1)
            pygame.time.wait(4)
            arduino.digital[13].write(0)
    
        elif reward_pulses == 2:
            # Send first pulse
            arduino.digital[13].write(1)
            pygame.time.wait(4)
            arduino.digital[13].write(0)
            pygame.time.wait(400)
            # Send second pulse
            arduino.digital[13].write(1)
            pygame.time.wait(4)
            arduino.digital[13].write(0)
    
        elif reward_pulses == 1:
            arduino.digital[13].write(1)
            pygame.time.wait(4)
            arduino.digital[13].write(0)
    while True:
        clock.tick(refresh_rate)
        frame_fb += 1
        if frame_fb > info['fbTime']:
            break
    if arduino_connected:
        arduino.digital[13].write(0)

    # =============================================================================
    # Save trial data
    # =============================================================================
    # FA ASSIST MODE:
    recent_trials.append((trial_type, corr_resp, rt))
    
    # Keep only the last 100 trials
    if len(recent_trials) > 50:
        recent_trials = recent_trials[-50:]
    
    # Compute FA rate
    false_alarms = 0
    for ttype, acc, rts in recent_trials:
        if ttype == "catch" and acc == 0:
            false_alarms += 1
        elif ttype == "target":
            if isinstance(rts, list) and any(isinstance(r, tuple) and r[0] == 'cti' for r in rts):
                false_alarms += 1
    
    fa_rate_recent = false_alarms / len(recent_trials) if recent_trials else 0
    
    # Adjust p_catch if 100 trials reached
    if len(recent_trials) == 50:
        if fa_rate_recent > 0.06:
            p_catch = 0.25
        else:
            p_catch = 0.25
            
    trial_data = [
        0,  # block number is now omitted or set to 0 since there's no block structure
        global_trial_number,
        trial_type,
        taps_down_loc_fix,
        taps_up_loc_fix,
        on_lever_fix,
        taps_s_fix,
        bar_orientation,
        target_pos,
        ','.join(map(str, cti)),
        ','.join(map(str, rt)),
        corr_resp,
        time_elapsed,
        reward_pulses,
        fa_rate_recent,
        p_catch
    ]
    
    with open(filename + '.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(trial_data)

    global_trial_number += 1

    
    # =============================================================================
    # Inter-trial interval
    # =============================================================================
    frame_iti = 0
    while True:
        clock.tick(refresh_rate)
        win.fill(info['bgColor'])
        pygame.display.update()
        frame_iti += 1
        if frame_iti > info['iti']:
            break

print(f"Completed all {total_trials} trials.")

trials = data.TrialHandler(trialList=conditions, nReps=1, method='random', name='mainExp')
if arduino_connected:
    arduino.exit()
pygame.quit()
