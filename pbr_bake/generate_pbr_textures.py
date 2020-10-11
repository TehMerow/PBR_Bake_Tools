bl_info = {
    "name"    : "PBR Bake Tools",
    "blender" : (2,90,1),
    "version" : (1,0),
    "category": "Material",
    "author" : "Merow",
    "doc_url" : "https://github.com/TehMerow/PBR_Bake_Tools/wiki/Tutorial",
    "location" : "Node Editor > Properties Panel",
    "description" : "Aids in PBR Texture baking"
}

import bpy

from bpy.utils import (
    register_class,
    unregister_class
)
from bpy.app.handlers import persistent
from bpy.types import AddonPreferences

bl_info = {
    "name"    : "Prepare PBR Bake",
    "blender" : (2,90,1),
    "category": "Material",
    "author" : "Merow"
}

image_names_full = [
    "base_color",
    "ambient_occlusion",
    "specular",
    "metalness",
    "roughness",
    "normal",
    "height",
]

image_names_orm = [
    "base_color",
    "specular",
    "ORM",
    "normal",
    "height"
]


def create_image_texture(name, size, context):
    """
        Creates an image texture
        names the image texture
        stores it into memory
    """
    active_mat = context.active_object.active_material.name  
    mat_name = active_mat + "-" + name
    
    bpy.ops.image.new(
        name= mat_name, 
        width=size,
        height=size,
        color=[0,0,0,0],
        alpha=True,
        generated_type="BLANK",
    )


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
        image_order = [1, 0, 6, 5, 4, 2]
    elif pbr_type == 'ORM':
        image_order = [1, 4, 0, 3, 2]
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

    start_pos = [-512,2048]
    for texture in ordered_images:
        mat_name = context.active_object.active_material.name
        if texture.name.find(mat_name) == -1:
            continue

        create_texture_node(texture, texture.name, start_pos, context)
        start_pos[1] += -256

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
        ("Alpha", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", 1.0),
        ("Transmission", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", .0),
        ("Transmission Roughness", "NodeSocketFloat", "NodeSocketShader", "ShaderNodeEmission", .0),
        ("Normal", "NodeSocketVector", "NodeSocketShader", "ShaderNodeBsdfDiffuse",(0.0,0.0,0.0)),

    ]



    # Create Group Inputs
    group_inputs = pbr_bake_group.nodes.new("NodeGroupInput")
    group_inputs.location = (-350, 0)

    for socket in io:
        pbr_bake_group.inputs.new(socket[1], socket[0]).default_value = socket[4]


    # create emission nodes
    def create_emit_node(type, pos):
        node_emit = pbr_bake_group.nodes.new(type)
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
        emit_node = create_emit_node("ShaderNodeEmission", -1500)

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
        pbr_bake_group.links.new(emit_node.outputs[0], group_outputs.inputs[14])

    create_orm()

    # itterate through all the sockets and link them together
    # with an emmision node
    def create_slots_and_make_links():
        offset = 0
        for nodes in io:
            node = create_emit_node(nodes[3], offset)
            offset -= 100

            if nodes[0] == "Normal":
                
                pbr_bake_group.links.new(group_inputs.outputs[nodes[0]], node.inputs[2])
                pbr_bake_group.links.new(node.outputs[0], group_outputs.inputs[nodes[0]])
            
                continue
            
            pbr_bake_group.links.new(group_inputs.outputs[nodes[0]], node.inputs[0])
            pbr_bake_group.links.new(node.outputs[0], group_outputs.inputs[nodes[0]])

    create_slots_and_make_links()



class LinkSlotsFromBakeNode(bpy.types.Operator):
    """Links the slots from the custom node group"""
    bl_idname = "node.link_bake_slots"
    bl_label = "Link Slots from Bake Node"
    bl_options = {'REGISTER', 'UNDO'}

    bake_slots : bpy.props.EnumProperty(
        items = [
            ("base_color", "Base Color", "The Base color or Albedo"),
            ("ao", "Ambient Occlusion", "The Ambient Occlusion"),
            ("metalic", "Metalness", "The Metalness Slot"),
            ("specular", "Specular", "Specular F0 Slot"),
            ("rough", "Roughness", "Roughness slot"),
            ("sheen", "Sheen", "Sheen slot"),
            ("tint", "Sheen Tint", "Sheen Tint Slot"),
            ("clearcoat", "Clearcoat", "Clearcoat Slot"),
            ("clear_rough", "Clearcoat Roughness", "Clearcoat Roughness slot"),
            ("emit", "Emission", "Emission Slot"),
            ("alpha", "Alpha", "Alpha Slot"),
            ("orm", "ORM", "ORM slot. Red Channel = Occlusion, Green Channel = Roughness, Blue channel = Metalness"),
            ("height", "Heightmap", "Heightmap, blender can't do this very well"),
            ("normal", "NORMAL", "BSDF output for normal map"),
        ],
        name = "Bake Slot",
        description = "Which bake slot to choose"
    )

    def set_bake_mode(self, mode):
        bpy.data.scenes['Scene'].cycles.bake_type = mode


    @classmethod
    def poll(cls, context):
        return context
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "bake_slots")
    
    def execute(self, context):
        # link_slot(context, bake_slots)
        
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

        # else:
        #     return "invalid"
        
        return {'FINISHED'}

class SetupBakingScene(bpy.types.Operator):
    """Sets up the scene for baking PBR Materials"""
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

    @classmethod
    def poll(cls, context):
        return context
    

    def execute(self, context):
        scene = context.scene
        _set_bake_settings(context, self.image_size)
        
        scene.render.bake.use_selected_to_active = self.selected_to_active
        scene.render.bake.cage_extrusion = 0.1
        scene.render.bake.margin = 8

        return {"FINISHED"}


class ResetBakeSettings(bpy.types.Operator):
    """Aids in resetting the render settings quickly"""

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
        sam = self.render_samples
        tile = self.render_tile_size
        scene = context.scene

        scene.cycles.samples = sam
        scene.render.tile_x = tile
        scene.render.tile_y = tile
        return {'FINISHED'}



class CreateBasicMaterialTextures(bpy.types.Operator):
    """ Creates PBR Textures and adds them to the active Material"""
    bl_idname = "scene.create_basic_pbr_textures"
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
    """ Creates PBR Textures and adds them to the active Material"""
    bl_idname = "scene.create_orm_pbr_textures"
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
    """adds the bake node to the current node tree"""
    bl_idname = "node.add_bake_node"
    bl_label = "Adds the bake node to the node tree"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context

    def execute(self, context):
        if bpy.data.node_groups.find("PBR_Bake") == -1:
            create_the_stuff()

        mat = context.active_object.material_slots[0].material
        tree = mat.node_tree

        bpy.ops.node.add_node(type="ShaderNodeGroup", use_transform=True, settings=[{"name":"node_tree", "value":"bpy.data.node_groups['PBR_Bake']"}])

        active_node = tree.nodes.active
        active_node.name = "PBR_Bake"
        active_node.location = (300, 0)
        return {'FINISHED'}


class PBRBakeTexture(bpy.types.Operator):
    "links and bakes the texture"
    bl_idname = "node.bake_current_texture"
    bl_label = "link and bake"
    bl_options = {"REGISTER", "UNDO"}

    bake_slot : bpy.props.StringProperty(
        name = "bake slot",
    )

    @classmethod
    def poll(cls, context):
        return context

    def execute(self, context):
        slt = ""

        if  self.bake_slot == "normal":
            slt = "NORMAL"
        else:
            slt = "EMIT"
        bpy.ops.node.link_bake_slots(bake_slots=self.bake_slot)
        bpy.ops.object.bake(type=slt)
        
        return {'FINISHED'}



class NODE_PT_Bake_Panel_setup(bpy.types.Panel):
    bl_label = "PBR Bake Setup"
    bl_category = "PBR Bake"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Scene Setup")  

        tile_size = box.prop(
            bpy.data.scenes['Scene'],
            'pbr_bake_image_tile_size',
            text="Tile Size"
        )
        box.operator(
            operator="scene.setup_baking_scene", 
            text="Setup Baking Scene"
        ).image_size = context.scene.pbr_bake_image_tile_size

        box.operator(
            operator = "scene.reset_bake_settings",
            text = "reset baking scene"
        )


class NODE_PT_PBR_Bake_Textures(bpy.types.Panel):
    bl_label = "PBR Bake Textures"
    bl_category = "PBR Bake"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        box = layout.box()

        box.label(text="Texture Creators")
        box.prop(
            context.scene,
            'pbr_bake_image_size',
            text="Texture Size"
        )
        box.operator(
            operator = "scene.create_basic_pbr_textures",
            text = "Create PBR Textures Full"
        ).image_size = context.scene.pbr_bake_image_size

        box.operator(
            operator = "scene.create_orm_pbr_textures",
            text = "Create PBR Textures ORM"
        ).image_size = context.scene.pbr_bake_image_size

        box.operator(
            operator = "node.add_bake_node",
            text = "Add Bake Node"
        )


class NODE_PT_PBR_Bake_Bake(bpy.types.Panel):
    bl_label = "PBR Bake "
    bl_category = "PBR Bake"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        box2 = layout.box()

        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Base Color"
        ).bake_slot = "base_color"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake AO"
        ).bake_slot = "ao"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Metalic"
        ).bake_slot = "metalic"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake ORM"
        ).bake_slot = "orm"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Specular f0"
        ).bake_slot = "specular"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Rough"
        ).bake_slot = "rough"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Sheen"
        ).bake_slot = "sheen"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Tint"
        ).bake_slot = "tint"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Clearcoat"
        ).bake_slot = "clearcoat"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Emission"
        ).bake_slot = "emit"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Alpha Mask"
        ).bake_slot = "alpha"
        box2.operator(
            operator = "node.bake_current_texture",
            text = "Bake Normal"
        ).bake_slot = "normal"


"""
Tuple for registering classes
"""
registration_classes = (
    SetupBakingScene,
    CreateBasicMaterialTextures,
    CreateORMMaterialTextures,
    ResetBakeSettings,
    LinkSlotsFromBakeNode,
    AddPbrBakeNode,
    PBRBakeTexture,
    NODE_PT_Bake_Panel_setup,
    NODE_PT_PBR_Bake_Textures,
    NODE_PT_PBR_Bake_Bake,
)

def init_props():
    
    # Scene props for Addon

    # Scene prop for tile size
    bpy.types.Scene.pbr_bake_image_tile_size = bpy.props.IntProperty(
        name="pbr_bake_image_tile_size",
        min=1,
        max=1024,
        default = 256,
        description = "The render tile size,"
    )

# Registration function
def register():
    for cls in registration_classes:
        register_class(cls)

def unregister():
    for cls in registration_classes:
        unregister_class(cls)
    

if __name__ == "__main__":
    register()