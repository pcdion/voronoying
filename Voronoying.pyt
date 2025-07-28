# -*- coding: utf-8 -*-
import arcpy
from src.voronoying import voronoying
from src.topology import validate_topology

class Toolbox(object):
    def __init__(self):
        self.label =  "Voronoying"
        self.alias  = "voronoying"
        self.tools = [Voronoying, Topology]

class Voronoying(object):
    def __init__(self):
        self.label       = "Boost Voronoi"
        self.description = "Generate voronoi diagrams from line and point geometries."

    def getParameterInfo(self):

        in_points = arcpy.Parameter(
            displayName="Input points",
            name="in_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        in_points.filter.list = ["POINT"]

        in_lines = arcpy.Parameter(
            displayName="Input lines",
            name="in_lines",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        in_lines.filter.list = ["POLYLINE"]

        out_dataset = arcpy.Parameter(
            displayName="Output dataset",
            name="out_dataset",
            datatype = ['DEWorkspace', 'DEFeatureDataset'],
            parameterType="Required",
            direction="Input")

        out_points = arcpy.Parameter(
            displayName="Output points",
            name="out_points",
            datatype="GPString", #NOTE: vonoroying.py does not expect full path, just the name"
            parameterType="Required",
            direction="Output")

        out_points.value = "VONOROYING_POINTS"

        out_polygons = arcpy.Parameter(
            displayName="Output polygons",
            name="out_polygons",
            datatype="GPString",
            parameterType="Required",
            direction="Output")

        out_polygons.value = "VONOROYING_POLYGONS"

        line_identifiers = arcpy.Parameter(
            displayName="Line identifiers",
            name="line_identifiers",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        line_identifiers.filter.type = "ValueList"

        factor = arcpy.Parameter(
            displayName="Factor",
            name="factor",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        factor.filter.type = "ValueList"
        factor.filter.list = [1, 10, 100, 1000, 10000]

        parameters = [in_points, in_lines, out_dataset, out_points, out_polygons, line_identifiers, factor]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if(parameters[1].value):
            parameters[5].filter.list = [f.name for f in arcpy.Describe(parameters[1].value).fields]
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        inPoints    = parameters[0].valueAsText
        inLines     = parameters[1].valueAsText
        outData     = parameters[2].valueAsText
        outPoints   = parameters[3].valueAsText
        outPoly     = parameters[4].valueAsText
        lineIds     = parameters[5].valueAsText
        factor      = parameters[6].valueAsText

        voronoying(inPoints, inLines, outData, outPoints, outPoly, lineIds, int(factor))

    def postExecute(self, parameters):
        return

class Topology(object):
    def __init__(self):
        self.label       = "Validate Topology"
        self.description = "Validate topology of input features intended for Voronoying tool."

    def getParameterInfo(self):

        in_points = arcpy.Parameter(
            displayName="Input points",
            name="in_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        in_points.filter.list = ["POINT"]

        in_lines = arcpy.Parameter(
            displayName="Input lines",
            name="in_lines",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        in_lines.filter.list = ["POLYLINE"]

        factor = arcpy.Parameter(
            displayName="Factor",
            name="factor",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        factor.filter.type = "ValueList"
        factor.filter.list = [1, 10, 100, 1000, 10000]

        out_gdb = arcpy.Parameter(
            displayName="Output geodatabase",
            name="out_gdb",
            datatype = 'DEWorkspace',
            parameterType="Required",
            direction="Output")

        parameters = [in_points, in_lines, factor, out_gdb]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        inPoints    = parameters[0].valueAsText
        inLines     = parameters[1].valueAsText
        factor     = parameters[2].valueAsText
        gdb     = parameters[3].valueAsText

        validate_topology(inPoints, inLines, int(factor), gdb)

    def postExecute(self, parameters):
        return
