"""
Created on Fri Jan 19 11:31:48 2024

@author: Phillip Cheng

monkey hold lever for 300-1500ms to make square target change color. Release needs to be within 1000ms after contrast change
to get reward.

target randomly appears in one of four vertices of an invisible square.

a central fix dot is present
bars are present

any tap outside the lever is an incorrect response.
any taps too short or too long are incorrect

touch before stimuli onset is not queued

"""

import sys
import math
import random
import pygame
import pyfirmata
import csv
import platform
from psychopy import data, core, gui

# Set to True if Arduino is connected
arduino_connected = False

pygame.FULLSCREEN = True
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
        serPort = "COM4" #change to COM3 if needed
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
info['barColor'] = [190, 190, 190]
info['targetColor_start'] = [190, 190, 190]
info['leverColor'] = [255, 255, 255]
info['targetColor_end'] = [150, 150, 150] #if I want to change the contrast, make it closer to 190

# Sizes and positions
info['fixSize'] = 15
info['cueSize'] = 90 ###
info['targetSize'] = 70
info['leverSize'] = 100
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
info['release_timeout'] = int(0.8 / frameDur)

info['dateStr'] = data.getDateStr().replace('-', '')  # Convert 'mm-dd-yyyy' to 'mmddyyyy'
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


# =============================================================================
# Trials conditions
# =============================================================================
experiment_start_time = pygame.time.get_ticks()  # Record the experiment start time in milliseconds

practice = data.importConditions("practice.xlsx")
conditions = data.importConditions('conditions.xlsx')
pracTrials = data.TrialHandler(trialList=practice, nReps=1, method='random', name='pracTrials')
trials = data.TrialHandler(trialList=conditions, nReps=info['blks'], method='random', name='mainExp')
allTrials = [pracTrials,trials]

thisExp = data.ExperimentHandler(name='ed', version='1.0', extraInfo=info, dataFileName=filename)

# =============================================================================
# Main experiment loop
# =============================================================================
for trials in allTrials:
    thisExp.addLoop(trials)

    for thisTrial in trials:
        
        # Record the start time of the trial
        trial_start_time = pygame.time.get_ticks()  # Get the current time in milliseconds
        time = (trial_start_time - experiment_start_time) / 1000  # Convert to seconds
        
        # Randomly select target position and bar orientation
        bar_orientation = random.choice(["vertical", "horizontal"])
        target_pos = random.choice(vertices)
        info['square_pos'] = pygame.Rect(target_pos[0] - info['targetSize'],
                                         target_pos[1] - info['targetSize'],
                                         info['targetSize'] * 2,
                                         info['targetSize'] * 2)
        ###
        info['cue_square_pos'] = pygame.Rect(target_pos[0] - info['cueSize'],  # left
                                         target_pos[1] - info['cueSize'],  # top
                                         info['cueSize'] * 2,  # width
                                         info['cueSize'] * 2)  # height
        
        tapDur = random.randint(500, 1200) / 1000
        info['tapDur_fix'] = int(tapDur / frameDur)
        
        fixDur = random.randint(500, 800) / 1000
        info['fixDur'] = int(fixDur / frameDur)

        RT = 0
        corr_resp = 0
        3
        
        
        
        # =============================================================================
        # Beginning of Trial
        # =============================================================================
        mouse_is_down = False
        mouse_in_lever = False
        down_dur_frame = 0
        taps_down_time_fix = []  # all taps time (finger down)
        taps_down_loc_fix = []  # all taps location (finger down)
        taps_up_time_fix = []
        taps_up_loc_fix = []
        on_lever_fix = []  # if taps on lever
        taps_frame_fix = []  # tap duration in frames
        taps_s_fix = []  # tap duration in s
        rt=[]
        cti=[]
        frame_fix = 0
        
        
        running = True
        #1. lever appear phase
        while running:
            clock.tick(refresh_rate) 
            lever_show_draw(info['leverColor'])
            pygame.display.update()
            frame_fix += 1 
            if frame_fix > 1:
                pygame.event.set_allowed(pygame.MOUSEBUTTONUP)
                pygame.event.set_allowed(pygame.MOUSEBUTTONDOWN)
            # detects lever press
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_is_down = True
                    # down_time = pygame.time.get_ticks()
                    down_loc = pygame.mouse.get_pos()
                    # taps_down_time_fix.append(down_time)
                    taps_down_loc_fix.append(down_loc)
                    
                    #detects if the press is in the lever range
                    if lever_show_draw(info['bgColor']).collidepoint(down_loc):  # finger on lever
                        mouse_in_lever = True
                        on_lever_fix.append(1)
                        #RT = down_time - stim_onset_time
                    else:
                        mouse_in_lever = False
                        on_lever_fix.append(0)

                elif event.type == pygame.MOUSEBUTTONUP:
                    # up_time = pygame.time.get_ticks()
                    # up_loc = pygame.mouse.get_pos()
                    # taps_up_time_fix.append(up_time)
                    # taps_up_loc_fix.append(up_loc)

                    # taps_frame_fix.append(down_dur_frame)
                    # taps_s_fix.append(down_dur_frame * frameDur)

                    running = True

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if arduino_connected:
                            arduino.exit()
                        pygame.quit()
                        sys.exit()
                        
            if mouse_is_down and mouse_in_lever:
                down_dur_frame += 1
            
            #This defines how long the stimulus appears after pressing
            if down_dur_frame >1:
                running = False
            # add feature wheree if FINger down throughout the whole trial, level of next trial won't appear. 
        
        # =============================================================================
        # Fix phase
        # =============================================================================
        fixation_duration_frames = random.randint(int(0.5 / frameDur), int(0.8 / frameDur))  # 500-800 ms in frames
        frame_count = 0
        running = True
        barphase=False
        
        while running:
            clock.tick(refresh_rate)
            fix_draw(info['fixColor'])  # Display fixation dot
            pygame.display.update()
            
            frame_count += 1
            
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONUP:
                    rt.append(0)
                    running=False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_is_down = True
                    down_time = pygame.time.get_ticks()
                    down_loc = pygame.mouse.get_pos()
                    taps_down_time_fix.append(down_time)
                    taps_down_loc_fix.append(down_loc)

                    if lever_show_draw(info['bgColor']).collidepoint(down_loc):  # finger on lever
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
                running = False  # End fixation phase
                barphase=True
            
        
            
        # =============================================================================
        # Bar phase
        # =============================================================================
        running = True
        
        change_cue_color = False
        frame_fix = 0
        down_dur_bar=0
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
                        down_loc = pygame.mouse.get_pos()
                        taps_down_time_fix.append(down_time)
                        taps_down_loc_fix.append(down_loc)
    
                        if lever_show_draw(info['bgColor']).collidepoint(down_loc):  # finger on lever
                            mouse_in_lever = True
                            on_lever_fix.append(1)
                            RT = down_time - stim_onset_time
                        else:
                            mouse_in_lever = False
                            on_lever_fix.append(0)
    
                    elif event.type == pygame.MOUSEBUTTONUP:
                        up_time = pygame.time.get_ticks()
                        up_loc = pygame.mouse.get_pos()
                        taps_up_time_fix.append(up_time)
                        taps_up_loc_fix.append(up_loc)
    
                        taps_frame_fix.append(down_dur_bar)
                        taps_s_fix.append(down_dur_bar * frameDur)
                        rt.append(0)
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
                running=False
       
                
                
        # =============================================================================
        # Cue & CTI phase ###
        # =============================================================================
        info['cue_duration']=int((100/1000)/frameDur)
        info['cue_target_interval'] = int((random.randint(500, 1700) / 1000) / frameDur)
        change_target_color=False
        cue_frame=0
        running = True
        cue_returned = False
        
        while running:
            clock.tick(refresh_rate)

            fix_draw(info['fixColor'])
            

            if change_cue_color:
                cue_frame += 1
                
                # Monitor Finger/Mouse
                for event in pygame.event.get():
                    if event.type == pygame.MOUSEBUTTONUP:
                        rt.append(0)
                        running = False
                        change_cue_color = False

                # Draw the cue beofre the bars so that it appears behind the bars.  
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
                    
                if cue_frame > info['cue_target_interval']: ###CTI phase
                    corr_resp = 0
                    cti.append(info['cue_target_interval']*frameDur)
                    running = False
                    change_cue_color = False
                    change_target_color=True
            else:
                running = False


        
        # =============================================================================
        # Target change phase
        # =============================================================================
        info['target_duration']=int((250/1000)/frameDur)
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
                
                # After 250ms, change the target color back to 'targetColor_start'
                if down_dur_t_frame > info['target_duration'] and not target_returned:
                   draw_bars(bar_orientation, target_pos, info['barColor'])
                   target_draw(info['targetColor_start'])
                   lever_show_draw(info['leverColor'])
                   pygame.display.update()
                   target_returned = True  # Set the state to prevent changing the color back again


                for event in pygame.event.get():
                    if event.type == pygame.MOUSEBUTTONUP:
                        taps_frame_fix.append(down_dur_frame + down_dur_t_frame)
                        taps_s_fix.append((down_dur_frame + down_dur_t_frame) * frameDur)
                        
                        up_time = pygame.time.get_ticks()  # Stop the timer
                        rt_in_seconds = (up_time - target_change_time) / 1000  # Reaction time in seconds
                        rt.append(rt_in_seconds)
                        
                        corr_resp = 1
                        running = False

                if down_dur_t_frame > info['release_timeout']:
                    taps_frame_fix.append(down_dur_frame + down_dur_t_frame)
                    taps_s_fix.append((down_dur_frame + down_dur_t_frame) * frameDur)
                    
                    up_time = pygame.time.get_ticks()  # Stop the timer
                    rt_in_seconds = (up_time - target_change_time) / 1000  # Reaction time in seconds
                    rt.append(rt_in_seconds)
                    
                    corr_resp = 0
                    running = False
            else:
                running = False

        # Prevent queueing events
        pygame.event.set_blocked(pygame.MOUSEBUTTONUP) #change back to figerup/down
        pygame.event.set_blocked(pygame.MOUSEBUTTONDOWN)

        # =============================================================================
        # Feedback phase
        # =============================================================================
        frame_fb = 0
        while True:
            clock.tick(refresh_rate)

            #if corr_resp == 1:
                #auditory_fb("sound_correct.mp3")

            if arduino_connected:
                if corr_resp == 1:
                    arduino.digital[13].write(1)  # Activate channel 13

            frame_fb += 1
            if frame_fb > info['fbTime']:
                break

        if arduino_connected:
            arduino.digital[13].write(0)  # Deactivate channel 13

        # =============================================================================
        #         save data manually...
        #         ('.addData' not working reliably on spyder)
        # =============================================================================
        header = ['block',
                  'practice',
                  'trial',

                  'change_interval_s',
                  'change_interval_frames',

                  'taps_start_time_during_fix',
                  'taps_end_time_during_fix',
                  'taps_start_loc_during_fix',
                  'taps_end_loc_during_fix',
                  'taps_on_lever_during_fix',
                  'taps_on_lever_frame_during_fix',
                  'taps_on_lever_s_during_fix',

                  'fix_xy',
                  'bar_orientation',
                  'target_xy',

                  # 'taps_start_time_during_target',
                  # 'taps_start_loc_during_target',
                  # 'taps_on_lever_during_target',
                  # 'taps_frame_during_target',
                  # 'taps_s_during_target',
                  'cti',
                  'rt',
                  'acc',
                  'time']

        trial_data = [trials.thisRepN + 1,
                      trials.name == 'pracTrials',
                      trials.thisN + 1,

                      tapDur,
                      info['tapDur_fix'],

                      taps_down_time_fix,
                      taps_up_time_fix,
                      taps_down_loc_fix,
                      taps_up_loc_fix,
                      on_lever_fix,
                      taps_frame_fix,
                      taps_s_fix,

                      info['fixPos'],
                      bar_orientation,
                      target_pos,

                      # taps_time_target,
                      # taps_loc_target,
                      # on_lever_target,
                      # taps_frame_target,
                      # taps_s_target,
                      cti,
                      rt,
                      corr_resp,
                      time]

        with open(filename + '.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            if trials.thisN == 0 and trials.name == 'pracTrials':
                writer.writerow(header)
            writer.writerow(trial_data)

        # # Save data
        # with open(filename + '.csv', 'a', newline='') as f:
        #     writer = csv.writer(f)
        #     if trials.thisN == 0 and trials.name == 'pracTrials':
        #         writer.writerow(['block', 'practice', 'trial', 'bar_orientation', 'target_position', 'rt', 'acc'])
        #     writer.writerow([trials.thisRepN + 1, trials.name == 'pracTrials', trials.thisN + 1,
        #                      bar_orientation, target_pos, RT, corr_resp])

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

if arduino_connected:
    arduino.exit()
pygame.quit()
