# Spy-Metronome
Simple metronome built on wxPython and PyAudio, and inspired by gtklick (http://das.nasophon.de/klick/)

Basically I live in linux world, and there, I am satisfied with gtklick for my daily use.

When I travel to the windows world, one frustration is that I cannot find free, flexible and ACCURATE
metronome. So I try to write a python metronome, in my capacity, as accurate and flexible as gtklick.

It is somehow customizable, but all the customization should be done by directly editing the top part of
the program. Most probably you will need to change the wav files' path. Hopefully you will find how to do
it when you read the program (currently the paths are set in line 57 and 58).

You need to first setup python, wxpython numpy and pyaudio (any others?) in order for this program to work.

wav files are taken from klick project, and their copyright notice are written in the program.

Hope you'll find it useful.
