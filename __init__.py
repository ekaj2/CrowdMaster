bl_info = {
    "name": "CrowdMaster",
    "author": "Peter Noble, John Roper, Patrick Crawford",
    "version": (1, 2, 0),
    "blender": (2, 78, 0),
    "location": "Node Editor > CrowdMaster",
    "description": "Blender crowd simulation",
    "warning": "",
    "wiki_url": "http://jmroper.com/crowdmaster/docs/",
    "tracker_url": "https://github.com/johnroper100/CrowdMaster/issues",
    "category": "Simulation"
}

import bpy
from bpy.props import PointerProperty, BoolProperty, StringProperty
from bpy.types import PropertyGroup, UIList, Panel, Operator

from . import cm_prefs
from . icon_load import register_icons, unregister_icons, cicon
from . import addon_updater_ops
from . cm_graphics import cm_nodeHUD
from . cm_graphics . cm_nodeHUD import update_hud_text
from . cm_graphics . utils import cm_redrawAll

# =============== GROUPS LIST START ===============#


class SCENE_UL_group(UIList):
    """for drawing each row"""
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname):
        layout.label(item.name)
        layout.label(str(item.totalAgents) + " | " + item.groupType)
        layout.label("Frozen" if item.freezePlacement else "Unlocked")


class SCENE_UL_agent_type(UIList):
    """for drawing each row"""
    use_filter_sort_alpha = True

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname):
        layout.label(item.name)
        layout.label(str(len(item.agents)))


class SCENE_OT_cm_groups_reset(Operator):
    """Delete a group and all the agent in it (including the agents geo)"""
    bl_idname = "scene.cm_groups_reset"
    bl_label = "Reset Group"

    groupName = StringProperty()

    def execute(self, context):
        scene = context.scene
        
        group = scene.cm_groups.get(self.groupName)
        for obj in bpy.context.selected_objects:
            obj.select = False
        for agentType in group.agentTypes:
            for agent in agentType.agents:
                if group.groupType == "auto":
                    if group.freezePlacement:
                        if agent.name in scene.objects:
                            scene.objects[agent.name].animation_data_clear()
                    else:
                        if agent.geoGroup in bpy.data.groups:
                            for obj in bpy.data.groups[agent.geoGroup].objects:
                                obj.select = True
                            bpy.data.groups.remove(bpy.data.groups[agent.geoGroup],
                                                   do_unlink=True)
                elif group.groupType == "manual":
                    if agent.name in scene.objects:
                        scene.objects[agent.name].animation_data_clear()
        if not group.freezePlacement:
            bpy.ops.object.delete(use_global=True)
            groupIndex = scene.cm_groups.find(self.groupName)
            scene.cm_groups.remove(groupIndex)
        
        newhudText = "Group {} reset!".format(self.groupName)
        update_hud_text(newhudText)
        cm_redrawAll()

        return {'FINISHED'}


# =============== GROUPS LIST END ===============#

# =============== AGENTS LIST START ===============#


class SCENE_OT_cm_agent_add(Operator):
    bl_idname = "scene.cm_agent_add"
    bl_label = "Add single agent to cm agents list"

    agentName = StringProperty()
    brainType = StringProperty()
    groupName = StringProperty()
    geoGroupName = StringProperty()

    def execute(self, context):
        scene = context.scene

        if scene.cm_groups.find(self.groupName) == -1:
            newGroup = scene.cm_groups.add()
            newGroup.name = self.groupName
            newGroup.groupType = "auto"
        group = scene.cm_groups.get(self.groupName)
        if group.groupType == "manual" or group.freezePlacement:
            return {'CANCELLED'}
        ty = group.agentTypes.find(self.brainType)
        if ty == -1:
            at = group.agentTypes.add()
            at.name = self.brainType
            ty = group.agentTypes.find(at.name)
        agentType = group.agentTypes[ty]
        newAgent = agentType.agents.add()
        newAgent.name = self.agentName
        newAgent.geoGroup = self.geoGroupName
        group.totalAgents += 1
        return {'FINISHED'}


class SCENE_OT_cm_agent_add_selected(Operator):
    bl_idname = "scene.cm_agent_add_selected"
    bl_label = "Create Manual Agents"

    groupName = StringProperty(name="New Group Name")
    brainType = StringProperty(name="Brain Type")

    def execute(self, context):
        scene = context.scene

        if self.groupName.strip() == "" or self.brainType.strip() == "":
            return {'CANCELLED'}
        if scene.cm_groups.find(self.groupName) == -1:
            newGroup = scene.cm_groups.add()
            newGroup.name = self.groupName
            newGroup.groupType = "manual"
        group = scene.cm_groups.get(self.groupName)
        if group.groupType == "auto":
            return {'CANCELLED'}
        ty = group.agentTypes.find(self.brainType)
        if ty == -1:
            at = group.agentTypes.add()
            at.name = self.brainType
            ty = group.agentTypes.find(at.name)
        agentType = group.agentTypes[ty]
        for obj in context.selected_objects:
            newAgent = agentType.agents.add()
            newAgent.name = obj.name
            group.totalAgents += 1
        
        newhudText = "Manual Agents {} Created!".format(self.groupName)
        update_hud_text(newhudText)
        cm_redrawAll()

        return {'FINISHED'}


# =============== AGENTS LIST END ===============#


# =============== SIMULATION START ===============#


class SCENE_OT_cm_start(Operator):
    """Start the CrowdMaster agent simulation."""
    bl_idname = "scene.cm_start"
    bl_label = "Start Simulation"

    def execute(self, context):
        scene = context.scene

        preferences = context.user_preferences.addons[__package__].preferences
        if (bpy.data.is_dirty) and (preferences.ask_to_save):
            self.report({'ERROR'}, "You must save your file first!")
            return {'CANCELLED'}
        
        newhudText = "Simulation Running!"
        update_hud_text(newhudText)
        cm_redrawAll()

        scene.frame_current = scene.frame_start

        global sim
        if "sim" in globals():
            sim.stopFrameHandler()
            del sim
        sim = Simulation()
        sim.actions()

        for group in scene.cm_groups:
            sim.createAgents(group)

        sim.startFrameHandler()

        if preferences.play_animation:
            bpy.ops.screen.animation_play()

        return {'FINISHED'}


class SCENE_OT_cm_stop(Operator):
    """Stop the CrowdMaster agent simulation."""
    bl_idname = "scene.cm_stop"
    bl_label = "Stop Simulation"

    def execute(self, context):
        preferences = context.user_preferences.addons[__package__].preferences
        if preferences.play_animation:
            bpy.ops.screen.animation_cancel()

        global sim
        if "sim" in globals():
            sim.stopFrameHandler()
        
        newhudText = "Simulation Stopped!"
        update_hud_text(newhudText)
        cm_redrawAll()

        return {'FINISHED'}

# =============== SIMULATION END ===============#

global initialised
initialised = False


class SCENE_PT_CrowdMaster(Panel):
    """Creates CrowdMaster Panel in the node editor."""
    bl_label = "Main"
    bl_idname = "SCENE_PT_CrowdMaster"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'TOOLS'
    bl_category = "CrowdMaster"

    @classmethod
    def poll(self, context):
        try:
            return bpy.context.space_data.tree_type == 'CrowdMasterTreeType', bpy.context.space_data.tree_type == 'CrowdMasterGenTreeType'
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        preferences = context.user_preferences.addons[__package__].preferences

        row = layout.row()
        row.scale_y = 1.5
        if preferences.use_custom_icons:
            row.operator(SCENE_OT_cm_start.bl_idname, icon_value=cicon('start_sim'))
        else:
            row.operator(SCENE_OT_cm_start.bl_idname, icon='FILE_TICK')

        row = layout.row()
        row.scale_y = 1.25
        if preferences.use_custom_icons:
            row.operator(SCENE_OT_cm_stop.bl_idname, icon_value=cicon('stop_sim'))
        else:
            row.operator(SCENE_OT_cm_stop.bl_idname, icon='CANCEL')

        row = layout.row()
        row.separator()

        row = layout.row()
        if not scene.show_utilities:
            row.prop(scene, "show_utilities", icon="RIGHTARROW", text="Utilities")
        else:
            row.prop(scene, "show_utilities", icon="TRIA_DOWN", text="Utilities")

            box = layout.box()
            row = box.row()
            row.scale_y = 1.5
            row.operator("scene.cm_place_deferred_geo", icon="EDITMODE_VEC_HLT")

            box = layout.box()
            row = box.row()
            row.prop(scene, "nodeTreeType")

            row = box.row()
            row.prop(scene, "append_to_tree")

            if scene.append_to_tree:
                row = box.row()
                row.prop_search(scene, "node_tree_name", bpy.data, "node_groups")

            row = box.row()
            row.scale_y = 1.5
            if preferences.use_custom_icons:
                row.operator("scene.cm_setup_sample_nodes", icon_value=cicon('instant_setup'))
            else:
                row.operator("scene.cm_setup_sample_nodes", icon="NODETREE")

            box = layout.box()
            row = box.row()
            row.scale_y = 1.5
            row.operator("scene.cm_convert_to_bound_box", icon="BBOX")

            box = layout.box()
            row = box.row()
            row.label("You must have the Simplify Curves addon enabled and an agent selected.")
            row = box.row()
            row.scale_y = 1.5
            row.operator("graph.simplify", icon="IPO")


class SCENE_PT_CrowdMasterAgents(Panel):
    """Creates CrowdMaster agent panel in the node editor."""
    bl_label = "Agents"
    bl_idname = "SCENE_PT_CrowdMasterAgents"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'TOOLS'
    bl_category = "CrowdMaster"

    @classmethod
    def poll(self, context):
        try:
            return bpy.context.space_data.tree_type == 'CrowdMasterTreeType', bpy.context.space_data.tree_type == 'CrowdMasterGenTreeType'
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        global initialised
        if not initialised:
            initialised = True
            initialise()
        layout = self.layout
        scene = context.scene
        preferences = context.user_preferences.addons[__package__].preferences

        row = layout.row()
        row.label("Group name")
        row.label("Number | origin")
        row.label("Status")

        layout.template_list("SCENE_UL_group", "", scene,
                             "cm_groups", scene, "cm_groups_index")

        layout.separator()

        if not scene.cm_view_details:
            layout.prop(scene, "cm_view_details", icon='RIGHTARROW')
        else:
            layout.prop(scene, "cm_view_details", icon='TRIA_DOWN')

            box = layout.box()

            index = scene.cm_groups_index
            if 0 <= index < len(scene.cm_groups):
                group = scene.cm_groups[index]

                box.template_list("SCENE_UL_agent_type", "", group,
                                  "agentTypes", scene, "cm_view_details_index")

                if group.name == "cm_allAgents":
                    box.label("cm_allAgents: To freeze use Add To Group node")
                else:
                    box.prop(group, "freezePlacement")

                if preferences.use_custom_icons:
                    op = box.operator(SCENE_OT_cm_groups_reset.bl_idname, icon_value=cicon('reset'))
                else:
                    op = box.operator(SCENE_OT_cm_groups_reset.bl_idname)
                op.groupName = group.name
            else:
                box.label("No group selected")


class SCENE_PT_CrowdMasterManualAgents(Panel):
    """Creates CrowdMaster agent panel in the node editor."""
    bl_label = "Manual Agents"
    bl_idname = "SCENE_PT_CrowdMasterManualAgents"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'TOOLS'
    bl_category = "CrowdMaster"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        try:
            return bpy.context.space_data.tree_type == 'CrowdMasterTreeType', bpy.context.space_data.tree_type == 'CrowdMasterGenTreeType'
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        preferences = context.user_preferences.addons[__package__].preferences

        layout.prop(scene.cm_manual, "groupName", text="Group Name")
        layout.prop(scene.cm_manual, "brainType", text="Brain Type")
        if preferences.use_custom_icons:
            op = layout.operator(SCENE_OT_cm_agent_add_selected.bl_idname, icon_value=cicon('agents'))
        else:
            op = layout.operator(SCENE_OT_cm_agent_add_selected.bl_idname)
        op.groupName = "cm_" + scene.cm_manual.groupName
        op.brainType = scene.cm_manual.brainType


# documentation links
prefix = "http://jmroper.com/crowdmaster/docs/"
documentation_mapping = (
    # OPERATORS
    # toolbar
    ("bpy.ops.scene.cm_start", "simulation/toolbar/main.html#main"),
    ("bpy.ops.scene.cm_stop", "simulation/toolbar/main.html#main"),
    ("bpy.ops.scene.cm_place_deferred_geo", "getting_started/utilities/place_defered_geo.html#place-defered-geometry"),
    ("bpy.ops.scene.cm_setup_sample_nodes", "getting_started/utilities/sample_node_setups.html#sample-node-setups"),
    ("bpy.ops.scene.cm_convert_to_bound_box", "getting_started/utilities/conv_to_bound_box.html#convert-selected-to-bounding-box"),
    ("bpy.ops.scene.cm_groups_reset", "simulation/toolbar/agents.html?highlight=groups%20reset#status"),
    ("bpy.ops.scene.cm_agent_add_selected", "simulation/toolbar/manual_agents.html#manual-agents"),
    ("bpy.ops.scene.cm_actions_populate", "simulation/toolbar/actions.html#actions"),
    ("bpy.ops.scene.cm_actions_remove", "simulation/toolbar/actions.html#actions"),
    ("bpy.ops.scene.cm_agents_move", "simulation/toolbar/actions.html#actions"),
    ("bpy.ops.scene.cm_events_populate", "simulation/toolbar/events.html#events"),
    ("bpy.ops.scene.cm_events_remove", "simulation/toolbar/events.html#events"),
    ("bpy.ops.scene.cm_events_move", "simulation/toolbar/events.html#events"),
    ("bpy.ops.scene.cm_paths_populate", "simulation/toolbar/paths.html#paths"),
    ("bpy.ops.scene.cm_paths_remove", "simulation/toolbar/paths.html#paths"),
    # TODO - nodes

    # PROPS
    # TODO - toolbar
    ("bpy.types.Scene.nodeTreeType", "getting_started/utilities/sample_node_setups.html#node-tree-type"),
    # TODO - nodes
)


def doc_map():
    dm = (prefix, documentation_mapping)
    return dm


def register():
    # register custom documentation mapping
    bpy.utils.register_manual_map(doc_map)

    register_icons()
    cm_nodeHUD.register()

    addon_updater_ops.register(bl_info)
    cm_prefs.register()

    bpy.utils.register_class(SCENE_UL_group)
    bpy.utils.register_class(SCENE_UL_agent_type)
    bpy.utils.register_class(SCENE_OT_cm_groups_reset)
    bpy.utils.register_class(SCENE_OT_cm_agent_add)
    bpy.utils.register_class(SCENE_OT_cm_agent_add_selected)
    bpy.utils.register_class(SCENE_OT_cm_start)
    bpy.utils.register_class(SCENE_OT_cm_stop)
    bpy.utils.register_class(SCENE_PT_CrowdMaster)
    bpy.utils.register_class(SCENE_PT_CrowdMasterAgents)
    bpy.utils.register_class(SCENE_PT_CrowdMasterManualAgents)

    global action_register
    from .cm_actions import action_register
    global action_unregister

    global event_register
    from .cm_events import event_register
    global event_unregister

    from . import cm_blenderData
    cm_blenderData.registerTypes()

    global cm_bpyNodes
    from . import cm_bpyNodes
    cm_bpyNodes.register()

    global cm_generation
    from . import cm_generation
    cm_generation.register()

    global cm_utilities
    from . import cm_utilities
    cm_utilities.register()

    action_register()
    event_register()

    global cm_channels
    from . import cm_channels
    cm_channels.register()



def initialise():
    global Simulation


def unregister():
    unregister_icons()

    bpy.utils.unregister_class(SCENE_UL_group)
    bpy.utils.unregister_class(SCENE_UL_agent_type)
    bpy.utils.unregister_class(SCENE_OT_cm_groups_reset)
    bpy.utils.unregister_class(SCENE_OT_cm_agent_add)
    bpy.utils.unregister_class(SCENE_OT_cm_agent_add_selected)
    bpy.utils.unregister_class(SCENE_OT_cm_start)
    bpy.utils.unregister_class(SCENE_OT_cm_stop)
    bpy.utils.unregister_class(SCENE_PT_CrowdMaster)
    bpy.utils.unregister_class(SCENE_PT_CrowdMasterAgents)
    bpy.utils.unregister_class(SCENE_PT_CrowdMasterManualAgents)

    action_unregister()
    event_unregister()
    from . import cm_blenderData
    cm_blenderData.unregisterAllTypes()

    addon_updater_ops.unregister()
    cm_bpyNodes.unregister()
    cm_generation.unregister()
    cm_utilities.unregister()
    cm_prefs.unregister()
    
    cm_nodeHUD.unregister()

    cm_channels.unregister()

    if "sim" in globals():
        if sim.frameChangeHighlight in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.remove(sim.frameChangeHighlight)

    # unregister custom documentation mapping
    bpy.utils.unregister_manual_map(doc_map)

if __name__ == "__main__":
    register()
