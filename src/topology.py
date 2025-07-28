"""
Author: Patrick Dion
Script created with:
    Python 3.11
    ArcGIS 10.3
"""

import os,sys,traceback,time
import arcpy

def validate_input_type(in_feature, shape_type):
    """Validate that the input feature class is appropriate featureType and shapeType"""

    desc = arcpy.Describe(in_feature)

    if desc.featureType != "Simple":
        raise Exception('The feature class should contains simple features.')

    if desc.shapeType != shape_type:
        raise Exception(f'The feature class should contain {shape_type} shape type')

def validate_spatial_ref(inpoints, inlines, factor):
    """Validate that the input point and line feature classes share spatial reference"""
    srp = arcpy.Describe(inpoints).spatialReference
    srl = arcpy.Describe(inlines).spatialReference
    #wkt strings
    srp_str = srp.exportToString()
    srl_str = srl.exportToString()
    resolution = 1 / (factor * 10)
    tolerance = 1 / factor
    if srp.projectionCode == 0 or srl.projectionCode == 0:
        raise Exception(f'The feature class should contain Projected spatial reference')
    if srp_str != srl_str:
        raise Exception('mismatched spatial reference')
    if srp.XYResolution > resolution or srl.XYResolution > resolution:
        arcpy.AddWarning("feature resolution has fewer significant digits than 1 / (factor * 10)")
    if srp.XYTolerance > tolerance or srl.XYTolerance > tolerance:
        arcpy.AddWarning("feature tolerance has fewer significant digits than 1 / factor")

def report_errors(topo_path, prefix):
    """
    Report topology validation errors
    :param: topo_path: the path to the topology file
    :param: workspace: the path to the workspace
    :prefix: the base name appended for export of error features
    """

    arcpy.AddMessage(arcpy.GetMessages(0)) # NOTE: nothing at index 2 upon error
    # NOTE: returned result object from ValidateTopology process yielding only success messages even with bad input. Neither can SearchCursor open topology by reference from result, possibly a file lock
    # currently relying on ExportTopologyErrors as workaround, potentially heavy for large datasets?
    arcpy.management.ExportTopologyErrors(topo_path, arcpy.env.workspace, prefix)

    error_count = 0
    for vType in ["_line", "_point", "_poly"]:
        fc = (f"{prefix}{vType}")
        count = int(arcpy.management.GetCount(fc).getOutput(0))
        if count > 0:
            rule_types = set(row[0] for row in arcpy.da.SearchCursor(fc, "RuleType"))
            for rt in rule_types:
                sel = arcpy.management.SelectLayerByAttribute(fc,"NEW_SELECTION", f"RuleType = '{rt}'")
                type_count = int(arcpy.management.GetCount(sel).getOutput(0))
                arcpy.AddMessage(f"{rt} errors: {type_count}")
                arcpy.management.SelectLayerByAttribute(fc, "CLEAR_SELECTION")

        error_count += count
        arcpy.Delete_management(fc)

    arcpy.AddMessage(f"total topology errors: {error_count}")

def create_point_intersect(inpoints, inlines, out_points):
    """
    Points disjoint from lines are valid, but those overlapping lines must be covered by line endpoints. To satisfy this criteria,
    we run a clip/intersect and use the output intersecting points as the input for the dataset. If intersect returns null, we continue without copying the points.
    :param: inpoints: the input point feature class
    :param: inlines: the input line feature class
    :param: out_points: the intersecting points to generate
    """
    result = arcpy.analysis.Clip(inpoints, inlines, out_points)
    while result.status < 4:  # is this necessary for large sets?
        time.sleep(0.2)
    clip_out = result.getOutput(0)
    feature_count = int(arcpy.GetCount_management(clip_out).getOutput(0))
    return feature_count > 0

def create_topology(out_lines, out_points, factor, p_intersect_result):
    """
    topology creation and rule configuration
    :param: out_lines: the output line feature class
    :param: out_points: the output line feature class
    :param: factor: use to set cluster tolerance
    :param: p_intersect_result: boolean check based on whether intersecting points exist
    :return: path to topology file
    """
    arcpy.management.CreateTopology(os.path.join(arcpy.env.workspace, "dataset"), "topology", 1 / factor)  # REVIEW: is cluster tolerance inherited from ds?
    topo_path = os.path.join(arcpy.env.workspace, "dataset", "topology")
    arcpy.management.AddFeatureClassToTopology(topo_path, out_lines, "")
    arcpy.management.AddRuleToTopology(topo_path, "Must Not Overlap (Line)", out_lines, "", "", "")
    arcpy.management.AddRuleToTopology(topo_path, "Must Not Intersect Or Touch Interior (Line)", out_lines, "", "","")
    arcpy.management.AddRuleToTopology(topo_path, "Must Not Self-Overlap (Line)", out_lines, "", "", "")
    if p_intersect_result:
        arcpy.management.AddFeatureClassToTopology(topo_path, out_points, "")
        arcpy.management.AddRuleToTopology(topo_path, "Must Be Covered By Endpoint Of (Point-Line)", out_points, "", out_lines, "")
    return topo_path

def validate_topology(inpoints: str, inlines: str, factor: int, out_gdb: str):
    """
    Validate that input features do not overlap or self-intersect, and share coordinate system
    :param inpoints: input points feature class
    :param inlines: input lines feature class
    :param factor: scaling multiplier for coordinates
    :param out_gdb: full path for output geodatabase to create
    """
    try:
        if inpoints is None or inlines is None or out_gdb is None or factor == 0:
            raise Exception(f'invalid null input feature class')

        arcpy.AddMessage("validating spatial reference and feature type")
        # verify input feature class types before topology
        validate_input_type(inpoints, "Point")
        validate_input_type(inlines, "Polyline")
        validate_spatial_ref(inpoints, inlines, factor)

        arcpy.AddMessage("generating dataset and topology")

        arcpy.env.overwriteOutput = "True"
        parentdir = os.path.dirname(out_gdb) #TOFIX: check for .gdb extension
        arcpy.management.CreateFileGDB(parentdir, os.path.basename(out_gdb))
        arcpy.env.workspace = out_gdb
        
        spatial_reference = arcpy.Describe(inlines).spatialReference

        # apply the required resolution and cluster tolerance to dataset
        sr = arcpy.SpatialReference(spatial_reference.factoryCode)
        sr.XYResolution = 1 / (factor * 10)
        sr.XYTolerance = 1 / factor

        arcpy.management.CreateFeatureDataset(arcpy.env.workspace, "dataset", sr)

        out_lines = os.path.join(arcpy.env.workspace, "dataset", "lines")
        out_points = os.path.join(arcpy.env.workspace, "dataset", "points")

        # polylines must be split into segments as they are in pyvoronoi
        arcpy.management.SplitLine(inlines, out_lines)
        # generate intersecting points
        p_intersect_result = create_point_intersect(inpoints, out_lines, out_points)

        topo_path = create_topology(out_lines, out_points, factor, p_intersect_result)

        arcpy.AddMessage("validating topology")
        arcpy.management.ValidateTopology(topo_path)

        report_errors(topo_path, "topoerrors")
        
    except Exception as ex:
        tb = sys.exc_info()[2]
        tbInfo = traceback.format_tb(tb)[-1]
        arcpy.AddError('PYTHON ERRORS:\n%s\n%s:' %
                       (tbInfo, ex))
        arcpy.AddMessage('PYTHON ERRORS:\n%s\n%s:' %
                       (tbInfo, ex))
        gp_errors = arcpy.GetMessages(2)
        if gp_errors:
            arcpy.AddError('GP ERRORS:\n%s\n' % gp_errors)
        raise (ex)
    
if __name__ == '__main__':
    if len(sys.argv) == 3:
        validate_topology(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
    else:
        print('PYTHON ERRORS:\n Please provide required arguments')
    #validate_topology("D:\\MAPDATA\\voronoyTest.gdb\\fishnet_points_intersects_good", "D:\\MAPDATA\\voronoyTest.gdb\\fishnet_lines", 10, "D:\\MAPDATA\\scratchTopo.gdb")
