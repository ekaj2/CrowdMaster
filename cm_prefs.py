import bpy
import os
from bpy.types import AddonPreferences
from bpy.props import *
from . import addon_updater_ops
from . icon_load import cicon


class CMSavePrefs(bpy.types.Operator):
    """Save the CrowdMaster preferences """
    bl_idname = "scene.cm_save_prefs"
    bl_label = "Save Settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.wm.save_userpref()

        return {'FINISHED'}


class CMPreferences(AddonPreferences):
    bl_idname = __package__
    scriptdir = bpy.path.abspath(os.path.dirname(__file__))

    auto_check_update = BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
        )

    updater_intrval_months = IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
        )
    updater_intrval_days = IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=14,
        min=0,
        )
    updater_intrval_hours = IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
        )
    updater_intrval_minutes = IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
        )

    use_custom_icons = BoolProperty(
        name="Use Custom Icons",
        description="Chose whether to use the custom icons that come with the addon or not.",
        default=True,
        )

    show_debug_options = BoolProperty(
        name="Show Debug Options",
        description="Chose whether to show the debug options in the interface. This also enables debug mode.",
        default=False,
        )
    
    show_node_hud = BoolProperty(
        name="Show Node Editor HUD",
        description="Chose whether to show the CrowdMaster text HUD in the node editor.",
        default=False,
        )
    
    show_sim_data = BoolProperty(
        name="Show Detailed Simulation Data",
        description="Chose whether to show detailed data while running a simulation or operator in the node tree hud. Warning, this makes each operator take longer.",
        default=False,
        )

    play_animation = BoolProperty(
        name="Start Animation Automatically",
        description="Start and stop the animation automatically when the start and stop sim buttons are pressed.",
        default=True,
        )

    ask_to_save = BoolProperty(
        name="Ask To Save",
        description="Chose whether the current file has to be saved or not before simulating or generating.",
        default=True,
        )

    use_node_color = BoolProperty(
        name="Use Node Color",
        description="Choose whether or not to show the node info colors while simulating.",
        default=True,
        )

    prefs_tab_items = [
        ("GEN", "General Settings", "General settings for the addon."),
        ("UPDATE", "Addon Update Settings", "Settings for the addon updater.")]

    prefs_tab = EnumProperty(name="Options Set", items=prefs_tab_items)

    def draw(self, context):
        layout = self.layout
        preferences = context.user_preferences.addons[__package__].preferences

        row = layout.row()
        row.prop(preferences, "prefs_tab", expand=True)

        if preferences.prefs_tab == "GEN":
            row = layout.row()
            row.prop(preferences, 'use_custom_icons', icon_value=cicon('plug'))

            if preferences.use_custom_icons:
                row.prop(preferences, 'play_animation', icon_value=cicon('shuffle'))
            else:
                row.prop(preferences, 'play_animation', icon='ACTION')

            row = layout.row()
            row.prop(preferences, 'ask_to_save', icon='SAVE_AS')
            row.prop(preferences, 'use_node_color', icon='COLOR')

            row = layout.row()
            row.prop(preferences, 'show_node_hud', icon='SORTALPHA')
            
            if preferences.show_node_hud:
                row.prop(preferences, 'show_sim_data', icon='OUTLINER_DATA_FONT')
                row = layout.row()
    
            if preferences.use_custom_icons:
                row.prop(preferences, 'show_debug_options', icon_value=cicon('code'))
            else:
                row.prop(preferences, 'show_debug_options', icon='RECOVER_AUTO')

        if preferences.prefs_tab == "UPDATE":
            layout.row()
            addon_updater_ops.update_settings_ui(self, context)

        row = layout.row(align=True)
        row.scale_y = 1.25
        row.operator("scene.cm_save_prefs", icon='SAVE_PREFS')
        row.operator("wm.url_open", text="Email Us", icon='URL').url = "mailto:crowdmaster@jmroper.com"


def register():
    bpy.utils.register_class(CMSavePrefs)
    bpy.utils.register_class(CMPreferences)


def unregister():
    bpy.utils.unregister_class(CMSavePrefs)
    bpy.utils.unregister_class(CMPreferences)
