# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# C R E D I T S
##################################################################
# (C) 2016 Gernot Ziegler, - released under Blender Artistic License - www.blender.org
# (C) 2016 Marco Alesiani, - released under Blender Artistic License - www.blender.org
# Date: February 9th, 2016
# Ver: 1.1
#-----------------------------------------------------------------

# U S A G E    D E T A I L S
##################################################################
# Usage: File > Export > GeoCast file
#
# NOTICE: A valid camera must be selected in the scene
#
#-----------------------------------------------------------------

bl_info = {
    "name": "GeoCast Exporter",
    "author": "Gernot Ziegler, Marco Alesiani",
    "version": (1, 0, 2),
    "blender": (2, 76, 0),
    "location": "File > Export > GeoCast Thingy",
    "description": "Exports depth data and camera .geocast files",
    "warning": "",
    "wiki_url": "http://www.geofront.eu/",
    "category": "Import-Export",
}


import bpy
from bpy.types import Operator
from bpy.props import (StringProperty, IntProperty, BoolProperty, EnumProperty)
from bpy_extras.io_utils import (ExportHelper)

# The main exporter class which creates the 'GeoCast Exporter' panel in the export window
# and starts the file saving process
class ExportGeoCast(bpy.types.Operator, ExportHelper):
    """Export the current scene to a GeoCast file """
    bl_idname = "export_geocast.folder"
    bl_label = "GeoCast Exporter"

    directory = StringProperty(subtype='DIR_PATH', name = "", default = "", description = "Path where to save GeoCast data")    
    check_extension = False
    filename_ext = '.' # Needed, bug?
    use_filter_folder = True # Export into a directory
    # filter_glob = StringProperty(default="*.geocast", options={'HIDDEN'}) # File filters

    # (identifier, name, description) tuples for the combo box
    export_sizes = ( 
            ("256", "256 x 256", ""), 
            ("512", "512 x 512", ""), 
            ("1024", "1024 x 1024", "") 
            )
    export_size = EnumProperty( 
            name="Export Size", 
            description="Export size for all the output images", 
            items=export_sizes, 
            default='256'
            )

    frame_start = IntProperty(name="Start Frame",
            description="Start frame for exporting",
            default=1, min=1, max=300000)
    frame_end = IntProperty(name="End Frame",
            description="End frame for exporting (not included in the export data)",
            default=40, min=1, max=300000)

    export_colormap = BoolProperty(
            description="Export a color map together with the geocast file",
            name="Export color map",
            default = False)
    export_depthmap = BoolProperty(
            description="Export a depth map together with the geocast file",
            name="Export depth map",
            default = False)

    @classmethod
    def poll(cls, context):
        return context.active_object != None

    def invoke(self, context, event):
        self.filepath = "" # Clears the filename since we're not using it
        # Scene frame range is overridden with [1;40] by design
        # self.frame_start = context.scene.frame_start
        # self.frame_end = context.scene.frame_end
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        import os

        directory = self.properties.directory
        if os.path.isdir(directory) == False:
            msg = "Please select a directory, not a file (" + directory + ")"
            self.report({'WARNING'}, msg)
            return {'FINISHED'}
        # filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

        return exportToGeoCastFile(self, context, directory, self.export_size, (self.frame_start, self.frame_end))

    def draw(self, context): # UI setup
        layout = self.layout

        layout.label("Camera Exporter options")
        layout.separator()
        layout.prop(self, "frame_start")
        layout.prop(self, "frame_end")
        layout.prop(self, "export_size", expand=True)        
        layout.separator()
        layout.prop(self, "export_colormap")
        layout.prop(self, "export_depthmap")

# A simple progressbar in the console inspired by unix terminals
def updateProgressBar(task_title, percentage): # e.g. ("saving", 34 / 100)
    import sys
    bar_length = 20
    block_length = int(round(bar_length * percentage))
    # Caveat: using a carriage return at the beginning ensures we overwrite the same line as before.
    # Just using a newline generates new output.
    msg = "[{0}] [{1}] {2}%\n".format(task_title, "#" * block_length + "-" * (bar_length - block_length), round(percentage * 100, 2))
    if percentage >= 1: msg += " DONE\r\n"
    sys.stdout.write(msg)
    sys.stdout.flush()    

# Exporting routine
def exportToGeoCastFile(self, context, output_path, export_size, export_frame_range):
    import os

    print ("@@@@@@@@@@ START EXPORTING ROUTINE @@@@@@@@@@@@@@\n")

    print ('\n')
    print ('|| GeoCast exporter script V1.02 ||\n')
    print ('|| February 2016, Marco Alesiani ||\n')
    version = bl_info["version"]

    # Debug info to be displayed in the terminal    
    print ('Width and height is: ', export_size)

    # Set output path
    print ('Output path is: ', output_path)

    # Cycle through all selected objects (i.e. through all selected cameras)
    for camera_object in context.selected_objects:        
    
        # Check if this camera_object is actually a camera
        if camera_object.type != 'CAMERA':
            raise Exception("[ERROR] - Object with name '" + camera_object.name + "' is not a camera")
        print ("Found camera with name " + camera_object.name);

        # Create subdirectory "CameraName/" where to store OpenEXR and GeoCast files
        output_camera_path = output_path + camera_object.name
        if not os.path.exists(output_camera_path):
            os.makedirs(output_camera_path)

        context.scene.render.filepath = output_camera_path + os.sep;

        # Set up nodes to export the colormap and/or depthmap if asked to do so
        nodes_to_cleanup = []
        old_use_nodes = context.scene.use_nodes
        context.scene.use_nodes = True
        nodes = context.scene.node_tree.nodes
        render_layers = nodes['Render Layers']        
        if self.export_colormap == True:

            set_alpha = nodes.new("CompositorNodeSetAlpha")
            nodes_to_cleanup.append(set_alpha)

            color_file_output = nodes.new("CompositorNodeOutputFile")
            nodes_to_cleanup.append(color_file_output)
            color_file_output.base_path = context.scene.render.filepath + "colormap"
            color_file_output.format.file_format = 'PNG'
            color_file_output.format.color_mode = 'RGBA'
            color_file_output.format.color_depth = '8' # Needed by geofront webgl viewers
            color_file_output.file_slots[0].path = '' # No prefix to filenames

            # Connections
            context.scene.node_tree.links.new(
                render_layers.outputs['Image'],
                set_alpha.inputs['Image']
            )
            context.scene.node_tree.links.new(
                render_layers.outputs['Alpha'],
                set_alpha.inputs['Alpha']
            )
            context.scene.node_tree.links.new(
                set_alpha.outputs['Image'],
                color_file_output.inputs['Image']
            )

        if self.export_depthmap == True:

            map_range = nodes.new("CompositorNodeMapRange")
            nodes_to_cleanup.append(map_range)
            map_range.inputs[1].default_value = 0
            map_range.inputs[2].default_value = camera_object.data.clip_end
            map_range.inputs[3].default_value = 0
            map_range.inputs[4].default_value = 1

            color_ramp = nodes.new("CompositorNodeValToRGB")
            nodes_to_cleanup.append(color_ramp)
            color_ramp.color_ramp.color_mode = 'RGB'
            color_ramp.color_ramp.interpolation = 'LINEAR'

            depth_file_output = nodes.new("CompositorNodeOutputFile")
            nodes_to_cleanup.append(depth_file_output)
            depth_file_output.base_path = context.scene.render.filepath + "depthmap"
            depth_file_output.format.file_format = 'PNG'
            depth_file_output.format.color_mode = 'BW'
            depth_file_output.format.color_depth = '8' # Needed by geofront webgl viewers
            depth_file_output.file_slots[0].path = '' # No prefix to filenames

            # Connections
            context.scene.node_tree.links.new(
                render_layers.outputs['Z'],
                map_range.inputs['Value']
            )
            context.scene.node_tree.links.new(
                map_range.outputs['Value'],
                color_ramp.inputs['Fac']
            )
            context.scene.node_tree.links.new(
                color_ramp.outputs['Image'],
                depth_file_output.inputs['Image']
            )

        for frameNr in range(export_frame_range[0], export_frame_range[1]):

            updateProgressBar("Exporting GeoCast data", frameNr / export_frame_range[1])

            # Save OpenEXR with depth data (color channels are only used for debugging purposes)
            context.scene.camera = camera_object
            context.scene.frame_start = frameNr
            context.scene.frame_end = frameNr
            context.scene.frame_step = 1
            context.scene.frame_current = frameNr
            context.scene.render.pixel_aspect_x = 1
            context.scene.render.pixel_aspect_y = 1
            context.scene.render.use_file_extension = True
            context.scene.render.image_settings.color_mode ='RGB' # Alpha might not be present, pick RGB
            context.scene.render.image_settings.file_format = 'OPEN_EXR'
            context.scene.render.image_settings.exr_codec = 'ZIP'
            # context.scene.render.image_settings.color_depth = '16' # Half float
            context.scene.render.image_settings.use_zbuffer = True
            context.scene.render.resolution_x = int(export_size)
            context.scene.render.resolution_y = int(export_size)
            context.scene.render.use_raytrace = False # Speeds things up considerably

            # Handles markers in a timeline animation (i.e. if there's a marker, set our current camera
            # as the rendering one - restore afterwards)
            markersForThisFrame = [x for x in context.scene.timeline_markers if x.frame == frameNr]
            previousCameras = []
            if len(markersForThisFrame) > 0:
                for marker in markersForThisFrame:
                    previousCameras.append(marker.camera)
                    marker.camera = camera_object
            else:
                context.scene.timeline_markers.new('GEOCASTMARKER', frameNr)
                context.scene.timeline_markers['GEOCASTMARKER'].camera = camera_object

            # Update the scene before rendering or gathering camera data            
            context.scene.update()

            bpy.ops.render.render(animation=True) # Render            

            # Write the geocast file corresponding to this frame
            cm = camera_object.matrix_world
            #print ("Camera Location is", cm)
            loc = camera_object.location.to_tuple()
            #print ("Camera Position is", loc)
            geocastFilename = context.scene.render.filepath + str(frameNr).zfill(4) + ".geocast"
            FILE = open(geocastFilename, "w")
            FILE.write('GeoCast V1.0\n')
            FILE.write('# Made with GeoCast Exporter Blender Addon V%d.%d.%d\n' % (version[0], version[1], version[2]))
            if camera_object.animation_data is None:
              FILE.write("StaticCamera\n")
            else:
              FILE.write("DynamicCamera\n")
            locstr = 'Pos %.02f %.02f %.02f\n' % loc
            #print (locstr)
            FILE.write(locstr)
            viewslicestr = 'ViewSlice FODAngle %.02f Size %.02f\n' % (145, 1000)
            #print (viewslicestr)
            FILE.write(viewslicestr)
            # World matrix is column-major stored
            cam_modelmat_str = 'ModelviewMatrix\n%f %f %f %f\n%f %f %f %f\n%f %f %f %f\n%f %f %f %f\n' %  \
                (cm[0][0], cm[1][0], cm[2][0], cm[3][0], \
                 cm[0][1], cm[1][1], cm[2][1], cm[3][1], \
                 cm[0][2], cm[1][2], cm[2][2], cm[3][2], \
                 cm[0][3], cm[1][3], cm[2][3], cm[3][3])
            FILE.write(cam_modelmat_str)
            #print (cam_modelmat_str)
            clipstart = camera_object.data.clip_start
            clipend = camera_object.data.clip_end
            print("Camera type is " + camera_object.data.type + "\n")
            if camera_object.data.type == 'ORTHO': # Orthogonal
                scale = camera_object.data.ortho_scale
                dataprojstr = 'DataProject Ortho WindowSize %.02f %.02f ProjRange %.02f %.02f\n' % (scale, scale, clipstart, clipend)
                #print (dataprojstr)
                FILE.write(dataprojstr)
            else: # Perspective
                # lens = camera_object.data.lens            
                # Obsolete: dataprojstr = 'DataProject BlenderPerspective Aspect %.02f Lens %.04f ClipRange %.02f %.02f\n' % (1.0, lens, clipstart, clipend)
                fovy = camera_object.data.angle_y            
                fovx = camera_object.data.angle_x            
                fov = camera_object.data.angle            
                pi = 3.14159265358979323846
                fovy_deg = fovy/pi*180
                fovx_deg = fovx/pi*180
                dataprojstr = 'DataProject Perspective Fovy %f Aspect %f ClipRange %.05f %.05f\n' % (fovy_deg, fovx/fovy, clipstart, clipend)
                #print (dataprojstr)
                FILE.write(dataprojstr)
                FILE.write("WorldSpaceDepth\n")
                fovstr = 'FoV %.03f  FoVx %.03f  Fovx_deg %f Fovy %.03f Fovy_deg %f\n' % (fov, fovx, fovx_deg, fovy, fovy_deg)
                print(fovstr)
            rangestr = 'ZDataRange 0.0 1.0\n'
            #print (rangestr)
            FILE.write(rangestr)
            FILE.close()
            print ("Saved: ", geocastFilename)

            # Restore markers, if any
            if len(markersForThisFrame) > 0:
                for idx, val in enumerate(previousCameras):
                    markersForThisFrame[idx].camera = val
            else:
                context.scene.timeline_markers.remove(context.scene.timeline_markers['GEOCASTMARKER'])

        for node in nodes_to_cleanup: # Cleanup nodes from the original graph
            nodes.remove(node)

        context.scene.use_nodes = old_use_nodes

    print ("@@@@@@@@@@ END EXPORTING ROUTINE @@@@@@@@@@@@@@\n")    
    print("This was geocast exporter plugin V%d.%d.%d" % (version[0], version[1], version[2]))
    
    return {'FINISHED'}


def menu_export(self, context):
    self.layout.operator(ExportGeoCast.bl_idname, text="GeoCast data (.geocast)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_export)    


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_export)


if __name__ == "__main__":
    register()
