import bpy

import time

from . import cm_channels as chan

from .cm_agent import Agent
from .cm_actions import getmotions


class Simulation:
    """The object that contains everything once the simulation starts"""
    def __init__(self):
        preferences = bpy.context.user_preferences.addons[__package__].preferences
        self.agents = {}
        self.framelast = 1
        self.compbrains = {}
        Noise = chan.Noise(self)
        Sound = chan.Sound(self)
        State = chan.State(self)
        World = chan.World(self)
        Crowd = chan.Crowd(self)
        Ground = chan.Ground(self)
        Formation = chan.Formation(self)
        Path = chan.Path(self)
        self.lvars = {"Noise": Noise,
                      "Sound": Sound,
                      "State": State,
                      "World": World,
                      "Crowd": Crowd,
                      "Ground": Ground,
                      "Formation": Formation,
                      "Path": Path}
        if preferences.show_debug_options:
            self.totalTime = 0
            self.totalFrames = 0

        self.actions = {}
        self.actionGroups = {}

    def actions(self):
        """Set up the actions"""
        self.actions, self.actionGroups = getmotions()

    def newagent(self, name, brain):
        """Set up an agent"""
        nGps = bpy.data.node_groups
        if brain in nGps and nGps[brain].bl_idname == "CrowdMasterTreeType":
            ag = Agent(name, nGps[brain], self)
            self.agents[name] = ag
        else:
            print("No such brain type:" + brain)

    def createAgents(self, group):
        """Set up all the agents at the beginning of the simulation"""
        for ty in group.agentTypes:
            for ag in ty.agents:
                self.newagent(ag.name, ty.name)

    def step(self, scene):
        """Called when the next frame is moved to"""
        preferences = bpy.context.user_preferences.addons[__package__].preferences
        if preferences.show_debug_options:
            t = time.time()
            print("NEWFRAME", bpy.context.scene.frame_current)
        for agent in self.agents.values():
            for tag in agent.access["tags"]:
                for channel in self.lvars:
                    if tag[:len(channel)] == channel:
                        self.lvars[channel].register(agent, tag[len(channel):],
                                                     agent.access["tags"][tag])
        # TODO registering channels would be much more efficient if done
        # straight after the agent is evaluated.
        for a in self.agents.values():
            a.step()
        for a in self.agents.values():
            a.apply()
        for chan in self.lvars.values():
            chan.newframe()
        if preferences.show_debug_options:
            newT = time.time()
            print("time", newT - t)
            self.totalTime += newT - t
            self.totalFrames += 1
            print("spf", self.totalTime/self.totalFrames)  # seconds per frame

    def frameChangeHandler(self, scene):
        """Given to Blender to call whenever the scene moves to a new frame"""
        if self.framelast+1 == bpy.context.scene.frame_current:
            self.framelast = bpy.context.scene.frame_current
            self.step(scene)

    def frameChangeHighlight(self, scene):
        """Not unregistered when simulation stopped"""
        if self.framelast >= bpy.context.scene.frame_current:
            active = bpy.context.active_object
            if active and active in self.agents:
                self.agents[bpy.context.active_object.name].highLight()

    def startFrameHandler(self):
        """Add self.frameChangeHandler to the Blender event handlers"""
        preferences = bpy.context.user_preferences.addons[__package__].preferences
        if preferences.show_debug_options:
            self.totalTime = 0
            self.totalFrames = 0
            print("Registering frame change handler")
        if self.frameChangeHandler in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.remove(self.frameChangeHandler)
        bpy.app.handlers.frame_change_pre.append(self.frameChangeHandler)
        if self.frameChangeHighlight not in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.append(self.frameChangeHighlight)

    def stopFrameHandler(self):
        """Remove self.frameChangeHandler from Blenders event handlers"""
        preferences = bpy.context.user_preferences.addons[__package__].preferences
        if self.frameChangeHandler in bpy.app.handlers.frame_change_pre:
            if preferences.show_debug_options:
                print("Unregistering frame change handler")
            bpy.app.handlers.frame_change_pre.remove(self.frameChangeHandler)
