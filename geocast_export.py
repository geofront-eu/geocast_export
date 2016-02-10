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
# Ver: 1.0
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
    "version": (1, 0, 0),
    "blender": (2, 76, 0),
    "location": "File > Export > GeoCast Thingy",
    "description": "Exports depth data and camera .geocast files",
    "warning": "",
    "wiki_url": "http://www.geofront.eu/",
    "category": "Import-Export",
}


import bpy
from bpy.types import Operator
from bpy.props import (StringProperty, IntProperty, EnumProperty)
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
            description="End frame for exporting",
            default=40, min=1, max=300000)

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

    print ("@@@@@@@@@@ START EXPORTING ROUTINE @@@@@@@@@@@@@@\n")

    print ('\n')
    print ('|| GeoCast exporter script V1.00 ||\n')
    print ('|| February 2016, Marco Alesiani ||\n')

    # Debug info to be displayed in the terminal    
    print ('Width and height is: ', export_size)

    # Set output path
    print ('Output path is: ', output_path)
    
    # Get camera name from the selected object
    if context.active_object.type != 'CAMERA':
        raise Exception("[ERROR] - Active object is not a camera")
    print ("Found camera with name " + context.active_object.name);

    context.scene.render.filepath = output_path + context.active_object.name + '_';

    for frameNr in range(export_frame_range[0], export_frame_range[1]):

        updateProgressBar("Exporting GeoCast data", frameNr / export_frame_range[1])

        # Save OpenEXR with depth data
        context.scene.camera = context.active_object
        context.scene.frame_start = frameNr
        context.scene.frame_end = frameNr
        context.scene.frame_step = 1    
        context.scene.render.pixel_aspect_x = 1
        context.scene.render.pixel_aspect_y = 1
        context.scene.render.use_file_extension = True
        context.scene.render.image_settings.color_mode ='RGB'
        context.scene.render.image_settings.file_format = 'OPEN_EXR'
        context.scene.render.image_settings.exr_codec = 'ZIP'
        # context.scene.render.image_settings.color_depth = '16' # Half float
        context.scene.render.image_settings.use_zbuffer = True
        context.scene.render.resolution_x = int(export_size)
        context.scene.render.resolution_y = int(export_size)
        bpy.ops.render.render(animation=True) # Render

        # Update the scene before gathering camera data
        context.scene.frame_current = frameNr
        context.scene.update()

        # Write the geocast file corresponding to this frame
        cm = context.scene.camera.matrix_world
        #print ("Camera Location is", cm)
        loc = context.scene.camera.location.to_tuple()
        #print ("Camera Position is", loc)
        geocastFilename = context.scene.render.filepath + str(frameNr).zfill(4) + ".geocast"
        FILE = open(geocastFilename, "w")
        #print ("Saving camera data to", geocastFilename)
        FILE.write('GeoCast V1.0\n')
        if context.scene.camera.animation_data is None:
          FILE.write("StaticCamera\n")
        else:
          FILE.write("DynamicCamera\n")
        locstr = 'Pos %.02f %.02f %.02f\n' % loc
        #print (locstr)
        FILE.write(locstr)
        viewslicestr = 'ViewSlice FODAngle %.02f Size %.02f\n' % (145, 1000)
        #print (viewslicestr)
        FILE.write(viewslicestr)
        cam_modelmat_str = 'ModelviewMatrix\n%f %f %f %f\n%f %f %f %f\n%f %f %f %f\n%f %f %f %f\n' %  \
            (cm[0][0], cm[0][1], cm[0][2], cm[0][3], \
             cm[1][0], cm[1][1], cm[1][2], cm[1][3], \
             cm[2][0], cm[2][1], cm[2][2], cm[2][3], \
             cm[3][0], cm[3][1], cm[3][2], cm[3][3])
        FILE.write(cam_modelmat_str)
        #print (cam_modelmat_str)
        clipstart = context.scene.camera.data.clip_start
        clipend = context.scene.camera.data.clip_end
        if context.scene.camera.data.type == 'ORTHO': # Orthogonal
            scale = context.scene.camera.data.ortho_scale
            dataprojstr = 'DataProject Ortho WindowSize %.02f %.02f ProjRange %.02f %.02f\n' % (scale, scale, clipstart, clipend)
            #print (dataprojstr)
            FILE.write(dataprojstr)
        else: # Perspective
            lens = context.scene.camera.data.lens            
            dataprojstr = 'DataProject BlenderPerspective Aspect %.02f Lens %.04f ClipRange %.02f %.02f\n' % (1.0, lens, clipstart, clipend)
            #print (dataprojstr)
            FILE.write(dataprojstr)
        rangestr = 'ZDataRange 0.0 1.0\n'
        #print (rangestr)
        FILE.write(rangestr)
        FILE.close()

    print ("@@@@@@@@@@ END EXPORTING ROUTINE @@@@@@@@@@@@@@\n")

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