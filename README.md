# Voronoying

## Description

This tool contains a Voronoi tool for ArcGIS Pro. It generates Voronoi cells from point and line inputs. Unlike ArcGIS Pro out-of-the box [Thiessen Polygons Tool](https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/create-thiessen-polygons.htm) it can generate cells from more than just point.

This tool relies on two project:
 - The [pyvoronoi](https://pypi.org/project/pyvoronoi) module provides a python wrapper for the Boost API in Python.
 - The [Boost Voronoi API](https://www.boost.org/doc/libs/1_75_0/libs/polygon/doc/voronoi_main.htm). This C++ API provides the core logic and is very, very fast. 

The geoprocessing contains information about its parameters in its built-in documentation.

Here is a screeenshot of what the output look like. Black segments and points are the voronoi input geometries while the cells and cell's vertices are represented in blue.:

![Voronoi Problem](/resources/VoronoiResults.png "Voronoi Problem")

## Setup

 - In your start menu, open your python environment from ArcGIS --> Python Command Prompt
 - Run the command `python.exe -m pip install pyvoronoi`

This will install the pyvoronoi library needed for the geoprocessing tool to run.

## Data consideration

### Resolution

The major constrain with the Boost Voronoi API is that the input segments must be converted into integers. In order to do that, the geoprocessing tool use a default factor of 100 to any input coordinates and then truncates the result. 

The input data should not have segments that are smaller than 1:100 = 0.01. Any segment smaller than that can create topology issue in the input data.

Because the coordinates get multiplied by a factor, and then truncated, do not use latitude / longitude coordinate with your input data. You are bound to run into issue.

### Topology

Input lines must follow the different constraints:

 - Segments cannot be smaller than 1 divided by the default factor (see above).
 - Segments must intersect each other at nodes. They should not cross or overlap. Use [ArcGIS Pro's topology](https://pro.arcgis.com/en/pro-app/latest/help/editing/geodatabase-topology.htm) features to check your input data.
 - Segments endpoint must be properly snapped together. Make sure the input data is correctly snapped.

 ### What happens if the data is incorrect?

 The call to `Construct` method of pyvoronoi will never complete or return an error. That means as a user that the tool will never complete, and will never get to the point where your output points and polygon feature class get generated. If you observe that behaviour, that's your cue: go fix your data.

## Limitations

The output feature class (vertices, edges, cells) may not be exactly snapped to the input line feature class. The reason for that is that the underlying Boost API takes integer as an input. 

When input coordinates are sent to the voronoi API, they multiplied by a factor and then truncated. The output coordinates for output points and polygon then gets divided by that factor.

There are different strategies we have implemented to fix that issues for our use. You can:
 - Use the [Snap tool](https://pro.arcgis.com/en/pro-app/latest/tool-reference/editing/snap.htm). This tool can force the output polygons to be snapped to your road network.
 - Modify the database resolution. If you want to learn more about that, go to the [documentation](https://pro.arcgis.com/en/pro-app/latest/help/data/geodatabases/overview/the-properties-of-a-spatial-reference.htm). 


