"""
    Disclaimer
    I barely know how to write Python and any 
    scripting experience I have is from JavaScript, 
    GDScript(Godot script) and Lua

    Appologies if the formatting is awful and it
    hurts to look at
"""
bl_info = {
    "name"    : "PBR Bake Tools",
    "blender" : (2,83,0),
    "version" : (1,2),
    "category": "Material",
    "author" : "Merow",
    "doc_url" : "https://github.com/TehMerow/PBR_Bake_Tools/wiki/Tutorial",
    "location" : "Node Editor > Properties Panel",
    "description" : "Aids in PBR Texture Baking"
}

import bpy

from bpy.utils import (
    register_class,
    unregister_class
)
from bpy.app.handlers import persistent
from bpy.types import AddonPreferences


COLOR_SPACE_SRGB = "sRGB"
COLOR_SPACE_NON_COLOR = "Non-Color"

image_names_full = [
    {"name": "base_color", "colorspace": COLOR_SPACE_SRGB},
    {"name": "ambient_occlusion", "colorspace": COLOR_SPACE_SRGB},
    {"name": "specular", "colorspace": COLOR_SPACE_NON_COLOR},
    {"name": "metalic", "colorspace": COLOR_SPACE_NON_COLOR},
    {"name": "roughness", "colorspace": COLOR_SPACE_NON_COLOR},
    {"name": "normal", "colorspace": COLOR_SPACE_NON_COLOR},
    {"name": "height", "colorspace": COLOR_SPACE_NON_COLOR},
]

image_names_orm = [
    {"name": "base_color", "colorspace": COLOR_SPACE_SRGB},
    {"name": "specular", "colorspace": COLOR_SPACE_NON_COLOR},
    {"name": "ORM", "colorspace": COLOR_SPACE_NON_COLOR},
    {"name": "normal", "colorspace": COLOR_SPACE_NON_COLOR},
    {"name": "height", "colorspace": COLOR_SPACE_NON_COLOR}
]

render_settings_pre_bake_scene_setup = {
    "samples" : 32,
    "tile_size" : {
        'x' : 16,
        'y' : 16
    },
    "bake_margin" : 8,
    "clear_image" : True
}


bake_slots_input = [
    ("base_color", "Base Color", "The Base color or Albedo"),
    ("ao", "Ambient Occlusion", "The Ambient Occlusion"),
    ("metalic", "Metalic", "The Metalic Slot"),
    ("specular", "Specular", "Specular F0 Slot"),
    ("rough", "Roughness", "Roughness slot"),
    ("sheen", "Sheen", "Sheen slot"),
    ("tint", "Sheen Tint", "Sheen Tint Slot"),
    ("clearcoat", "Clearcoat", "Clearcoat Slot"),
    ("clear_rough", "Clearcoat Roughness", "Clearcoat Roughness slot"),
    ("emit", "Emission", "Emission Slot"),
    ("emit_str", "Emission Strength", "Emission Strength Slot"),
    ("alpha", "Alpha", "Alpha Slot"),
    ("transmission", "Transmission", "Transmision slot"),
    ("transmission_rough", "Transmission Roughness", "Transmission Roughness Slot"),
    ("height", "Heightmap", "Heightmap, blender can't do this very well"),
    ("normal", "NORMAL", "BSDF output for normal map"),
]

bake_slots_output =  [
    ("base_color", "Base Color", "The Base color or Albedo"),
    ("ao", "Ambient Occlusion", "The Ambient Occlusion"),
    ("metalic", "Metalic", "The Metalic Slot"),
    ("specular", "Specular", "Specular F0 Slot"),
    ("rough", "Roughness", "Roughness slot"),
    ("sheen", "Sheen", "Sheen slot"),
    ("tint", "Sheen Tint", "Sheen Tint Slot"),
    ("clearcoat", "Clearcoat", "Clearcoat Slot"),
    ("clear_rough", "Clearcoat Roughness", "Clearcoat Roughness slot"),
    ("emit", "Emission", "Emission Slot"),
    ("emit_str", "Emission Strength", "Emission Strength Slot"),
    ("alpha", "Alpha", "Alpha Slot"),
    ("transmission", "Transmission", "Transmision slot"),
    ("transmission_rough", "Transmission Roughness", "Transmission Roughness Slot"),
    ("orm", "ORM", "ORM slot. Red Channel = Occlusion, Green Channel = Roughness, Blue channel = Metalic"),
    ("height", "Heightmap", "Heightmap, blender can't do this very well"),
    ("normal", "NORMAL", "BSDF output for normal map"),
]

def create_image_texture(name, size, context):
    """
        Creates an image texture
        names the image texture
        stores it into memory
    """
    active_mat = context.active_object.active_material.name  
    mat_name = active_mat + "-" + name['name']
    
    bpy.ops.image.new(
        name= mat_name, 
        width=size,
        height=size,
        color=[0,0,0,0],
        alpha=True,
        generated_type="BLANK",
    )
    bpy.data.images[mat_name].colorspace_settings.name = name['colorspace']


# Creates Image textures based on the image_names_full list
# used for creating default pbr layout
def create_image_textures_default(size, context):
    for name in image_names_full:
        create_image_texture(name, size, context)

    
# Creates Image textures based on the image_names_full list
# used for creating ORM pbr layout
def create_image_textures_orm(size, context):
    for name in image_names_orm:
        create_image_texture(name, size, context)


# creates image texture node
# sets the name of the node
# sets the position of the name
# sets the image of the node
def create_texture_node(image, name, position, context):
    texture_node = context.active_object.active_material.node_tree.nodes.new("ShaderNodeTexImage")
    texture_node.name = name
    texture_node.label = "PBR_Bake: " + name
    texture_node.location = position
    texture_node.image = image
 

# Helper for rordering the texture images 
# so the follow the same order of the pbr slots
def reorder_images(context, pbr_type):

    op_images = list()

    for image in bpy.data.images:
        mat_name = context.active_object.active_material.name

        if image.name.find(mat_name) == -1:
            continue
        
        op_images.append(image)

    image_order = list()

    if pbr_type == 'DEFAULT':
        image_order = [1, 0,3, 6, 5, 4, 2]
    elif pbr_type == 'ORM':
        image_order = [0, 4, 3, 2, 1]
        pass

    op_images = [op_images[i] for i in image_order]

    return op_images


# reorders the images
# sets the start pos of the ImageTexture Node
# breaks out of loop if the texture name 
# does not include the name of the material
# creates the textures 
# increments the start pos
def create_texture_nodes(context, pbr_type):
    ordered_images = reorder_images(context, pbr_type)

    material_output_node_position = context.active_object.active_material.node_tree.nodes['Material Output'].location
    bpy.ops.node.select_all(action='TOGGLE')
    start_pos = [material_output_node_position[0] + 256, material_output_node_position[1] + 512]
    for texture in ordered_images:
        mat_name = context.active_object.active_material.name
        if texture.name.find(mat_name) == -1:
            continue

        create_texture_node(texture, texture.name, start_pos, context)


        start_pos[1] += -256
    
    # Join the generated textures into a frame
    bpy.ops.node.join()

    # Set the name and label of the frame
    context.active_object.active_material.node_tree.nodes['Frame'].label = "Bake Textures"
    context.active_object.active_material.node_tree.nodes['Frame'].name = "Bake Textures"

# Function used inside of the CreateBasicMaterialTextures class
def _create_textures(type, texture_size, context):
    if type == "DEFAULT":
        create_image_textures_default(size=texture_size, context=context)
        create_texture_nodes(context=context, pbr_type='DEFAULT')
    elif type == "ORM":
        create_image_textures_orm(size=texture_size, context=context)
        create_texture_nodes(context=context, pbr_type='ORM')


# Sets the bake settings for quicker baking
def _set_bake_settings(context, texture_size):
    scene = context.scene

    # cache old settings

    render_settings_pre_bake_scene_setup['samples'] = scene.cycles.samples
    render_settings_pre_bake_scene_setup['tile_size']['x'] = scene.render.tile_x
    render_settings_pre_bake_scene_setup['tile_size']['y'] = scene.render.tile_y

    # set items with new stuff
    
    scene.cycles.samples = 1
    scene.render.tile_x = texture_size
    scene.render.tile_y = texture_size
    
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False

   
# Get the PBR_Bake node inside of the node tree 
# so that the link_slot function has access to it
def get_bake_node(ctx):
    obj = bpy.context.active_object
    mat = obj.material_slots[0].material
    nodes = mat.node_tree.nodes["PBR_Bake"]
    mat_output = mat.node_tree.nodes["Material Output"]

    return {
        "tree" : mat.node_tree,
        "nodes" : nodes,
        "mat_output" : mat_output
    }

# Allows linking of outputs of the PBR_Bake node
def link_slot(ctx, slot_name):
    # keys = get_bake_node(ctx)['nodes'].outputs.keys()
    
    bake_node = get_bake_node(ctx)['nodes']
    tree = get_bake_node(ctx)['tree']
    mat_output = get_bake_node(ctx)['mat_output'].inputs["Surface"]    
    outputs = bake_node.outputs[slot_name]
    
    tree.links.new(outputs, mat_output)


def link_to_bake_node(ctx, selected_slot):
    bake_node = get_bake_node(ctx)['nodes']
    tree = get_bake_node(ctx)['tree']
    inputs = bake_node.inputs[selected_slot]

    selected_node = ctx.active_object.active_material.node_tree.nodes.active.outputs[0]

    tree.links.new(selected_node, inputs)
    pass


# Very Big function for creating the PBR_Bake node group

@persistent
def create_the_stuff():
    pbr_bake_group = bpy.data.node_groups.new("PBR_Bake", "ShaderNodeTree")
    pbr_bake_group.name = "PBR_Bake"
    """ 
    tuple order:
        Name, InputType, OutputType, ShaderType, default value
    """
    io = [
        ("Base Color", "NodeSocketColor", "NodeSocketShader", "ShaderNodeEmission", (1.0, 1.0, 1.0, 1.0)),
        ("AO", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 1.0),
        ("Metalic", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 0.0),
        ("Specular", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 0.5),
        ("Roughness", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 0.5),
        ("Sheen", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 0.0),
        ("Sheen Tint", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 0.0),
        ("Clearcoat", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 0.0),
        ("Clearcoat Roughness", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 0.2),
        ("Emission", "NodeSocketColor", "NodeSocketShader", "ShaderNodeEmission",(0.0,0.0,0.0,1.0)),
        ("Emission Strength", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission",.0),
        ("Alpha", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 1.0),
        ("Transmission", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", .0),
        ("Transmission Roughness", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", .0),
        ("Normal", "NodeSocketVector", "NodeSocketShader", "ShaderNodeBsdfDiffuse",(0.0,0.0,0.0)),
        ("Heightmap", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", .0),


    ]


    # Create Group Inputs
    group_inputs = pbr_bake_group.nodes.new("NodeGroupInput")
    group_inputs.location = (-350, 0)

    
    for socket in io:
        pbr_bake_group.inputs.new(socket[1], socket[0]).default_value = socket[4]


    # create emission nodes
    def create_emit_node(type, pos, name):
        node_emit = pbr_bake_group.nodes.new(type)
        node_emit.name = name
        node_emit.label = name
        node_emit.location = (100, pos)

        return node_emit

    # Create group outputs

    group_outputs = pbr_bake_group.nodes.new("NodeGroupOutput")
    group_outputs.location = (300, 0)

    for socket in io:
        pbr_bake_group.outputs.new(socket[2], socket[0])

    # creates the orm input sockets, combineRGB node and
    # emission node then links them up
    def create_orm():
        # create orm output socket
        pbr_bake_group.outputs.new("NodeSocketShader", "ORM")

        # create emit node
        emit_node = create_emit_node("ShaderNodeEmission", -1500, "ORM")

        # create combine rgb node
        node_combine_rgb = pbr_bake_group.nodes.new("ShaderNodeCombineRGB")
        node_combine_rgb.location = (100, -2000)
        
        # make links between group input and combine rbg node
        pbr_bake_group.links.new(group_inputs.outputs[1], node_combine_rgb.inputs[0])
        pbr_bake_group.links.new(group_inputs.outputs[4], node_combine_rgb.inputs[1])
        pbr_bake_group.links.new(group_inputs.outputs[2], node_combine_rgb.inputs[2])

        # Connect combinergb node to emission node
        # then connect emmision node to output
        pbr_bake_group.links.new(node_combine_rgb.outputs[0], emit_node.inputs[0])
        pbr_bake_group.links.new(emit_node.outputs[0], group_outputs.inputs[16])

    create_orm()

    # itterate through all the sockets and link them together
    # with an emmision node
    def create_slots_and_make_links():
        offset = 1000
        for nodes in io:
            node = create_emit_node(nodes[3], offset, nodes[0])
            offset -= 200

            if nodes[0] == "Normal":
                
                pbr_bake_group.links.new(group_inputs.outputs[nodes[0]], node.inputs[2])
                pbr_bake_group.links.new(node.outputs[0], group_outputs.inputs[nodes[0]])
            
                continue
            
            pbr_bake_group.links.new(group_inputs.outputs[nodes[0]], node.inputs[0])
            pbr_bake_group.links.new(node.outputs[0], group_outputs.inputs[nodes[0]])

    create_slots_and_make_links()



class LinkSlotsFromBakeNodeAndBake(bpy.types.Operator):
    """Links outputs from the PBR Bake Node to the Material Output Node then bakes that texture
        Note: Make sure you have the texture you want to bake selected for pressing this button"""
    bl_idname = "node.link_bake_slots_and_bake"
    bl_label = "Links PBR Bake node to material output then bakes"
    bl_options = {'REGISTER', 'UNDO'}

    bake_slots : bpy.props.EnumProperty(
        items = bake_slots_output,
        name = "Bake Slot",
        description = "Which bake slot to choose"
    )

    # Changes the scenes bake mode
    def set_bake_mode(self, mode):
        bpy.data.scenes['Scene'].cycles.bake_type = mode


    @classmethod
    def poll(cls, context):
        return context
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "bake_slots")
    
    def execute(self, context):
        
        # This big conditional checks against the bake_slots 
        # property and delegates which bake mode should
        # be used and links the appropriate output socket
        # on the PBR_Bake Node
        
        if self.bake_slots == "base_color":
            link_slot(context, "Base Color")
            self.set_bake_mode("EMIT")
        elif self.bake_slots == "ao":
            link_slot(context, "AO")
            self.set_bake_mode("EMIT")
        elif self.bake_slots == "metalic":
            link_slot(context, "Metalic")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "specular":
            link_slot(context, "Specular")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "rough":
            link_slot(context, "Roughness")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "sheen":
            link_slot(context, "Sheen")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "tint":
            link_slot(context, "Sheen Tint")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "clearcoat":
            link_slot(context, "Clearcoat")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "clear_rough":
            link_slot(context, "Clearcoat Rough")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "emit":
            link_slot(context, "Emission")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "alpha":
            link_slot(context, "Alpha")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "orm":
            link_slot(context, "ORM")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "height":
            link_slot(context, "Heightmap")
            self.set_bake_mode("EMIT")

        elif self.bake_slots == "normal":
            link_slot(context, "Normal")
            bpy.data.scenes['Scene'].cycles.bake_type = "NORMAL"

        return {'FINISHED'}


class LinkSlotsFromBakeNode(bpy.types.Operator):
    """Links outputs from PBR Bake node to Material Output Node"""
    bl_idname = "node.link_bake_slots"
    bl_label = "Link Output slots from PBR Bake Node to Material Output"
    bl_options = {'REGISTER', 'UNDO'}

    bake_slots : bpy.props.EnumProperty(
        items = bake_slots_output,
        name = "Bake Slot",
        description = "Which bake slot to choose"
    )


    @classmethod
    def poll(cls, context):
        return context
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "bake_slots")
    
    def execute(self, context):
        
        # This big conditional checks against the bake_slots 
        # property and delegates which bake mode should
        # be used and links the appropriate output socket
        # on the PBR_Bake Node
        
        if self.bake_slots == "base_color":
            link_slot(context, "Base Color")
        elif self.bake_slots == "ao":
            link_slot(context, "AO")
        elif self.bake_slots == "metalic":
            link_slot(context, "Metalic")

        elif self.bake_slots == "specular":
            link_slot(context, "Specular")

        elif self.bake_slots == "rough":
            link_slot(context, "Roughness")

        elif self.bake_slots == "sheen":
            link_slot(context, "Sheen")

        elif self.bake_slots == "tint":
            link_slot(context, "Sheen Tint")

        elif self.bake_slots == "clearcoat":
            link_slot(context, "Clearcoat")

        elif self.bake_slots == "clear_rough":
            link_slot(context, "Clearcoat Roughness")

        elif self.bake_slots == "emit":
            link_slot(context, "Emission")

        elif self.bake_slots == "emit_str":
            link_slot(context, "Emission Strength")

        elif self.bake_slots == "alpha":
            link_slot(context, "Alpha")

        elif self.bake_slots == "orm":
            link_slot(context, "ORM")

        elif self.bake_slots == "transmission":
            link_slot(context, "Transmission")

        elif self.bake_slots == "transmission_rough":
            link_slot(context, "Transmission Roughness")

        elif self.bake_slots == "height":
            link_slot(context, "Heightmap")

        elif self.bake_slots == "normal":
            link_slot(context, "Normal")

        return {'FINISHED'}


class SetupBakingScene(bpy.types.Operator):
    """Changes render settings to make texture baking faster"""
    bl_idname = "scene.setup_baking_scene"
    bl_label = "Setup Baking Scene"
    bl_options = {'REGISTER', 'UNDO'}

    image_size: bpy.props.IntProperty(
        name = "Image Size",
        description = "The Size of your Textures. sets the tile size of the scene",
        default = 1024,
        min=16,
        max=8192
    )
    selected_to_active: bpy.props.BoolProperty(
        name = "Selected To Active",
        description = "",
        default = False
    )

    bake_margin: bpy.props.IntProperty(
        name = "Bake Margin",
        description = "",
        default = 16,
        min=0,
        max = 256,
    )

    clear_image: bpy.props.BoolProperty(
        name = "Clear Image",
        default = True
    )

    @classmethod
    def poll(cls, context):
        return context
    

    def execute(self, context):
        scene = context.scene
        _set_bake_settings(context, self.image_size)
        
        scene.render.bake.use_selected_to_active = self.selected_to_active
        scene.render.bake.cage_extrusion = 0.1
        scene.render.bake.margin = self.bake_margin
        scene.render.bake.use_clear = self.clear_image

        return {"FINISHED"}


class ResetBakeSettings(bpy.types.Operator):
    """Resets the Render settings to the settings before pressing the "Setup Baking Scene" button """

    bl_idname = "scene.reset_bake_settings"
    bl_label = "Reset Baking Scene"
    bl_options = {'REGISTER', 'UNDO'}

    render_tile_size: bpy.props.IntProperty(
        name = "Tile Size",
        description = "",
        default = 16,
        min=16,
        max=8192
    )

    render_samples: bpy.props.IntProperty(
        name = "Render Samples ",
        description = "",
        default = 32,
        min=16,
        max=8192
    )

    @classmethod
    def poll(cls, context):
        return context


    def execute(self, context):
        sam = render_settings_pre_bake_scene_setup['samples']
        tile_x = render_settings_pre_bake_scene_setup['tile_size']['x']
        tile_y = render_settings_pre_bake_scene_setup['tile_size']['y']
        scene = context.scene

        scene.cycles.samples = sam
        scene.render.tile_x = tile_x
        scene.render.tile_y = tile_y
        return {'FINISHED'}



class CreateBasicMaterialTextures(bpy.types.Operator):
    """ Creates PBR Textures (Seperate Occlusion, Roughness and Metalic). Adds them to the active Material"""
    bl_idname = "node.create_basic_pbr_textures"
    bl_label = "Create PBR Textures"
    bl_options = {"REGISTER", "UNDO"}

    image_size: bpy.props.IntProperty(
        name = "Image Size",
        description = "The Size of your Textures. Creates the textures with this size",
        default = 1024,
        min=16,
        max=8192
    )

    @classmethod
    def poll(cls, context):
        return context
    
    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="test")

    def execute(self, context):
        _create_textures("DEFAULT", self.image_size, context)
        return {'FINISHED'}


class CreateORMMaterialTextures(bpy.types.Operator):
    """ Creates PBR Textures with an ORM(Occlusion, Roughness, Metalic) in place of invividual for each. Adds them to the active Material"""
    bl_idname = "node.pbr_bake_create_orm_pbr_textures"
    bl_label = "Create PBR Textures"
    bl_options = {"REGISTER", "UNDO"}

    image_size: bpy.props.IntProperty(
        name = "Image Size",
        description = "The Size of your Textures. Creates the textures with this size",
        default = 1024,
        min=16,
        max=8192
    )


    @classmethod
    def poll(cls, context):
        return context
    

    def execute(self, context):
        _create_textures("ORM", self.image_size, context)
        return {'FINISHED'}


class AddPbrBakeNode(bpy.types.Operator):
    """Adds the bake node to the current node tree
        Note: This node is crucial for this add-on to work"""
    bl_idname = "node.pbr_bake_add_bake_node"
    bl_label = "Adds the bake node to the node tree"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context

    def execute(self, context):
        if bpy.data.node_groups.find("PBR_Bake") == -1:
            create_the_stuff()

        mat = context.active_object.active_material
        tree = mat.node_tree

        # Grabs the Material Output Nodes position in the node tree
        material_output_node_position = context.active_object.active_material.node_tree.nodes['Material Output'].location

        # adds the PBR Bake Group node to the node tree
        bake_node = bpy.ops.node.add_node(type="ShaderNodeGroup", use_transform=True, settings=[{"name":"node_tree", "value":"bpy.data.node_groups['PBR_Bake']"}])

        active_node = tree.nodes.active

        # Sets the node name to PBR_Bake
        active_node.name = "PBR_Bake"

        # Sets the position of the PBR Bake node relative to the Material Output position
        active_node.location = (material_output_node_position[0] + 800, material_output_node_position[1] + 64)
        return {'FINISHED'}


class PBRBakeTexture(bpy.types.Operator):
    """Links the corresponding output from the PBR Bake node to the material Output node then bakes.
        Note: Make sure you have the texture you want to bake selected before running this command"""
    bl_idname = "node.pbr_bake_bake_current_texture"
    bl_label = "link and bake"
    bl_options = {"REGISTER", "UNDO"}

    bake_slot : bpy.props.StringProperty(
        name = "bake slot",
    )

    @classmethod
    def poll(cls, context):
        return context

    def execute(self, context):
        # Baking Slot variable
        slt = ""

        # Checks to see if the bake slot is type of 'normal'
        # To change the output baking mode
        if  self.bake_slot == "normal":
            slt = "NORMAL"
        else:
            slt = "EMIT"
        
        bpy.ops.node.link_bake_slots(bake_slots=self.bake_slot)
        bpy.ops.object.bake(type=slt)
        
        return {'FINISHED'}


class ConnectToBakeNode(bpy.types.Operator):
    """Connect the selected node to the bake node"""
    bl_idname = "node.pbr_bake_connect_to_bake_node"
    bl_label  = "Link selected node to bake node"
    bl_options = {"REGISTER", "UNDO"}


    bake_slots : bpy.props.EnumProperty(
        name = "Connect To Slot",
        items = bake_slots_input,
        description = "Connect current not to slot"
    )

    @classmethod
    def poll(cls, context):
        valid = False
        if context.active_object.active_material.node_tree.nodes['PBR_Bake'] is not None:
            valid = True

        return valid
    
    def draw(self, context):
        layout = self.layout;
        layout.prop(self, "bake_slots")

    def execute(self, context):
        # This big conditional checks against the bake_slots 
        # property and delegates which bake mode should
        # be used and links the appropriate output socket
        # on the PBR_Bake Node
      
        
        if self.bake_slots == "base_color":
            link_to_bake_node(context, "Base Color")
        elif self.bake_slots == "ao":
            link_to_bake_node(context, "AO")
        elif self.bake_slots == "metalic":
            link_to_bake_node(context, "Metalic")

        elif self.bake_slots == "specular":
            link_to_bake_node(context, "Specular")

        elif self.bake_slots == "rough":
            link_to_bake_node(context, "Roughness")

        elif self.bake_slots == "sheen":
            link_to_bake_node(context, "Sheen")

        elif self.bake_slots == "tint":
            link_to_bake_node(context, "Sheen Tint")

        elif self.bake_slots == "clearcoat":
            link_to_bake_node(context, "Clearcoat")

        elif self.bake_slots == "clear_rough":
            link_to_bake_node(context, "Clearcoat Roughness")

        elif self.bake_slots == "emit":
            link_to_bake_node(context, "Emission")
        
        elif self.bake_slots == "emit_str":
            link_to_bake_node(context, "Emission Strength")

        elif self.bake_slots == "alpha":
            link_to_bake_node(context, "Alpha")
        
        elif self.bake_slots == "transmission":
            link_to_bake_node(context, "Transmission")
        
        elif self.bake_slots == "transmission_rough":
            link_to_bake_node(context, "Transmission Roughness")

        elif self.bake_slots == "orm":
            link_to_bake_node(context, "ORM")

        elif self.bake_slots == "height":
            link_to_bake_node(context, "Heightmap")

        elif self.bake_slots == "normal":
            link_to_bake_node(context, "Normal")
        return {'FINISHED'}




class PbrBakeConnectMenu(bpy.types.Menu):
    """popup menu for connecting selected node to the bake node
    Note: Requires a PBR Bake Node in the scene to work"""
    bl_idname = "NODE_MT_pbr_bake_connect_menu"
    bl_label = "Conect Selected Node to Bake Slot"

    def draw(self, context):
        type = context.space_data.tree_type
        layout = self.layout

        slots = bake_slots_input

        col_flow = layout.column_flow(columns=2)
        ii = 0

        for item in slots:
            col1 = col_flow.column()
            col2 = col_flow.column()

            if ii % 2 == 1:
                col1.operator(ConnectToBakeNode.bl_idname, text=item[1]).bake_slots = item[0]
            else:
                col2.operator(ConnectToBakeNode.bl_idname, text=item[1]).bake_slots = item[0]

            ii += 1

class PbrBakeBakeMenu(bpy.types.Menu):

    bl_idname = "NODE_MT_pbr_bake_bake_channel_menu"
    bl_label = "Bake Channel"

    def draw(self, context):
        type = context.space_data.tree_type
        layout = self.layout

        slots = bake_slots_output

        col_flow = layout.column_flow(columns=2)
        ii = 0
        for item in slots:
            col1 = col_flow.column()
            col2= col_flow.column()

            if ii % 2 == 1:
                col1.operator(PBRBakeTexture.bl_idname, text=item[1]).bake_slot = item[0]
            else:
                col1.operator(PBRBakeTexture.bl_idname, text=item[1]).bake_slot = item[0]

            ii += 1

class PbrBakeConnectToMaterialOutputMenu(bpy.types.Menu):
    bl_idname = "NODE_MT_pbr_bake_menu_connect_to_material_output"
    bl_label = "Connect Slot from PBR Bake Node to Material Output Node"

    def draw(self, context):
        layout = self.layout

        slots = bake_slots_output
        ii = 0
        c_flow = layout.column_flow(columns=2)
        for item in slots :
            col1 = c_flow.column()
            col2 = c_flow.column()

            if ii % 2 == 1:
                col1.operator(LinkSlotsFromBakeNode.bl_idname, text=item[1]).bake_slots = item[0]
            else:
                col2.operator(LinkSlotsFromBakeNode.bl_idname, text=item[1]).bake_slots = item[0]
                
            ii += 1

class PbrBakeMenu(bpy.types.Menu):
    bl_idname = "NODE_MT_pbr_bake_menu"
    bl_label = "PBR Bake Menu"

    def draw(self, context):
        layout = self.layout

        layout.operator(AddPbrBakeNode.bl_idname, text="Add PBR Bake Node", icon="ADD")
        layout.menu(PbrBakeConnectMenu.bl_idname, icon="TRIA_RIGHT")
        layout.menu(PbrBakeBakeMenu.bl_idname, icon="TRIA_RIGHT")
        layout.menu(PbrBakeConnectToMaterialOutputMenu.bl_idname, icon="TRIA_RIGHT")


class CallPbrBakeMenu(bpy.types.Operator):
    bl_idname = "wm.call_pie_menu"
    bl_label = "calls the pie menu for connection"

    @classmethod
    def poll(self, context):
        return context

    def execute(self, context):
        #   bpy.ops.wm.call_menu(name=PbrBakeConnectMenu.bl_idname)
          bpy.ops.wm.call_menu(name=PbrBakeMenu.bl_idname)

          return {'FINISHED'}
  

class NODE_PT_Bake_Panel_setup(bpy.types.Panel):
    """Panel for texture creation"""
    bl_label = "Setup"
    bl_category = "PBR Bake"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        box = layout

        tile_size = box.prop(
            bpy.data.scenes['Scene'],
            'pbr_bake_image_tile_size',
            text="Tile Size"
        )

        box.label(text="Bake Settings")

        row1 = box.row()

        row1.operator(
            operator="scene.setup_baking_scene", 
            text="Set"
        ).image_size = context.scene.pbr_bake_image_tile_size

        row1.operator(
            operator = "scene.reset_bake_settings",
            text = "Reset"
        )


        box.menu(PbrBakeConnectMenu.bl_idname)



class NODE_PT_PBR_Bake_Textures(bpy.types.Panel):
    """Panel for texture creation"""
    bl_label = "Texture and Node Creation"
    bl_category = "PBR Bake"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        box = layout


        box.prop(
            context.scene,
            'pbr_bake_image_size',
            text="Texture Size"
        
        )
        

        box.label(text="Generate Textures")
        row = box.row()
        row.operator(
            operator = CreateBasicMaterialTextures.bl_idname,
            text = "Full"
        ).image_size = context.scene.pbr_bake_image_size

        row.operator(
            operator = CreateORMMaterialTextures.bl_idname,
            text = "ORM"
        ).image_size = context.scene.pbr_bake_image_size

        box.operator(
            operator = AddPbrBakeNode.bl_idname,
            text = "Add Bake Node"
        )



class NODE_PT_PBR_Bake_Bake(bpy.types.Panel):
    """Panel containing the bake buttons"""
    bl_label = "Bake"
    bl_category = "PBR Bake"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        box2 = layout



        box2.label(text="Which to Bake")


        col_flow = box2.column_flow(columns=2)
        col1 = col_flow.column()
        col2 = col_flow.column()


        col1.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Base Color"
        ).bake_slot = "base_color"
        col2.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "AO"
        ).bake_slot = "ao"
        col1.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Metalic"
        ).bake_slot = "metalic"
        col2.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "ORM"
        ).bake_slot = "orm"
        col1.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Specular f0"
        ).bake_slot = "specular"
        col2.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Rough"
        ).bake_slot = "rough"
        col1.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Sheen"
        ).bake_slot = "sheen"
        col2.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Tint"
        ).bake_slot = "tint"
        col1.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Clearcoat"
        ).bake_slot = "clearcoat"
        col2.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Emission"
        ).bake_slot = "emit"
        col1.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Emission Strength"
        ).bake_slot = "emit_str"
        col2.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Alpha Mask"
        ).bake_slot = "alpha"
        col1.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Transmission"
        ).bake_slot = "transmission"
        col2.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Transmission Roughness"
        ).bake_slot = "transmission_rough"
        col1.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Heightmap"
        ).bake_slot = "height"
        col2.operator(
            operator = PBRBakeTexture.bl_idname,
            text = "Normal"
        ).bake_slot = "normal"


class NODE_PT_Bake_Panel_misc(bpy.types.Panel):
    bl_label="Misc"
    bl_category = "PBR Bake"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        layout.menu(PbrBakeConnectToMaterialOutputMenu.bl_idname)
        


class PbrBakeToolsAddonPrefs(bpy.types.AddonPreferences):
    """
        Addon Preferences
    """
    bl_idname = __name__

    default_texture_size: bpy.props.IntProperty(
        default = 1024,
        min = 64,
        max = 8192
    )

    default_tile_size: bpy.props.IntProperty(
        default = 256,
        min = 16,
        max = 2048
    )

    def draw(self, context):
        is_visible = False
        
    
        layout = self.layout
        col = layout.column()

        col.label(text="Hotkey: ctrl+shift+c in node editor")
        if is_visible == False:
            return
        col.prop(self, property="default_texture_size", text="Default Texture Size")
        col.prop(self, property="default_tile_size", text="Default Tile Size (Unstable)")
"""
Tuple for registering classes
"""
registration_classes = (
    SetupBakingScene,
    CreateBasicMaterialTextures,
    CreateORMMaterialTextures,
    ResetBakeSettings,
    LinkSlotsFromBakeNodeAndBake,
    LinkSlotsFromBakeNode,
    AddPbrBakeNode,
    PBRBakeTexture,
    ConnectToBakeNode,
    PbrBakeConnectMenu,
    CallPbrBakeMenu,
    PbrBakeBakeMenu,
    PbrBakeConnectToMaterialOutputMenu,
    PbrBakeMenu,
    PbrBakeToolsAddonPrefs,
    NODE_PT_Bake_Panel_setup,
    NODE_PT_PBR_Bake_Textures,
    NODE_PT_PBR_Bake_Bake,
    NODE_PT_Bake_Panel_misc ,
)

def init_props():
    prefs = {
        "default_texture_size" : 64,
        "default_tile_size" : 64,
        "bake_margin" : 8,
        "clear_image" : True
    }
    # if  bpy.context.preferences.addons.get('generate_pbr_textures') is not None:
    #     prefs = bpy.context.preferences.addons['generate_pbr_textures'].preferences
    # else:
    #     prefs['default_texture_size'] = 1024
    #     prefs['default_tile_size'] = 256
    
    prefs['default_texture_size'] = 1024
    prefs['default_tile_size'] = 256
    # Scene props for Addon

    # Scene prop for tile size
    bpy.types.Scene.pbr_bake_image_tile_size = bpy.props.IntProperty(
        name="pbr_bake_image_tile_size",
        min=1,
        max=8192,
        default = prefs["default_tile_size"],
        description = "Tile size of the Render, Match this with texture size for faster baking (doing this is more unstable)"
    )

    # Scene prop for image size
    bpy.types.Scene.pbr_bake_image_size = bpy.props.IntProperty(
        name="pbr_bake_image_size",
        min=32,
        max=8192,
        default = prefs['default_texture_size'],
        description = "Texture Size"
    )

    # scene prop for baking margin

    bpy.types.Scene.pbr_bake_bake_margin = bpy.props.IntProperty(
        name="pbr_bake_bake_margin",
        min = 0,
        max=256,
        default = prefs['bake_margin'],
        description = "Bake Margin",

    )
    bpy.types.Scene.pbr_bake_clear_image = bpy.props.IntProperty(
        name="pbr_bake_bake_clear_image",
        default = prefs['clear_image'],
        description = "Clear Image",

    )

addon_keymaps = []


# Registration function
def register():
    for cls in registration_classes:
        register_class(cls)
    
    init_props()


    # handle the keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new(CallPbrBakeMenu.bl_idname, 'C', 'PRESS', ctrl=True, shift=True, alt=False)
    addon_keymaps.append(km)

def unregister():
    for cls in registration_classes:
        unregister_class(cls)
    

    wm = bpy.context.window_manager

    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)

        del addon_keymaps[:]

if __name__ == "__main__":
    register()



    