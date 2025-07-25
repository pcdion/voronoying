"""
Author: Fabien Ancelin
Script created with:
    Python 2.7
    ArcGIS 10.3
The script required the library Pyvoronoi to be installed.
    https://github.com/Voxel8/pyvoronoi
"""


import os,sys, traceback, math
import arcpy
import pyvoronoi

#"C:\Users\fancelin\OneDrive - Esri Canada\Documents\ArcGIS\Projects\pyvoronoi-tests\pyvoronoi-tests.gdb\fishnet_points" "C:\Users\fancelin\OneDrive - Esri Canada\Documents\ArcGIS\Projects\pyvoronoi-tests\pyvoronoi-tests.gdb\fishnet_lines" "C:\Users\fancelin\OneDrive - Esri Canada\Documents\ArcGIS\Projects\pyvoronoi-tests\pyvoronoi-tests.gdb" VORONOYING_POINTS VORONOYING_LINES VORONOYING_POLYGONS OBJECTID

def Distance(point1, point2):
    """
	pute the euclidean distance between two points
        :param point1:  an array of two double precision numbers representing the first point
        :param point2: an array of two double precision numbers representing the starting point of the line on the other side of the curve
        :return: the distance, as a float8 number.			
    """
    return math.sqrt(math.pow(point2[0] - point1[0], 2) + math.pow(point2[1] - point1[1], 2))
	
def delFCByPath(FC):
    """attempts to delete a specified feature class"""
    try:
        arcpy.Delete_management(FC)
    except:
        pass

def mergeExtent(extents):
    """
    Read through a set of extent an return the extent containing them all.
    :param extents: a list of arcpy.Extent objects
    :return: an arcpy.Extent containing all other extents.
    """
    if len(extents) == 0:
        raise Exception("No extent was provided")

    if len(extents) == 1:
        return extents[0]

    outExtent = arcpy.Extent(extents[0].XMin, extents[0].YMin, extents[0].XMax, extents[0].YMax)
    for i in range(1, len(extents)):

        if extents[i].XMin < outExtent.XMin:
            outExtent.XMin =  extents[i].XMin

        if extents[i].YMin < outExtent.YMin:
            outExtent.YMin = extents[i].YMin

        if extents[i].XMax > outExtent.XMax:
            outExtent.XMax = extents[i].XMax

        if extents[i].YMax > outExtent.YMax:
            outExtent.YMax = extents[i].YMax

    return outExtent


def validateInputPointFeatureClass(inPointFeatureClass):
    """
    Validate that the input feature class comply with the requirements and returns its extent.
    :param inPointFeatureClass: the input point feature class
    :return: an arcpy.Extent object representing the extent of the feature class
    """

    #Check the characteristic of the feature class. Simple lines are expected.
    desc = arcpy.Describe(inPointFeatureClass)

    if desc.featureType != "Simple":
        raise Exception('The feature class should contains simple features.')

    if desc.shapeType != "Point":
        raise Exception('The feature class should contain points')

    #Validate that the input geometry does have self intersecting features
    return desc.extent


def validateInputLineFeatureClass(inLineFeatureClass):
    """
    Validate that the input feature class comply with the requirements and returns its extent.
    :param inLineFeatureClass:
    :return: an arcpy.Extent object representing the extent of the feature class
    """

    #Check the characteristic of the feature class. Simple lines are expected.
    desc = arcpy.Describe(inLineFeatureClass)

    if desc.featureType != "Simple":
        raise Exception('The feature class should contains simple features.')

    if desc.shapeType != "Polyline":
        raise Exception('The feature class should contain line')

    #Validate that the input geometry does have self intersecting features
    return desc.extent



def validateLicense():
    """
    Check that the current license is using advanced.
    :return:
    """
    if not arcpy.ProductInfo() == 'ArcInfo':
        if arcpy.CheckProduct('ArcInfo') == 'available':
            arcpy.SetProduct('ArcInfo')
        else:
            raise Exception('An advanced license was not available')


def checkSelfOverlap(inputFC, outPath, outFCName, triggerFailure):
    """
    Check if a feature class contains overlapping features. Based on the value of the triggerFailure parameter,
    it will return either a warning or an exception.
    :param inputFC: The input feature class
    :param outPath: The output path for the feature class that will contain overlaps.
    :param outFCName: The name of the feature class containing the overlaps.
    :param triggerFailure: If true, then the function will return an exception when duplicates are found.
    :return:
    """
    tempFC = "in_memory/{0}".format(outFCName)
    outFCPath = "{0}{1}{2}".format(outPath,os.path.sep, outFCName)
    #Spatial Join into temporary feature class
    arcpy.SpatialJoin_analysis (inputFC, inputFC, tempFC, 'JOIN_ONE_TO_ONE', 'KEEP_COMMON', match_option='SHARE_A_LINE_SEGMENT_WITH')

    #Generate an output feature class
    arcpy.FeatureClassToFeatureClass_conversion (tempFC, outPath, outFCName, 'Join_Count > 1')

    #Delete the in memory feature class
    arcpy.Delete_management(tempFC)
    #Count if there are any issues
    count = int(arcpy.GetCount_management(outFCPath).getOutput(0))
    if count > 0:
        arcpy.AddMessage("Overlapping segments found. See feature class {0}".format(outFCPath))
        if triggerFailure:
            arcpy.AddError("Overlapping segments found. See feature class {0}".format(outFCPath))
            sys.exit(-1)

def voronoying(inpoints: str, inlines: str, outWorkspace: str, outpoints: str = "VONOROYING_POINTS", outpolygons: str = "VONOROYING_LINES", inroads_identifier: str = "OBJECTID", factor: int = 1):
    try:
        ##################################################################################
        #READ PARAMETERS
        ##################################################################################
        arcpy.env.workspace = outWorkspace

        ##################################################################################
        #HARD CODED PARAMETERS
        ##################################################################################
        # if arcpy.env.scratchWorkspace is None:

        arcpy.env.scratchWorkspace = outWorkspace

        inroads_split_name = "voronoying_lines_split"
        inroads_split_line_name = "voronoying_lines_split_lines"
        inroads_split = "{0}{1}{2}".format(arcpy.env.scratchWorkspace, os.path.sep, inroads_split_name)
        inroads_split_line = "{0}{1}{2}".format(arcpy.env.scratchWorkspace, os.path.sep, inroads_split_line_name)
        spatial_reference = arcpy.Describe(inlines).spatialReference
        minimum_length = 1/factor


        ##################################################################################
        #VALIDATION
        ##################################################################################
        arcpy.AddMessage("Validation")
        #Validate license requirements
        validateLicense()

        #Validate that a line identifier was provided
        if len(inroads_identifier) == 0:
            raise Exception("Input lines identifer was not provided.")

        extents = []
        #Validate input line feature class.
        inlinesBBox = validateInputLineFeatureClass(inlines)
        extents.append(inlinesBBox)
        #Validate input point feature class if required.
        inPointsBBox = validateInputPointFeatureClass(inpoints) if inpoints is not None else None

        ##################################################################################
        #REMOVE FEATURE CLASSES
        ##################################################################################
        for fc in [
            inroads_split,
            inroads_split_line,
            "{0}{1}{2}".format(outWorkspace, os.path.sep, outpoints),
            "{0}{1}{2}".format(outWorkspace,os.path.sep,outpolygons)]:
            delFCByPath(fc)


        ##################################################################################
        #COMPUTING THE BOUNDING BOX
        ##################################################################################
        # Instanciate pyvoronoi
        pv = pyvoronoi.Pyvoronoi(factor)
        arcpy.AddMessage("Add points to voronoi")
        pointOIDs = []
        if inPointsBBox != None:
            extents.append(inPointsBBox)
            for point in arcpy.da.SearchCursor(inpoints, ['SHAPE@X', 'SHAPE@Y', 'OID@']):
                pointOIDs.append(point[2])
                pv.AddPoint([point[0], point[1]])

        arcpy.AddMessage("Computing bounding box outlines")
        finalBBox = mergeExtent(extents)
        finalBBoxExpended = arcpy.Extent(finalBBox.XMin -1, finalBBox.YMin - 1, finalBBox.XMax + 1, finalBBox.YMax + 1)
        bbox_line = [
            arcpy.Array([arcpy.Point(finalBBox.XMin, finalBBox.YMin),
             arcpy.Point(finalBBox.XMax, finalBBox.YMin)]),
                    arcpy.Array([arcpy.Point(finalBBox.XMin, finalBBox.YMin),
             arcpy.Point(finalBBox.XMin, finalBBox.YMax)]),
        arcpy.Array([arcpy.Point(finalBBox.XMax, finalBBox.YMax),
             arcpy.Point(finalBBox.XMin, finalBBox.YMax)]),
        arcpy.Array([arcpy.Point(finalBBox.XMax, finalBBox.YMax),
             arcpy.Point(finalBBox.XMax, finalBBox.YMin)]),

            arcpy.Array([arcpy.Point(finalBBoxExpended.XMin, finalBBoxExpended.YMin),
             arcpy.Point(finalBBoxExpended.XMax, finalBBoxExpended.YMin)]),
                    arcpy.Array([arcpy.Point(finalBBoxExpended.XMin, finalBBoxExpended.YMin),
             arcpy.Point(finalBBoxExpended.XMin, finalBBoxExpended.YMax)]),
        arcpy.Array([arcpy.Point(finalBBoxExpended.XMax, finalBBoxExpended.YMax),
             arcpy.Point(finalBBoxExpended.XMin, finalBBoxExpended.YMax)]),
        arcpy.Array([arcpy.Point(finalBBoxExpended.XMax, finalBBoxExpended.YMax),
             arcpy.Point(finalBBoxExpended.XMax, finalBBoxExpended.YMin)])
        ]
        arcpy.AddMessage(
            "Bounding Box Info: {0},{1} | {2},{3}".format(finalBBox.XMin, finalBBox.YMin, finalBBox.XMax,
                                                          finalBBox.YMax))


        ##################################################################################
        #FORMAT INPUT. NEED TO MAKE SURE LINE ARE SPLIT AT VERTICES AND THAT THERE ARE NO OVERLAPS
        ##################################################################################
        arcpy.AddMessage("Format lines")
        arcpy.AddMessage("Split lines at vertices")
        arcpy.SplitLine_management(in_features=inlines, out_feature_class=inroads_split)

        arcpy.AddMessage("Add bounding box")
        with arcpy.da.InsertCursor(inroads_split, ['SHAPE@', inroads_identifier]) as op:
            for pointArray in bbox_line:
                arcpy.AddMessage(
                    "{0},{1} - {2},{3}".format(
                        pointArray[0].X,
                        pointArray[0].Y,
                        pointArray[1].X,
                        pointArray[1].Y)
                )
                op.insertRow([arcpy.Polyline(pointArray), None])
        del op

        arcpy.AddMessage("Split lines at intersections")
        arcpy.FeatureToLine_management(inroads_split, inroads_split_line, '#', 'ATTRIBUTES')


        ##################################################################################
        #SEND LINE INPUT TO VORONOI AND CONSTRUCT THE GRAPH
        ##################################################################################
        arcpy.AddMessage("Add lines to voronoi")
        lineIds = []		
        for road in arcpy.da.SearchCursor(inroads_split_line, ['SHAPE@', 'OID@', 'SHAPE@LENGTH', inroads_identifier]):
            
            
            
            if road[2]< minimum_length:
                arcpy.AddWarning(f"Warning: Segment {road[1]} is smaller than minimum length")
            else :
                lineIds.append(road[3])
                pv.AddSegment(
                    [
                    [
                        road[0].firstPoint.X,
                        road[0].firstPoint.Y
                    ],
                    [
                        road[0].lastPoint.X,
                        road[0].lastPoint.Y
                    ]
                    ])

        arcpy.AddMessage('Data validation')
        degenerate_segments = pv.GetDegenerateSegments()
        intersecting_segments = pv.GetIntersectingSegments()
        points_on_segments = pv.GetPointsOnSegments()
        arcpy.AddMessage(f'Detected {len(degenerate_segments)} degenerate segments')
        arcpy.AddMessage(f'Detected {len(intersecting_segments)} intersecting segments')
        arcpy.AddMessage(f'Detected {len(points_on_segments)} points on segments')

        for s_index in intersecting_segments:
            s = pv.GetSegment(s_index)
            arcpy.AddMessage(f'Intersecting segment at {s_index} - {s}  -Line Id = {lineIds[s_index]}')

        # if len(degenerate_segments) > 0 or len(intersecting_segments) > 0 or len(points_on_segments):
        #     raise Exception('Detected invalid input geometries... Aborting.')

        arcpy.AddMessage("Construct voronoi")
        pv.Construct()
        # cells = pv.GetCells()
        # edges = pv.GetEdges()
        # vertices = pv.GetVertices()

        ##################################################################################
        #CREATE THE OUTPUT FEATURE CLASSES
        ##################################################################################
        arcpy.AddMessage("Construct output point feature class")

        if len(outpoints) > 0:
            arcpy.CreateFeatureclass_management(outWorkspace, outpoints, 'POINT', spatial_reference=spatial_reference)		
            arcpy.AddField_management(outpoints, 'IDENTIFIER', "LONG")		
            fields = ['IDENTIFIER', 'SHAPE@X', 'SHAPE@Y']
            with arcpy.da.InsertCursor(outpoints, fields) as cursor:
                for vIndex, v in pv.EnumerateVertices():
                    cursor.insertRow([vIndex, v.X, v.Y])

        arcpy.AddMessage("Construct output cells feature class")
        if len(outpolygons) > 0:
            arcpy.CreateFeatureclass_management(outWorkspace, outpolygons,'POLYGON', spatial_reference=spatial_reference)
            arcpy.AddField_management(outpolygons, 'CELL_ID', "LONG")
            arcpy.AddField_management(outpolygons, 'CONTAINS_POINT', "SHORT")
            arcpy.AddField_management(outpolygons, 'CONTAINS_SEGMENT', "SHORT")
            arcpy.AddField_management(outpolygons, 'SITE', "LONG")
            arcpy.AddField_management(outpolygons, 'SOURCE_CATEGORY', "SHORT")
            arcpy.AddField_management(outpolygons, 'INPUT_TYPE', "TEXT")
            arcpy.AddField_management(outpolygons, 'INPUT_ID', "LONG")
            fields = ['CELL_ID', 'CONTAINS_POINT', 'CONTAINS_SEGMENT', 'SHAPE@', 'SITE', 'SOURCE_CATEGORY', 'INPUT_TYPE', 'INPUT_ID']
            with arcpy.da.InsertCursor(outpolygons, fields) as cursor:
                for cIndex, cell in pv.EnumerateCells():
                    if not cell.is_open and not cell.is_degenerate:
                        if (cIndex % 5000 == 0 and cIndex > 0):
                            arcpy.AddMessage("Cell Index: {0}".format(cIndex))

                        array = arcpy.Array()
                        for i, value in enumerate(cell.edges):
                            e = pv.GetEdge(value)
                            startVertex = pv.GetVertex(e.start)
                            endVertex = pv.GetVertex(e.end)
                            max_distance  = Distance([startVertex.X, startVertex.Y], [endVertex.X, endVertex.Y]) / 10

                            if e.is_linear:
                                array.add(arcpy.Point(startVertex.X, startVertex.Y))
                                array.add(arcpy.Point(endVertex.X, endVertex.Y))

                            else:
                                try:
                                    points = pv.DiscretizeCurvedEdge(cell.edges[i], max_distance, 1 / factor)
                                    for p in points:
                                        array.append(arcpy.Point(p[0], p[1]))
                                except pyvoronoi.FocusOnDirectixException:
                                    arcpy.AddMessage(
                                        "FocusOnDirectixException at: {5}. The drawing has been defaulted from a curved line to a straight line. Length {0} - From: {1}, {2} To: {3}, {4}".format(
                                            max_distance, startVertex.X,
                                            startVertex.Y, endVertex.X,
                                            endVertex.Y, cell.edges[i]))
                                    array.add(arcpy.Point(startVertex.X, startVertex.Y))
                                    array.add(arcpy.Point(endVertex.X, endVertex.Y))

                        if cell.site >= len(pointOIDs):
                            input_type = "LINE"
                            input_id = lineIds[cell.site - len(pointOIDs)]
                        else:
                            input_type = "POINT"
                            input_id = pointOIDs[cell.site]
                        polygon = arcpy.Polygon(array)
                        cursor.insertRow((cell.cell_identifier, cell.contains_point, cell.contains_segment, polygon, cell.site,
                                          cell.source_category, input_type, input_id))

    except Exception as ex:
        tb = sys.exc_info()[2]
        tbInfo = traceback.format_tb(tb)[-1]
        arcpy.AddError('PYTHON ERRORS:\n%s\n%s:' %
                       (tbInfo, ex))
        # print('PYTHON ERRORS:\n%s\n%s: %s\n' %
        #                 (tbInfo, _sys.exc_type, _sys.exc_value))
        arcpy.AddMessage('PYTHON ERRORS:\n%s\n%s:' %
                       (tbInfo, ex))
        gp_errors = arcpy.GetMessages(2)
        if gp_errors:
            arcpy.AddError('GP ERRORS:\n%s\n' % gp_errors)
        raise (ex)


if __name__ == '__main__':
    if len(sys.argv) == 8: #REVIEW: allow some default values?
        voronoying(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7])
    else:
        print('PYTHON ERRORS:\n Please provide required arguments')