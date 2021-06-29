#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Spy Metronome
#
# Copyright (C) 2021  SUZUDO Yasushi  <yasushi_suzudo@yahoo.co.jp>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

# Copyright notice of click wav files, taken from "copyright" file in
# "klick" package, follows.
# (http://das.nasophon.de/klick/)
#
#  samples/click_*.wav
# Copyright:
#  2004-2006 Free Software Foundation
#  License: GPL-2+

import wx
import pyaudio
import wave
import threading
import time
# to do: 
#        volume control for 24, 32bit wav files?
#
#        use of configparser:
#             initial value for bpm and pattern
#             sound file selection

programName = "Spy Metronome"

# interpretation  of checkbox state to click state
ACCENT = wx.CHK_CHECKED
ON = wx.CHK_UNDETERMINED
OFF = wx.CHK_UNCHECKED

# for note Choice
noteValue = {"1":4, "2":2, "4":1, "8":0.5, "16":0.25}
noteValueIndex = {"1":0, "2":1, "4":2, "8":3, "16":4}

EVENT_WAIT = 0.1 # waiting time for an thread stopping event to occur

# you can change following values, but I suppose no such need.
BPM_MIN = 30
BPM_MAX = 600
TICK_NUM = 16 # max length of click pattern

#
# beginning of configurable values
#
############################################################################
normalWavFilePath = "/usr/share/klick/samples/click_normal.wav"
emphasisWavFilePath = "/usr/share/klick/samples/click_emphasis.wav"
### if you live in the windows, place wav files in the same folder as this
### file, and comment out above two lines and uncomment below two lines.
#normalWavFilePath = ".\click_normal.wav"
#emphasisWavFilePath = ".\click_emphasis.wav"

ENABLE_VOL = True       # if you do not have numpy package, turn this to False.

if ENABLE_VOL == True:
    INIT_VOL = 20       # initial value for volume
    mainWindowSize = (320,380)
else:    
    mainWindowSize = (320,280)

borderValue = 10

INIT_PATTERN = [ON, OFF, OFF, OFF] # initial value for click pattern.
                                   # OFF, ON or ACCENT.
INIT_BPM = 120   # initial value for BPM
INIT_NVAL = "16" # initial value for note. "1": whole note, "2": half note,
                 # "4": quarter note etc.

debug = False

############################################################################
#
# end of configurable values
#
if ENABLE_VOL == True:
    import numpy

class metronome():

    def __init__(self, parent, p = None, nval = None, bpm = None,
                 normal = None, accent = None, pattern = None):
        self.p = p         # PyAudio instance
        self.nval = nval   # whole note (4), half note (2), etc.
        self.bpm = bpm
        self.pattern = pattern   
        self.P_index = 0   # index of "click" in the pattern
        self.B_index = 0   # posision index in the current "click"
        self.wf = {}       # click wav file dict. normal click and accent click
                           # should have same framerate, width and channels.
        self.click = {}    # click sound data dict.
                           # each element is a list of "frame" of the sound.
        self.clicklen = 0
        # clicklen = framerate * interval : number of frames within interval

        self.clickp = 0    # current position in "clicklen"
        self.currentClick = None

        self.stream = None
        self.event = None
        self.started = False # whether stream has started or not

        self.framerate = None
        self.width =  None
        self.channels = None
        
        self.volume = 100

        for each in [[normal, ON], [accent, ACCENT], [None, OFF]]:
            # "OFF" should come after all the values needed
            # for the calculation have been obtained.
            snd = each[1] # just for readability
            if each[0] != None:
                self.wf[snd] = wave.open(each[0], 'rb')

                if self.framerate   == None:
                    self.framerate   = self.wf[snd].getframerate()
                elif self.framerate != self.wf[snd].getframerate():
                    print("framerate of wav files differ!")
                    exit(1)
                if self.width   == None:
                    self.width   =  self.wf[snd].getsampwidth()
                elif self.width !=  self.wf[snd].getsampwidth():
                    print("width of wav files differ!")
                    exit(1)
                if self.channels   == None:
                    self.channels   = self.wf[snd].getnchannels()
                elif self.channels != self.wf[snd].getnchannels():
                    print("channel number of wav files differ!")
                    exit(1)

            # from now on, "click" date for ON, ACCENT and OFF.
            # framerate, width and channels should be the same in ACCENT ahd ON

            self.click[snd] = []
            if snd == OFF:
                frames = 0
            else:
                frames = self.wf[snd].getnframes()
            for i in range(0, frames):
                self.click[snd].append(self.wf[snd].readframes(1))
                # i frame (sample)
                #   = (width (i.e. bytes/sample e.g 2 bytes for 16 bit file.)
                #     * channels) bytes

        self.Set_Interval(nval = nval, bpm = bpm)
        self.Set_Pattern(pattern = pattern)

        self.stream = self.p.open(format = self.p.get_format_from_width(self.width),
                                channels = self.channels,
                                rate = self.framerate,
                                output = True, start = False,
                                stream_callback = self.callback)

    # callback function
    # P_index indicate the position of the "click" in the patern,
    # and B_index indicate the position of byte in the "click"

    def callback(self, in_data, frame_count, time_info, status):
        data =b""
        for i in range (0, frame_count):  # getting "frame_count" size of data
            if self.clickp >= self.clicklen:
                self.P_index  = self.P_index  + 1
                if self.P_index >= len(self.clicklist):
                    self.P_index  = 0
                    # if reached at the end of pattern, go back to the head.
                self.clickp = 0
                if len(self.clicklist[self.P_index]) > 0:
                    self.currentClick = self.clicklist[self.P_index]
                    self.B_index  = 0                    

            if self.B_index < len(self.currentClick):
                chunk = self.currentClick[self.B_index]
                self.B_index  = self.B_index  + 1
            else:
                chunk = bytes(self.width * self.channels) # pad with 0 data
            self.clickp = self.clickp + 1

            if ENABLE_VOL == True:
                if self.width == 2: # 16bit
                    chunk = numpy.frombuffer(chunk, numpy.int16) * (self.volume/100.)
                    chunk = chunk.astype(numpy.int16).tobytes()
                elif self.width == 1: # 8bit
                    chunk = numpy.frombuffer(chunk, numpy.uint8) * (self.volume/100.)
                    chunk = chunk1.astype(numpy.uint8).tobytes()
                #elif self.width == 4: # float32? not tested
                #    chunk = numpy.frombuffer(chunk, numpy.float32) * (self.volume/100.)
                #    chunk = chunk1.astype(numpy.float32).tobytes()
            data = data + chunk

        return (data, pyaudio.paContinue)

    def ring(self, check = None):

        self.P_index = 0
        self.B_index = 0
        self.currentClick = self.clicklist[self.P_index]
        self.clickp = 0
        self.stream.start_stream()

        if debug == True:
            print("stream started: pattern = " + str(self.pattern)
                  + "nval: " + str(self.nval)
                  + " bpm: " + str(self.bpm) + " clicklen: "
                  + str(self.clicklen))
        while self.stream.is_active():
            if self.event.wait(timeout =  EVENT_WAIT):
                self.stream.stop_stream()

        if debug == True:
            print("stream stopped")
        return()


    def start_sound(self):
        self.event = threading.Event()
        self.thread = threading.Thread(target = self.ring)
        self.thread.start()
        self.started = True

    def stop_sound(self):
        if self.event != None:
            self.event.set()
        self.started = False

    def Get_Status(self):
        return(self.started)

    def Get_Pattern(self):
        return(self.pattern)

    if ENABLE_VOL == True:
        
        def Get_Volume(self):
            return self.volume

        def Set_Volume(self, vol = None):
            if vol != None:
                self.volume = vol

    def Set_Interval(self, nval = None, bpm = None):
        if nval != None:
            self.nval = nval
        if bpm != None:
            self.bpm = bpm

        self.interval = 60 * self.nval / self.bpm
        self.clicklen = int(self.framerate * self.interval)

    def Set_Pattern(self, pattern = None):
        if pattern != None:
            self.pattern = pattern
        self.clicklist = []                      # rythme (or click) pattern
        for each in self.pattern:
            # click[each] should be built up again,
            # if interval has benn changed.
            self.clicklist.append(self.click[each])

class mainWindow(wx.Frame):

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size = mainWindowSize)

        self.p = pyaudio.PyAudio()
        init_bpm = INIT_BPM
        init_pattern = INIT_PATTERN
        if ENABLE_VOL == True:
            init_vol = INIT_VOL
        self.patternlen = len(INIT_PATTERN)
        self.TickList = []
        normWavPath = normalWavFilePath
        emphWavPath = emphasisWavFilePath
        self.lastTap = None

        # GUI parts

        menuBar = wx.MenuBar()

        fileMenu = wx.Menu()
        metronomeMenu  = wx.Menu()

        menuAbout = fileMenu.Append(wx.ID_ABOUT, "&About",
                                    " Information about this program")
        fileMenu.AppendSeparator()
        menuExit = fileMenu.Append(wx.ID_EXIT,"&Exit",
                                   " Terminate this program")
        
        wID_StartMenu = wx.Window.NewControlId()
        wID_Tap = wx.Window.NewControlId()
        wID_Up01 = wx.Window.NewControlId()
        wID_Up10 = wx.Window.NewControlId()
        wID_Down01 = wx.Window.NewControlId()
        wID_Down10 = wx.Window.NewControlId()

        if ENABLE_VOL == True:
            wID_VolUp = wx.Window.NewControlId()
            wID_VolDown = wx.Window.NewControlId()

        menuStart = metronomeMenu.Append(wID_StartMenu,
                                         "&Start/Stop Clicking (Space)","")
        menuTap = metronomeMenu.Append(wID_Tap, "&Tap Tempo (Tab)\tCTRL-t","")
        metronomeMenu.AppendSeparator()
        menuBpmUp01 = metronomeMenu.Append(wID_Up01, "BPM up by  1 (Right)","")
        menuBpmUp10 = metronomeMenu.Append(wID_Up10, "BPM up by 10 (Up)","")
        metronomeMenu.AppendSeparator()
        menuBpmDown01 = metronomeMenu.Append(wID_Down01,
                                             "BPM down by  1 (Left)","")
        menuBpmDown10 = metronomeMenu.Append(wID_Down10,
                                             "BPM down by 10 (Down)","")

        if ENABLE_VOL == True:
            metronomeMenu.AppendSeparator()
            menuVolUp = metronomeMenu.Append(wID_VolUp,
                                             "Volume Up by  1\tCTRL-Up","")
            menuVolDown = metronomeMenu.Append(wID_VolDown,
                                               "Volume Down by  1\tCTRL-Down",
                                               "")

        menuBar.Append(fileMenu, "&File")
        menuBar.Append(metronomeMenu, "&Metronome")
        # now set the menubar to the mainWindow
        self.SetMenuBar(menuBar)

        box = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(box)

        ##### tempo related items
        self.BpmTitle =  wx.StaticText(self, label="Tempo",
                                       style = wx.ALIGN_CENTRE)

        self.TempoBox = wx.BoxSizer(wx.HORIZONTAL)

        self.BpmCtrl = wx.SpinCtrl(self, wx.Window.NewControlId())
        self.BpmCtrl.SetRange(BPM_MIN, BPM_MAX)
        self.TapBtn = wx.Button(self, wx.Window.NewControlId(),
                                label='Tap Tempo')

        self.TempoBox.Add(self.BpmCtrl, flag = wx.RIGHT, border = borderValue)
        self.TempoBox.Add(self.TapBtn, flag = wx.LEFT, border = borderValue)


        ##### time signature related items
        self.TimeSigTitle =  wx.StaticText(self, label="Meter",
                                           style = wx.ALIGN_CENTRE)

        self.TimeSigBox =  wx.BoxSizer(wx.HORIZONTAL)

        self.NumNoteCtrl = wx.SpinCtrl(self, wx.Window.NewControlId())
        self.NumNoteCtrl.SetRange(1, TICK_NUM)
        self.TimeSigSeparator =  wx.StaticText(self, label=" / ",
                                               style = wx.ALIGN_CENTRE)
        self.NValChoice = wx.Choice(self, wx.Window.NewControlId(),
                                       choices = ["1","2","4","8","16"])

        ##### click pattern related items
        self.PatternTitle =  wx.StaticText(self, label="Pattern",
                                           style = wx.ALIGN_CENTRE)
        self.PatternBox = wx.BoxSizer(wx.HORIZONTAL)

        self.TickList = []
            
        for i in range(0, TICK_NUM):
            newTick = wx.CheckBox(self, wx.Window.NewControlId(),
                                  label = str(i + 1),
                                  style = wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER)
            newTick.SetValue(wx.CHK_UNCHECKED)
            self.PatternBox.Add(newTick)
            self.TickList.append(newTick)
            self.Bind(wx.EVT_CHECKBOX, self.On_Tick_Change, newTick)

        ##### volume related items
        if ENABLE_VOL == True:
            self.VolTitle =  wx.StaticText(self, label="Volume",
                                           style = wx.ALIGN_CENTRE)
            self.Vol = wx.SpinCtrl(self, wx.Window.NewControlId())
            self.Vol.SetRange(0, 100)
            self.Vslider = wx.Slider(self, wx.Window.NewControlId())
            self.Vslider.SetRange(0, 100)
            self.Vslider.SetTick(1)
            self.Vslider.SetTickFreq(10)

        ##### start button
        wID_START = wx.Window.NewControlId()
        self.StartBtn = wx.ToggleButton(self, wID_START, label='Start')

        ##### metronome backend
        self.metronome1 = metronome(self, p = self.p,
                                    nval = noteValue[INIT_NVAL],
                                    bpm = init_bpm,
                                    accent = emphWavPath,
                                    normal = normWavPath,
                                    pattern = init_pattern)

        # initial value setting
        self.BpmCtrl.SetValue(init_bpm)
        self.NumNoteCtrl.SetValue(len(init_pattern))
        self.NValChoice.SetSelection(noteValueIndex[INIT_NVAL])
        if ENABLE_VOL == True:
            self.Vol.SetValue(init_vol)
            self.Vslider.SetValue(init_vol)
            self.Change_Vol(init_vol)

        self.Redraw_PatternBox(pattern = init_pattern) # pattern is set here

        self.TimeSigBox.Add(self.NumNoteCtrl)
        self.TimeSigBox.Add(self.TimeSigSeparator, wx.ALIGN_BOTTOM)
        self.TimeSigBox.Add(self.NValChoice)

        # adding parts to the "box" (vertical boxsizer)
        lst = [None,
               [self.BpmTitle, 0],
               [self.TempoBox, 0],
               None,
               [self.TimeSigTitle, 0],
               [self.TimeSigBox, 0],
               None,
               [self.PatternTitle, 0],
               [self.PatternBox, 0],
               None]
        
        if ENABLE_VOL == True:
            lstVol = [[self.VolTitle, 0],
                      [self.Vol, 0],
                      None,
                      [self.Vslider, wx.EXPAND],
                      None,
                      None]
            for each in lstVol:
                lst.append(each)
        
        lst.append([self.StartBtn, 0])

        for each in lst:
            if each == None:
                box.AddSpacer(borderValue)
            else:
                box.Add(each[0], flag = wx.LEFT | wx.RIGHT | each[1],
                        border = borderValue)
                

        #### setting up menu
        cmdList = [[self.On_menuStart, menuStart],
                   [self.Tapped, menuTap],
                   [self.On_menuBpmUp01, menuBpmUp01],
                   [self.On_menuBpmUp10, menuBpmUp10],
                   [self.On_menuBpmDown01, menuBpmDown01],
                   [self.On_menuBpmDown10, menuBpmDown10],
                   [self.OnAbout, menuAbout],
                   [self.OnClose, menuExit]]

        if ENABLE_VOL == True:
            cmdList.append([self.On_menuVolUp, menuVolUp])
            cmdList.append([self.On_menuVolDown, menuVolDown])

        #### binding menu to commands
        for item in cmdList:
            self.Bind(wx.EVT_MENU, item[0], item[1])

        self.Bind(wx.EVT_BUTTON, self.Tapped, self.TapBtn)
        self.Bind(wx.EVT_SPINCTRL, self.On_BpmCtrl_Change, self.BpmCtrl)
        self.Bind(wx.EVT_SPINCTRL, self.On_NumNoteCtrl_Change, self.NumNoteCtrl)
        self.Bind(wx.EVT_CHOICE, self.On_NValChoice_Change, self.NValChoice)
        if ENABLE_VOL == True:
            self.Bind(wx.EVT_SPINCTRL, self.On_Vol_Change, self.Vol)
            self.Bind(wx.EVT_SLIDER, self.On_Vsl_Change, self.Vslider)

        self.Bind(wx.EVT_TOGGLEBUTTON, self.Toggle_Sound, self.StartBtn)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        lst = [[wx.WXK_SPACE, wID_StartMenu],
               [wx.WXK_TAB, wID_Tap],
               [wx.WXK_RIGHT, wID_Up01],
               [wx.WXK_UP,    wID_Up10],
               [wx.WXK_LEFT,  wID_Down01],
               [wx.WXK_DOWN,  wID_Down10]]

        #### hotkeys
        HotKeyEntries = []
        for each in lst:
            e = wx.AcceleratorEntry()
            e.Set(wx.ACCEL_NORMAL, each[0], each[1])
            HotKeyEntries.append(e)

        HotKeyTable = wx.AcceleratorTable(HotKeyEntries)
        self.SetAcceleratorTable(HotKeyTable)

        #### ready.
        self.Layout() # in windows, you'd get corrupted frame without this.
        self.Show()

    def Redraw_PatternBox(self, length = None, pattern = None):
        p = []
        if pattern == None:
            if length != None:
                self.patternlen = length

            i = 0
            while i < self.patternlen:
                p.append(self.TickList[i].Get3StateValue())
                self.TickList[i].Show()
                i = i + 1
        else:
            p = pattern
            if length != None:
                self.patternlen = min(len(p), length)
            else:
                self.patternlen = len(p)
                
            i = 0
            while i < self.patternlen:
                self.TickList[i].Set3StateValue(p[i])
                self.TickList[i].Show()
                i = i + 1

        while i < TICK_NUM:
            self.TickList[i].Hide()
            i = i + 1
            
        if debug == True:
            print("redraw: pattern = " + str(p))
        self.metronome1.Set_Pattern(p)
        self.Layout()
        self.Show(True)

    def Tapped(self, e):
        current = time.perf_counter()
        if self.lastTap != None:
            diff = current - self.lastTap
            bpm = round(60/diff)
            if debug == True:
                print("diff :" + str(diff) + " BPM: " + str(bpm))
            self.BpmCtrl.SetValue(bpm)
            self.Set_Interval()

        self.lastTap = current

    def BpmChange(self, num = 1):
        self.BpmCtrl.SetValue(self.BpmCtrl.GetValue() + num)
        self.Set_Interval()

    def On_menuBpmUp01(self, e):
        self.BpmChange(1)
        self.Set_Interval()

    def On_menuBpmUp10(self, e):
        self.BpmChange(10)
        self.Set_Interval()

    def On_menuBpmDown01(self, e):
        self.BpmChange(-1)
        self.Set_Interval()

    def On_menuBpmDown10(self, e):
        self.BpmChange(-10)
        self.Set_Interval()

    def On_BpmCtrl_Change(self, e):
        self.Set_Interval()

    def On_NumNoteCtrl_Change(self, e):
        self.patternlen = self.NumNoteCtrl.GetValue()
        self.Redraw_PatternBox()

    def On_NValChoice_Change(self, e):
        self.Set_Interval()

    def Set_Interval(self):
        if debug == True:
            print("nval: "
                  + str(noteValue[self.NValChoice.GetString(self.NValChoice.GetSelection())])
                  + " + bpm: " + str(self.BpmCtrl.GetValue()))
        self.metronome1.Set_Interval(nval = noteValue[self.NValChoice.GetString(self.NValChoice.GetSelection())],
                                     bpm = self.BpmCtrl.GetValue())

    def On_Tick_Change(self, e):
        self.Redraw_PatternBox()

    def On_menuStart(self, e):
        self.StartBtn.SetValue(not self.StartBtn.GetValue())
        self.Toggle_Sound(e)

    def Toggle_Sound(self, e):
        if debug == True:
            print(e.GetId())
        if self.metronome1.Get_Status() == False:
            self.metronome1.start_sound()
            self.StartBtn.SetLabel("Stop")
        else:
            self.metronome1.stop_sound()
            self.StartBtn.SetLabel("Start")
        self.Show()

    if ENABLE_VOL == True:
        def Change_Vol(self, vol = None):
            self.metronome1.Set_Volume(vol)

        def On_Vol_Change(self, e):
            self.Change_Vol(self.Vol.GetValue()) 
            self.Vslider.SetValue(self.Vol.GetValue())

        def On_Vsl_Change(self, e):
            self.Change_Vol(self.Vslider.GetValue()) 
            self.Vol.SetValue(self.Vslider.GetValue())

        def On_menuVolUp(self, e):
            self.Vol.SetValue(self.Vol.GetValue() + 1)
            self.On_Vol_Change(e)

        def On_menuVolDown(self, e):
            self.Vol.SetValue(self.Vol.GetValue() - 1)
            self.On_Vol_Change(e)

    def OnAbout(self, e):
        dlg = wx.MessageBox("Simple Metronome by SY \n\n"
                            "built on WxPython and PyAudio\n\n"
                            "inspired by gtklick", programName)

    def OnClose(self, e):
        self.metronome1.stop_sound()
        self.p.terminate()
        e.Skip()
        exit(0) # for exit from menu
        
app = wx.App(False)
frame = mainWindow(None, programName)
app.MainLoop()
