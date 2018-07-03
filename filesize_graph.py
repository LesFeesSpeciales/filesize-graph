# Copyright (C) 2017 Les Fees Speciales
# voeu@les-fees-speciales.coop
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


bl_info = {
    "name": "Filesize Graph",
    "author": "Les Fees Speciales",
    "version": (0, 0, 1),
    "blender": (2, 77, 0),
    "location": "View3D",
    "description": "Helps visualize file sizes in a folder, in graph form",
    "category": "Files"
}

import bpy
import os
import re
from math import inf

rexp = re.compile(r'([0-9]+)')


def sizeof_fmt(num, suffix='B'):
    '''From https://stackoverflow.com/a/1094933/4561348'''
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def create_curve_object(name):
    if name not in bpy.data.objects:
        curve = bpy.data.curves.new(name, 'CURVE')
        obj = bpy.data.objects.new(name, curve)
        bpy.context.scene.objects.link(obj)
    else:
        obj = bpy.data.objects[name]
    return obj


def get_name_and_frame(filename):
    # try:
    frame_number = rexp.findall(filename)[-1]
    padding = len(frame_number)
    pattern = filename.replace(frame_number, '{:0}' + str(padding))
    frame_number = int(frame_number)
    return pattern, frame_number
    # except:
    print('Could not parse file ' + filename)


def visualize_size(name, filepath):
    frames = {}
    min_frame = inf
    min_size = inf
    max_frame = 0
    max_size = 0

    basedir, filename = os.path.split(filepath)
    base_pattern, frame_number = get_name_and_frame(filename)

    for file in os.listdir(basedir):
        pattern, frame_number = get_name_and_frame(file)
        if pattern != base_pattern:
            print(file)
            continue

        if int(frame_number) > max_frame:
            max_frame = frame_number
        if int(frame_number) < min_frame:
            min_frame = frame_number

        size = os.path.getsize(os.path.join(basedir, file))

        frames[frame_number] = size
        if size > max_size:
            max_size = size
        if size < min_size:
            min_size = size

    for i in range(0, max_frame + 1):
        if not i in frames:
            frames[i] = -1.0

    obj = create_curve_object(name)

    obj.data.splines.clear()
    spline = obj.data.splines.new('POLY')
    obj.data.dimensions = '3D'
    spline.points.add(len(frames)-1)
    for i, (frame, size) in enumerate(frames.items()):
        spline.points[frame].co.x = frame
        spline.points[i].co.z = size
        if size != -1.0 and max_size != 0.0:
            spline.points[i].co.z /= max_size
        spline.points[i].co.z *= 100
    return (min_frame, min_size, max_frame, max_size)


class FilesizeGraph(bpy.types.Operator):
    bl_idname = "lfs.filesize_graph"
    bl_label = "Filesize Graph"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        for g in context.scene.filesize_graphs:
            try:
                min_frame, min_size, max_frame, max_size = visualize_size(g.name, g.filepath)
                g.min_frame = min_frame
                g.min_size = min_size
                g.max_frame = max_frame
                g.max_size = max_size
            except FileNotFoundError:
                self.report({"WARNING"}, 'Path not found: ' + g.name)
                create_curve_object(g.name)
        return {"FINISHED"}


class FilesizeGraphAdd(bpy.types.Operator):
    bl_idname = "lfs.filesize_graph_add"
    bl_label = "Filesize Graph Add"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        context.scene.filesize_graphs.add()
        if "Graph" not in context.scene.filesize_graphs:
            name = "Graph"
        else:
            i = 1
            while "Graph.{:03}".format(i) in context.scene.filesize_graphs:
                i += 1
            name = "Graph.{:03}".format(i)
        context.scene.filesize_graphs[-1].name = name
        context.scene.filesize_graphs[-1].old_name = name
        create_curve_object(name)
        return {"FINISHED"}


class FilesizeGraphRemove(bpy.types.Operator):
    bl_idname = "lfs.filesize_graph_remove"
    bl_label = "Filesize Graph Remove"
    bl_description = ""
    bl_options = {"REGISTER"}

    index = bpy.props.IntProperty(default=0)

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        name = context.scene.filesize_graphs[self.index].name
        if name in context.scene.objects:
            obj = bpy.data.objects[name]
            context.scene.objects.unlink(obj)
            bpy.data.objects.remove(obj)
        context.scene.filesize_graphs.remove(self.index)
        return {"FINISHED"}


class FilesizeGraphPanel(bpy.types.Panel):
    bl_idname = "lfs.filesize_graph_panel"
    bl_label = "Filesize Graph"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Files"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        col = row.column(align=True)
        for i, g in enumerate(context.scene.filesize_graphs):
            sub = col.row(align=True)
            split = sub.split(percentage=0.2, align=True)
            split.prop(g, "name", text="")
            split.prop(g, "filepath", text="")
            sub.operator("lfs.filesize_graph_remove", icon='X', text="").index = i
            if g.name in context.scene.objects:
                sub.prop(context.scene.objects[g.name], 'hide', text="")
        col = row.column()

        sub = col.column(align=True)
        sub.operator("lfs.filesize_graph_add", icon='ZOOMIN', text="")

        layout.operator('lfs.filesize_graph')

        if (
                context.object is not None
                and context.object.name in context.scene.filesize_graphs):
            frames = len([p for p in context.object.data.splines[0].points if p.co.z != -100.0])
            graph = context.scene.filesize_graphs[context.object.name]
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Frames: {}".format(frames))
            col.label(text="Frame range: {:04}-{:04}".format(graph.min_frame, graph.max_frame))
            col.label(text="Sizes: {} - {}".format(sizeof_fmt(graph.min_size), sizeof_fmt(graph.max_size)))


def graph_update(self, context):
    if self.old_name in context.scene.objects:
        print('found')
        context.scene.objects[self.old_name].name = self.name
        self.old_name = self.name
    else:
        create_curve_object(self.name)


class FilesizeGraphs(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(default='', update=graph_update)
    old_name = bpy.props.StringProperty(default='')
    filepath = bpy.props.StringProperty(default='', subtype='FILE_PATH')
    min_frame = bpy.props.IntProperty(default=0)
    max_frame = bpy.props.IntProperty(default=0)
    min_size = bpy.props.FloatProperty(default=0.0)
    max_size = bpy.props.FloatProperty(default=0.0)


def register():
    bpy.utils.register_class(FilesizeGraphs)
    bpy.types.Scene.filesize_graphs = bpy.props.CollectionProperty(
        name="Filesize Graphs", type=FilesizeGraphs)
    bpy.utils.register_module(__name__)


def unregister():
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
